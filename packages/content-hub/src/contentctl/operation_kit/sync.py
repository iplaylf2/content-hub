from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

from contentctl.execute.sync import apply_sync_plan, print_sync_plan
from contentctl.plan.sync import SyncAction, SyncOperation
from contentctl.utils.streams import count_stream

if TYPE_CHECKING:
    import asyncio
    from collections.abc import AsyncIterable
    from pathlib import Path


async def execute_sync_operation(
    stream: AsyncIterable[SyncOperation],
    source_root: Path,
    destination_root: Path,
    semaphore: asyncio.Semaphore,
    operation_name: str,
    workspace_name: str,
    output: TextIO,
    *,
    dry_run: bool,
    verbose: bool,
) -> int:
    if dry_run:
        return await _count_planned_operations(
            stream,
            destination_root,
            operation_name,
            workspace_name,
            output,
        )
    else:
        return await _execute_and_count_copied(
            stream,
            source_root,
            destination_root,
            semaphore,
            operation_name,
            workspace_name,
            output,
            verbose=verbose,
        )


async def _count_planned_operations(
    stream: AsyncIterable[SyncOperation],
    destination_root: Path,
    operation_name: str,
    workspace_name: str,
    output: TextIO,
) -> int:
    stream = print_sync_plan(stream, destination_root, output)
    total = await count_stream(stream)
    print(
        f"{operation_name} {workspace_name}: planned {total} files",
        file=output,
    )
    return total


async def _execute_and_count_copied(
    stream: AsyncIterable[SyncOperation],
    source_root: Path,
    destination_root: Path,
    semaphore: asyncio.Semaphore,
    operation_name: str,
    workspace_name: str,
    output: TextIO,
    *,
    verbose: bool,
) -> int:
    if verbose:
        stream = print_sync_plan(stream, destination_root, output)

    stream = apply_sync_plan(stream, source_root, destination_root, semaphore)
    total = await count_stream(
        stream, predicate=lambda op: op.action not in (SyncAction.SKIP,)
    )
    print(
        f"{operation_name} {workspace_name}: synced {total} files",
        file=output,
    )
    return total
