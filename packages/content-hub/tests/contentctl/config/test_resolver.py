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
from tests.contentctl.fixtures import fixture_path


@pytest.mark.parametrize(
    ("fixture_name", "expected_origin_include", "expected_origin_exclude"),
    [
        ("resolver_defaults.yaml", ("src/**", "docs/**"), ("build/**",)),
        (
            "resolver_patterns.yaml",
            ("docs/**", "assets/**", "origin/**"),
            ("build/**",),
        ),
    ],
)
def test_resolve_config_origin_patterns(
    fixture_name: str,
    expected_origin_include: tuple[str, ...],
    expected_origin_exclude: tuple[str, ...],
) -> None:
    config_path = fixture_path(fixture_name)
    config = _load_fixture(config_path)
    base_dir = config_path.parent

    resolved = resolve_config(config, config_path)

    assert resolved.origin.path == (base_dir / "origin").resolve()
    assert resolved.origin.include == expected_origin_include
    assert resolved.origin.exclude == expected_origin_exclude


def test_resolve_config_workspace_patterns_defaults() -> None:
    config_path = fixture_path("resolver_defaults.yaml")
    config = _load_fixture(config_path)
    base_dir = config_path.parent

    resolved = resolve_config(config, config_path)

    docs = resolved.workspaces["docs"]
    assert docs.path == (base_dir / "docs").resolve()
    assert docs.include == ("src/**", "docs/**", "api/**")
    assert docs.exclude == ("build/**", "drafts/**")

    assets = resolved.workspaces["assets"]
    assert assets.path == (base_dir / "assets").resolve()
    assert assets.include == ("src/**", "docs/**")
    assert assets.exclude == ("build/**",)


def test_resolve_config_workspace_patterns_normalized() -> None:
    config_path = fixture_path("resolver_patterns.yaml")
    config = _load_fixture(config_path)

    resolved = resolve_config(config, config_path)

    site = resolved.workspaces["site"]
    assert site.include == ("docs/**", "assets/**", "site/**")
    assert site.exclude == ("build/**", "site/tmp/**")

    assets = resolved.workspaces["assets"]
    assert assets.include == ("docs/**", "assets/**")
    assert assets.exclude == ("build/**",)


def test_select_all_workspaces_sorted() -> None:
    config_path = fixture_path("resolver_sort.yaml")
    config = _load_fixture(config_path)

    resolved = resolve_config(config, config_path)
    names = [workspace.name for workspace in select_all_workspaces(resolved)]

    assert names == ["alpha", "zeta"]


def test_select_workspaces_unknown() -> None:
    config_path = fixture_path("resolver_unknown.yaml")
    config = _load_fixture(config_path)
    resolved = resolve_config(config, config_path)

    with pytest.raises(ConfigError):
        select_workspaces(resolved, ["missing"])


def _load_fixture(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))
