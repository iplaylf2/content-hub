from __future__ import annotations

from pathlib import Path

from contentctl.plan.sync import SyncAction, SyncOperation, SyncPlan

SOURCE_ROOT = Path("/virtual/source")
TARGET_ROOT = Path("/virtual/target")


def make_sync_op(filename: str, action: SyncAction) -> SyncOperation:
    return SyncOperation(
        source=SOURCE_ROOT / filename,
        destination=TARGET_ROOT / filename,
        action=action,
    )


def make_plan(*operations: SyncOperation) -> SyncPlan:
    return SyncPlan(
        source_path=SOURCE_ROOT,
        target_path=TARGET_ROOT,
        operations=operations,
    )


def make_file_plan(filename: str) -> SyncPlan:
    return SyncPlan(
        source_path=SOURCE_ROOT / filename,
        target_path=TARGET_ROOT / filename,
        operations=(),
    )
