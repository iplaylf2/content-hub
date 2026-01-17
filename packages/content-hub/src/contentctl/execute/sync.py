import asyncio
import shutil
from typing import TYPE_CHECKING, TextIO

from contentctl.plan.sync import SyncAction, SyncOperation
from contentctl.utils.concurrent import map_concurrent

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, AsyncIterator
    from pathlib import Path


async def print_sync_plan(
    operations: AsyncIterable[SyncOperation],
    destination_root: Path,
    output: TextIO,
) -> AsyncIterator[SyncOperation]:
    async for operation in operations:
        _print_operation(
            operation,
            destination_root,
            output,
        )
        yield operation


async def apply_sync_plan(
    operations: AsyncIterable[SyncOperation],
    source_root: Path,
    destination_root: Path,
    semaphore: asyncio.Semaphore,
) -> AsyncIterator[SyncOperation]:
    async def apply(operation: SyncOperation) -> SyncOperation:
        if operation.action is not SyncAction.SKIP:
            await asyncio.to_thread(
                _apply_operation,
                operation,
                source_root,
                destination_root,
            )
        return operation

    async for operation in map_concurrent(operations, apply, semaphore):
        yield operation


def _apply_operation(
    operation: SyncOperation,
    source_root: Path,
    destination_root: Path,
) -> None:
    destination = destination_root / operation.relative

    if operation.action is SyncAction.DELETE:
        if destination.exists():
            destination.unlink()
    elif operation.action in (SyncAction.COPY, SyncAction.REPLACE):
        source = source_root / operation.relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _print_operation(
    operation: SyncOperation,
    destination_root: Path,
    output: TextIO,
) -> None:
    destination = destination_root / operation.relative
    action_label = operation.action.value.lower()
    print(f"{action_label:<7} {destination}", file=output)
