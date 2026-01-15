"""Fixtures for config module tests."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from .fixture_types import LoadYamlFixture


@pytest.fixture
def load_yaml_fixture() -> LoadYamlFixture:
    """Load a YAML fixture file."""

    def _load(path: Path) -> dict[str, Any]:
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    return _load
