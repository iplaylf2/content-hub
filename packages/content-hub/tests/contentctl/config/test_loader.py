from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from contentctl.config import ConfigError, load_config
from tests.contentctl.fixtures import fixture_path


def _check_env_config(config: dict[str, Any], root: str) -> bool:
    return str(config["origin"]).endswith("/origin") and str(
        config["workspaces"]["docs"]
    ).endswith("/docs")


def _check_env_nested_config(config: dict[str, Any], root: str) -> bool:
    return (
        config["defaults"]["exclude"] == [f"{root}/tmp/*"]
        and config["origin"]["path"] == f"{root}/origin"
        and config["origin"]["include"] == [f"{root}/docs/*.md", "/fallback/*.md"]
        and config["workspaces"]["docs"]["path"] == f"{root}/docs"
        and config["workspaces"]["docs"]["include"] == [f"{root}/docs/*.md"]
        and config["workspaces"]["docs"]["exclude"] == [f"{root}/docs/drafts/*.md"]
        and config["workspaces"]["assets"] == f"{root}/assets"
    )


@pytest.mark.parametrize(
    "fixture_name",
    ["config_valid.yaml"],
)
def test_load_config_valid(fixture_name: str) -> None:
    config_path = fixture_path(fixture_name)

    config = load_config(config_path)

    assert config["origin"] == "./origin"
    assert config["workspaces"]["docs"] == "./docs"


@pytest.mark.parametrize(
    ("fixture_name", "env_vars", "expected_checks"),
    [
        (
            "config_env.yaml",
            {"SPACE_STATION": "station"},
            _check_env_config,
        ),
        (
            "config_env_nested.yaml",
            {"ROCKET_LAUNCHPAD": "launchpad"},
            _check_env_nested_config,
        ),
    ],
)
def test_load_config_env_substitution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fixture_name: str,
    env_vars: dict[str, str],
    expected_checks: Callable[[dict[str, Any], str], bool],
) -> None:
    for key, value in env_vars.items():
        monkeypatch.setenv(key, str(tmp_path / value))
    if fixture_name == "config_env_nested.yaml":
        monkeypatch.delenv("MISSING_VAR", raising=False)
    config_path = fixture_path(fixture_name)

    config = load_config(config_path)

    root_value = str(tmp_path / list(env_vars.values())[0])
    assert expected_checks(config, root_value)


@pytest.mark.parametrize(
    "filename",
    ["missing.yaml"],
)
def test_load_config_rejects_missing_file(tmp_path: Path, filename: str) -> None:
    config_path = tmp_path / filename

    with pytest.raises(ConfigError):
        load_config(config_path)


@pytest.mark.parametrize(
    "fixture",
    [
        "config_empty.yaml",
        "config_invalid_yaml.yaml",
        "config_invalid_root.yaml",
        "config_schema_error.yaml",
    ],
)
def test_load_config_invalid_files(fixture: str) -> None:
    config_path = fixture_path(fixture)

    with pytest.raises(ConfigError):
        load_config(config_path)
