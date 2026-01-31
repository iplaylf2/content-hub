from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, TextIO

from contentctl.operation_kit import execute_sync_operation
from contentctl.plan.sync import SyncFilters, SyncPolicy, SyncScope, plan_sync
from contentctl.utils.concurrent import default_concurrency

if TYPE_CHECKING:
    from collections.abc import Iterable

    from contentctl.config import Workspace


async def run_deploy(
    workspaces: Iterable[Workspace],
    origin: Workspace,
    path: str,
    output: TextIO,
    *,
    dry_run: bool,
    verbose: bool,
    allow_delete: bool,
) -> None:
    base = default_concurrency()
    io_semaphore = asyncio.Semaphore(base)

    for workspace in workspaces:
        plan = plan_sync(
            SyncScope(origin.path, workspace.path, path),
            SyncFilters(
                source_include=origin.include,
                source_exclude=origin.exclude,
                destination_include=workspace.include,
                destination_exclude=workspace.exclude,
            ),
            policy=SyncPolicy(semaphore=io_semaphore, allow_delete=allow_delete),
        )

        if verbose or dry_run:
            print(
                f"deploy {workspace.name}: {plan.source_path} -> {plan.destination_path}",
                file=output,
            )

        await execute_sync_operation(
            stream=plan.stream,
            source_root=plan.source_root,
            destination_root=plan.destination_root,
            semaphore=io_semaphore,
            operation_name="deploy",
            workspace_name=workspace.name,
            dry_run=dry_run,
            verbose=verbose,
            output=output,
        )
