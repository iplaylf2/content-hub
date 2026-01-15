"""Fixtures specific to contentctl module tests."""

from pathlib import Path

import pytest

from contentctl.config import Workspace

from .fixture_types import MakeWorkspace


@pytest.fixture
def make_workspace() -> MakeWorkspace:
    """Create a Workspace instance for testing."""

    def _make(name: str, root: str | Path) -> Workspace:
        return Workspace(name=name, path=Path(root), include=(), exclude=())

    return _make
