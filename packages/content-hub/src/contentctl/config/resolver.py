from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


def resolve_config(config: dict[str, Any], config_path: Path) -> ResolvedConfig:
    base_dir = config_path.parent
    defaults = config.get("defaults", {})
    default_include = _normalize_patterns(defaults.get("include", []))
    default_exclude = _normalize_patterns(defaults.get("exclude", []))

    origin = _resolve_workspace(
        base_dir=base_dir,
        default_include=default_include,
        default_exclude=default_exclude,
        name="",
        raw=config["origin"],
    )

    workspaces: dict[str, Workspace] = {}
    for name, raw in config["workspaces"].items():
        workspaces[name] = _resolve_workspace(
            base_dir=base_dir,
            default_include=default_include,
            default_exclude=default_exclude,
            name=name,
            raw=raw,
        )

    return ResolvedConfig(origin=origin, workspaces=workspaces)


@dataclass(frozen=True)
class Workspace:
    name: str
    path: Path
    include: tuple[str, ...]
    exclude: tuple[str, ...]


@dataclass(frozen=True)
class ResolvedConfig:
    origin: Workspace
    workspaces: dict[str, Workspace]


def _resolve_workspace(
    base_dir: Path,
    default_include: list[str],
    default_exclude: list[str],
    name: str,
    raw: Any,
) -> Workspace:
    raw_value = cast("dict[str, Any] | str", raw)
    match raw_value:
        case str():
            resolved_path = _resolve_path(base_dir, raw_value)
            include = tuple(default_include)
            exclude = tuple(default_exclude)
        case dict():
            raw_dict = cast("Mapping[str, Any]", raw_value)
            path_value = cast("str", raw_dict["path"])
            include_raw = cast("list[str]", raw_dict.get("include", []))
            exclude_raw = cast("list[str]", raw_dict.get("exclude", []))
            resolved_path = _resolve_path(base_dir, path_value)
            include = tuple(_normalize_patterns(default_include, include_raw))
            exclude = tuple(_normalize_patterns(default_exclude, exclude_raw))
    return Workspace(name=name, path=resolved_path, include=include, exclude=exclude)


def _resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _normalize_patterns(*pattern_groups: Iterable[str]) -> list[str]:
    patterns: list[str] = []
    for group in pattern_groups:
        for pattern in group:
            cleaned = pattern.strip().replace("\\", "/")
            if cleaned.startswith("./"):
                cleaned = cleaned[2:]
            if cleaned:
                patterns.append(cleaned)
    return patterns
