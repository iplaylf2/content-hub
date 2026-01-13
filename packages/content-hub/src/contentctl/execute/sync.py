"""Execution for sync plans."""

from __future__ import annotations

import asyncio
import shutil
from collections.abc import AsyncIterable, AsyncIterator
from pathlib import Path
from typing import TextIO

from contentctl.concurrent import map_concurrent
from contentctl.plan.sync import SyncAction, SyncOperation


async def print_sync_plan(
    operations: AsyncIterable[SyncOperation],
    source_root: Path,
    destination_root: Path,
    output: TextIO,
) -> AsyncIterator[SyncOperation]:
    async for operation in operations:
        _print_operation(
            operation,
            output,
            source_root,
            destination_root,
        )
        yield operation


async def apply_sync_plan(
    operations: AsyncIterable[SyncOperation],
    source_root: Path,
    destination_root: Path,
    semaphore: asyncio.Semaphore,
) -> AsyncIterator[SyncOperation]:
    async def apply(operation: SyncOperation) -> SyncOperation:
        if operation.action is SyncAction.SKIP:
            return operation
        await asyncio.to_thread(
            _copy_operation,
            operation,
            source_root,
            destination_root,
        )
        return operation

    async for operation in map_concurrent(operations, apply, semaphore):
        yield operation


def _copy_operation(
    operation: SyncOperation,
    source_root: Path,
    destination_root: Path,
) -> None:
    if operation.action is SyncAction.SKIP:
        return
    source = source_root / operation.relative
    destination = destination_root / operation.relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _print_operation(
    operation: SyncOperation,
    output: TextIO,
    source_root: Path,
    destination_root: Path,
) -> None:
    source = source_root / operation.relative
    destination = destination_root / operation.relative
    print(
        f"{operation.action.value:<7} {source} -> {destination}",
        file=output,
    )
