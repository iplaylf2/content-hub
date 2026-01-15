"""Fixtures specific to contentctl module tests."""

from pathlib import Path

import pytest

from contentctl.config import Workspace
from contentctl.plan.sync import SyncAction, SyncOperation

from .fixture_types import MakeWorkspace, MakeSyncOp


@pytest.fixture
def make_workspace() -> MakeWorkspace:
    """Create a Workspace instance for testing."""

    def _make(name: str, root: str | Path) -> Workspace:
        return Workspace(name=name, path=Path(root), include=(), exclude=())

    return _make


@pytest.fixture
def make_sync_op() -> MakeSyncOp:
    """Create a SyncOperation for testing."""

    def _make(filename: str, action: SyncAction) -> SyncOperation:
        return SyncOperation(relative=Path(filename), action=action)

    return _make
