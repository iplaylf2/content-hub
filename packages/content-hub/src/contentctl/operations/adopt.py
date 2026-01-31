from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, TextIO

from contentctl.operation_kit import execute_sync_operation
from contentctl.plan.sync import SyncFilters, SyncPolicy, SyncScope, plan_sync
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

    plan = plan_sync(
        SyncScope(workspace.path, origin.path, path),
        SyncFilters(
            source_include=workspace.include,
            source_exclude=workspace.exclude,
            destination_include=origin.include,
            destination_exclude=origin.exclude,
        ),
        policy=SyncPolicy(semaphore=io_semaphore),
    )

    if verbose or dry_run:
        print(
            f"adopt {workspace.name}: {plan.source_path} -> {plan.destination_path}",
            file=output,
        )

    await execute_sync_operation(
        stream=plan.stream,
        source_root=plan.source_root,
        destination_root=plan.destination_root,
        semaphore=io_semaphore,
        operation_name="adopt",
        workspace_name=workspace.name,
        dry_run=dry_run,
        verbose=verbose,
        output=output,
    )
