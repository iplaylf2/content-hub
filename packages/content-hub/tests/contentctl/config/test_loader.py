from typing import TYPE_CHECKING, Any

import pytest
from contentctl.config import ConfigError, load_config

if TYPE_CHECKING:
    from tests.fixture_types import FixturePath


@pytest.mark.parametrize(
    "config_file",
    ["config_valid.yaml"],
)
def test_load_config_valid(fixture_path: FixturePath, config_file: str) -> None:
    config_path = fixture_path(config_file)

    config = load_config(config_path)

    assert config["origin"] == "./origin"
    assert config["workspaces"]["docs"] == "./docs"


@pytest.mark.parametrize(
    ("config_file", "env_vars", "env_to_unset", "expected"),
    [
        (
            "config_env.yaml",
            {"SPACE_STATION": "/test/station"},
            [],
            {
                "origin": "/test/station/origin",
                "workspaces": {"docs": "/test/station/docs"},
            },
        ),
        (
            "config_env_nested.yaml",
            {"ROCKET_LAUNCHPAD": "/test/launchpad"},
            ["MISSING_VAR"],
            {
                "defaults": {"exclude": ["/test/launchpad/tmp/*"]},
                "origin": {
                    "path": "/test/launchpad/origin",
                    "include": ["/test/launchpad/docs/*.md", "/fallback/*.md"],
                },
                "workspaces": {
                    "docs": {
                        "path": "/test/launchpad/docs",
                        "include": ["/test/launchpad/docs/*.md"],
                        "exclude": ["/test/launchpad/docs/drafts/*.md"],
                    },
                    "assets": "/test/launchpad/assets",
                },
            },
        ),
    ],
)
def test_load_config_env_substitution(
    fixture_path: FixturePath,
    monkeypatch: pytest.MonkeyPatch,
    config_file: str,
    env_vars: dict[str, str],
    env_to_unset: list[str],
    expected: dict[str, Any],
) -> None:
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    for env_var in env_to_unset:
        monkeypatch.delenv(env_var, raising=False)
    config_path = fixture_path(config_file)

    config = load_config(config_path)

    assert config == expected


@pytest.mark.parametrize(
    "config_file",
    ["missing.yaml"],
)
def test_load_config_rejects_missing_file(
    fixture_path: FixturePath, config_file: str
) -> None:
    config_path = fixture_path(config_file)

    with pytest.raises(ConfigError):
        load_config(config_path)


@pytest.mark.parametrize(
    "config_file",
    [
        "config_empty.yaml",
        "config_invalid_yaml.yaml",
        "config_invalid_root.yaml",
        "config_schema_error.yaml",
    ],
)
def test_load_config_invalid_files(fixture_path: FixturePath, config_file: str) -> None:
    config_path = fixture_path(config_file)

    with pytest.raises(ConfigError):
        load_config(config_path)
