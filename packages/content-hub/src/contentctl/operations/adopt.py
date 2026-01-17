from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, TextIO

from contentctl.operation_kit import execute_sync_operation, resolve_sync_roots
from contentctl.plan.sync import plan_sync, resolve_sync_paths
from contentctl.utils.concurrent import default_concurrency

if TYPE_CHECKING:
    from contentctl.config import Workspace


async def run_adopt(
    workspace: Workspace,
    origin: Workspace,
    path: str,
    output: TextIO,
    *,
    dry_run: bool,
    verbose: bool,
) -> None:
    base = default_concurrency()
    io_semaphore = asyncio.Semaphore(base)

    source_path, destination_path = resolve_sync_paths(
        source_root=workspace.path,
        destination_root=origin.path,
        path=path,
    )

    stream = plan_sync(
        source_path=source_path,
        destination_path=destination_path,
        source_include=workspace.include,
        source_exclude=workspace.exclude,
        destination_include=origin.include,
        destination_exclude=origin.exclude,
        semaphore=io_semaphore,
    )

    source_root, destination_root = resolve_sync_roots(source_path, destination_path)

    if verbose or dry_run:
        print(
            f"adopt {workspace.name}: {source_path} -> {destination_path}",
            file=output,
        )

    await execute_sync_operation(
        stream=stream,
        source_root=source_root,
        destination_root=destination_root,
        semaphore=io_semaphore,
        operation_name="adopt",
        workspace_name=workspace.name,
        dry_run=dry_run,
        verbose=verbose,
        output=output,
    )
