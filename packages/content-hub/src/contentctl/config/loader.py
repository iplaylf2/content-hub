"""Config loading and validation for contentctl."""

from __future__ import annotations

import importlib.resources as resources
import json
import os
from collections import UserDict
from functools import lru_cache
from string import Template
from typing import TYPE_CHECKING, Any, Protocol, cast

import yaml
from jsonschema import Draft202012Validator

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from jsonschema.exceptions import ValidationError


def load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise ConfigError(f"config file not found: {config_path}")

    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read config file: {config_path}") from exc

    try:
        config = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid yaml in config file: {config_path}") from exc

    match config:
        case None:
            raise ConfigError(f"config file is empty: {config_path}")
        case dict():
            pass
        case _:
            raise ConfigError("config root must be a mapping.")

    config = _render_env_vars(config)
    config_dict = cast("dict[str, Any]", config)
    _validate_schema(config_dict)
    return config_dict


class ConfigError(ValueError):
    pass


def _validate_schema(config: dict[str, Any]) -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors = sorted(
        cast("_Validator", validator).iter_errors(config),
        key=lambda err: tuple(err.path),
    )
    if not errors:
        return

    details = "\n".join(f"- {_format_error_path(err)}: {err.message}" for err in errors)
    raise ConfigError(f"config schema validation failed:\n{details}")


def _render_env_vars(value: Any) -> Any:
    match value:
        case str():
            return Template(value).substitute(_EnvVars(os.environ))
        case list():
            value_list = cast("list[Any]", value)
            return [_render_env_vars(item) for item in value_list]
        case dict():
            rendered: dict[str, Any] = {}
            value_dict = cast("dict[str, Any]", value)
            for key, item in value_dict.items():
                rendered[key] = _render_env_vars(item)
            return rendered
        case _:
            return value


class _Validator(Protocol):
    def iter_errors(self, instance: Any) -> Iterable[ValidationError]: ...


def _format_error_path(error: ValidationError) -> str:
    if not error.path:
        return "<root>"
    segments: list[str] = []
    for segment in error.path:
        match segment:
            case int():
                segments.append(f"[{segment}]")
            case _:
                if segments:
                    segments.append(".")
                segments.append(str(segment))
    return "".join(segments)


class _EnvVars(UserDict[str, str]):
    def __missing__(self, key: str) -> str:
        return ""


@lru_cache
def _load_schema() -> dict[str, Any]:
    raw = resources.read_text(
        "contentctl.schema",
        "content-hub.schema.json",
    )
    return cast("dict[str, Any]", json.loads(raw))
