"""Fixtures for config module tests."""

from typing import TYPE_CHECKING, Any

import pytest
import yaml

if TYPE_CHECKING:
    from pathlib import Path

    from .fixture_types import LoadYamlFixture


@pytest.fixture
def load_yaml_fixture() -> LoadYamlFixture:
    """Load a YAML fixture file."""

    def _load(path: Path) -> dict[str, Any]:
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    return _load
