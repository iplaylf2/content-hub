from collections.abc import Iterable

from .loader import ConfigError
from .resolver import ResolvedConfig, Workspace


def select_all_workspaces(resolved: ResolvedConfig) -> list[Workspace]:
    return [resolved.workspaces[name] for name in sorted(resolved.workspaces.keys())]


def select_workspaces(
    resolved: ResolvedConfig, workspaces: Iterable[str]
) -> list[Workspace]:
    selected: list[Workspace] = []
    for name in workspaces:
        try:
            selected.append(resolved.workspaces[name])
        except KeyError as exc:
            raise ConfigError(f"unknown workspace: {name}") from exc
    return selected
