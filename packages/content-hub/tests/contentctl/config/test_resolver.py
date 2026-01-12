from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from contentctl.config import (
    ConfigError,
    resolve_config,
    select_all_workspaces,
    select_workspaces,
)
from conftest import FIXTURES_ROOT


def test_resolve_config_paths_and_patterns() -> None:
    config_path = _fixture_path("resolver_defaults.yaml")
    config = _load_fixture(config_path)
    base_dir = config_path.parent

    resolved = resolve_config(config, config_path)

    assert resolved.origin.path == (base_dir / "origin").resolve()
    assert resolved.origin.include == ("src/**", "docs/**")
    assert resolved.origin.exclude == ("build/**",)

    docs = resolved.workspaces["docs"]
    assert docs.path == (base_dir / "docs").resolve()
    assert docs.include == ("src/**", "docs/**", "api/**")
    assert docs.exclude == ("build/**", "drafts/**")

    assets = resolved.workspaces["assets"]
    assert assets.path == (base_dir / "assets").resolve()
    assert assets.include == ("src/**", "docs/**")
    assert assets.exclude == ("build/**",)


def test_select_all_workspaces_sorted() -> None:
    config_path = _fixture_path("resolver_sort.yaml")
    config = _load_fixture(config_path)

    resolved = resolve_config(config, config_path)
    names = [workspace.name for workspace in select_all_workspaces(resolved)]

    assert names == ["alpha", "zeta"]


def test_select_workspaces_unknown() -> None:
    config_path = _fixture_path("resolver_unknown.yaml")
    config = _load_fixture(config_path)
    resolved = resolve_config(config, config_path)

    with pytest.raises(ConfigError):
        select_workspaces(resolved, ["missing"])


def _fixture_path(name: str) -> Path:
    return FIXTURES_ROOT / name


def _load_fixture(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))
