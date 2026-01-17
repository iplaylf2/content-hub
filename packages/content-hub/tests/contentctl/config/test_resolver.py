from typing import TYPE_CHECKING

import pytest
from contentctl.config import (
    ConfigError,
    resolve_config,
    select_all_workspaces,
    select_workspaces,
)

if TYPE_CHECKING:
    from tests.fixture_types import FixturePath

    from .fixture_types import LoadYamlFixture


@pytest.mark.parametrize(
    ("config_file", "expected_origin_include", "expected_origin_exclude"),
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
    fixture_path: FixturePath,
    load_yaml_fixture: LoadYamlFixture,
    config_file: str,
    expected_origin_include: tuple[str, ...],
    expected_origin_exclude: tuple[str, ...],
) -> None:
    config_path = fixture_path(config_file)
    config = load_yaml_fixture(config_path)
    base_dir = config_path.parent

    resolved = resolve_config(config, config_path)

    assert resolved.origin.path == (base_dir / "origin").resolve()
    assert resolved.origin.include == expected_origin_include
    assert resolved.origin.exclude == expected_origin_exclude


@pytest.mark.parametrize(
    ("config_file", "workspace_name", "expected_include", "expected_exclude"),
    [
        (
            "resolver_defaults.yaml",
            "docs",
            ("src/**", "docs/**", "api/**"),
            ("build/**", "drafts/**"),
        ),
        (
            "resolver_defaults.yaml",
            "assets",
            ("src/**", "docs/**"),
            ("build/**",),
        ),
        (
            "resolver_patterns.yaml",
            "site",
            ("docs/**", "assets/**", "site/**"),
            ("build/**", "site/tmp/**"),
        ),
        (
            "resolver_patterns.yaml",
            "assets",
            ("docs/**", "assets/**"),
            ("build/**",),
        ),
    ],
)
def test_resolve_config_workspace_patterns(
    fixture_path: FixturePath,
    load_yaml_fixture: LoadYamlFixture,
    config_file: str,
    workspace_name: str,
    expected_include: tuple[str, ...],
    expected_exclude: tuple[str, ...],
) -> None:
    config_path = fixture_path(config_file)
    config = load_yaml_fixture(config_path)
    base_dir = config_path.parent

    resolved = resolve_config(config, config_path)

    workspace = resolved.workspaces[workspace_name]
    assert workspace.path == (base_dir / workspace_name).resolve()
    assert workspace.include == expected_include
    assert workspace.exclude == expected_exclude


@pytest.mark.parametrize(
    ("config_file", "expected_names"),
    [
        ("resolver_sort.yaml", ["alpha", "zeta"]),
    ],
)
def test_select_all_workspaces_sorted(
    fixture_path: FixturePath,
    load_yaml_fixture: LoadYamlFixture,
    config_file: str,
    expected_names: list[str],
) -> None:
    config_path = fixture_path(config_file)
    config = load_yaml_fixture(config_path)

    resolved = resolve_config(config, config_path)
    names = [workspace.name for workspace in select_all_workspaces(resolved)]

    assert names == expected_names


@pytest.mark.parametrize(
    "config_file",
    ["resolver_unknown.yaml"],
)
def test_select_workspaces_unknown(
    fixture_path: FixturePath, load_yaml_fixture: LoadYamlFixture, config_file: str
) -> None:
    config_path = fixture_path(config_file)
    config = load_yaml_fixture(config_path)
    resolved = resolve_config(config, config_path)

    with pytest.raises(ConfigError):
        select_workspaces(resolved, ["missing"])
