"""Execution for sync plans."""

from __future__ import annotations

import shutil
from typing import Iterable, TextIO

from contentctl.plan.sync import SyncAction, SyncOperation, SyncPlan


def apply_sync_plan(plan: SyncPlan) -> None:
    _prepare_target(plan)
    _apply_copy_operations(plan.operations)


def print_sync_plan(plan: SyncPlan, output: TextIO) -> None:
    for operation in plan.operations:
        print(
            f"{operation.action.value:<7} {operation.source} -> {operation.destination}",
            file=output,
        )


def _prepare_target(plan: SyncPlan) -> None:
    target_path = plan.target_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if plan.source_is_dir:
        target_path.mkdir(parents=True, exist_ok=True)


def _apply_copy_operations(ops: Iterable[SyncOperation]) -> None:
    for operation in ops:
        if operation.action is SyncAction.SKIP:
            continue
        destination = operation.destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(operation.source, destination)
