from __future__ import annotations

from pathlib import Path

from contentctl.plan.sync import SyncAction, SyncOperation, SyncPlan

SOURCE_ROOT = Path("/virtual/source")
DESTINATION_ROOT = Path("/virtual/destination")


def make_sync_op(filename: str, action: SyncAction) -> SyncOperation:
    return SyncOperation(
        source=SOURCE_ROOT / filename,
        destination=DESTINATION_ROOT / filename,
        action=action,
    )


def make_plan(*operations: SyncOperation) -> SyncPlan:
    return SyncPlan(
        source_path=SOURCE_ROOT,
        destination_path=DESTINATION_ROOT,
        operations=operations,
    )


def make_file_plan(filename: str) -> SyncPlan:
    return SyncPlan(
        source_path=SOURCE_ROOT / filename,
        destination_path=DESTINATION_ROOT / filename,
        operations=(),
    )
