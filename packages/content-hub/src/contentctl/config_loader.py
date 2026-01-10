"""Config loading and validation for contentctl."""

from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache
from importlib.resources import files
import json
from pathlib import Path
from typing import Any, Protocol, cast

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


def load_config(config_path: Path) -> dict[str, Any]:
    """Load and validate a content-hub config file."""
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Unable to read config file: {config_path}") from exc

    try:
        config = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in config file: {config_path}") from exc

    if config is None:
        raise ConfigError(f"Config file is empty: {config_path}")
    if not isinstance(config, dict):
        raise ConfigError("Config root must be a mapping/object.")

    config_dict = cast(dict[str, Any], config)
    _validate_schema(config_dict)
    return config_dict


class ConfigError(ValueError):
    """Raised when the config file cannot be loaded or validated."""


class _Validator(Protocol):
    def iter_errors(self, instance: Any) -> Iterable[ValidationError]: ...


def _validate_schema(config: dict[str, Any]) -> None:
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    errors = sorted(
        cast(_Validator, validator).iter_errors(config),
        key=lambda err: tuple(err.path),
    )
    if not errors:
        return

    details = "\n".join(f"- {_format_error_path(err)}: {err.message}" for err in errors)
    raise ConfigError(f"Config schema validation failed:\n{details}")


def _format_error_path(error: ValidationError) -> str:
    if not error.path:
        return "<root>"
    segments: list[str] = []
    for segment in error.path:
        if isinstance(segment, int):
            segments.append(f"[{segment}]")
        else:
            if segments:
                segments.append(".")
            segments.append(str(segment))
    return "".join(segments)


@lru_cache
def _load_schema() -> dict[str, Any]:
    schema_path = files("contentctl.schema").joinpath("content-hub.schema.json")
    try:
        raw = schema_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Unable to read schema file: {schema_path}") from exc
    return cast(dict[str, Any], json.loads(raw))
