from __future__ import annotations

from pathlib import Path

import pytest

from contentctl.config import ConfigError, load_config
from conftest import FIXTURES_ROOT


def test_load_config_valid() -> None:
    config_path = _fixture_path("config_valid.yaml")

    config = load_config(config_path)

    assert config["origin"] == "./origin"
    assert config["workspaces"]["docs"] == "./docs"


def test_load_config_env_substitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONTENT_HUB_ROOT", str(tmp_path / "root"))
    config_path = _fixture_path("config_env.yaml")

    config = load_config(config_path)

    assert config["origin"].endswith("/origin")
    assert config["workspaces"]["docs"].endswith("/docs")


def test_load_config_missing_file(tmp_path: Path) -> None:
    config_path = tmp_path / "missing.yaml"

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
    config_path = _fixture_path(fixture)

    with pytest.raises(ConfigError):
        load_config(config_path)


def _fixture_path(name: str) -> Path:
    return FIXTURES_ROOT / name
