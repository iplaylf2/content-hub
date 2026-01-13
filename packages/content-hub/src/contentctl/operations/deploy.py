"""Deploy operation implementation."""

from __future__ import annotations

import asyncio
from typing import Iterable, TextIO

from contentctl.config import Workspace
from contentctl.concurrent import count_stream, default_concurrency
from contentctl.execute.sync import apply_sync_plan, print_sync_plan
from contentctl.plan.sync import SyncAction, plan_sync, resolve_sync_paths


async def run_deploy(
    workspaces: Iterable[Workspace],
    origin: Workspace,
    path: str,
    dry_run: bool,
    verbose: bool,
    output: TextIO,
) -> None:
    base = default_concurrency()
    io_semaphore = asyncio.Semaphore(base)

    for workspace in workspaces:
        source_path, destination_path = resolve_sync_paths(
            source_root=origin.path,
            destination_root=workspace.path,
            path=path,
        )

        stream = plan_sync(
            source_path=source_path,
            destination_path=destination_path,
            source_include=origin.include,
            source_exclude=origin.exclude,
            destination_include=workspace.include,
            destination_exclude=workspace.exclude,
            semaphore=io_semaphore,
        )

        source_is_file = source_path.is_file()
        source_root = source_path.parent if source_is_file else source_path
        destination_root = (
            destination_path.parent if source_is_file else destination_path
        )

        if verbose or dry_run:
            print(
                f"deploy {workspace.name}: {source_path} -> {destination_path}",
                file=output,
            )

        if dry_run:
            stream = print_sync_plan(
                stream,
                source_root=source_root,
                destination_root=destination_root,
                output=output,
            )
            total = await count_stream(stream)
            print(
                f"deploy {workspace.name}: {total} files planned",
                file=output,
            )
            continue

        if verbose:
            stream = print_sync_plan(
                stream,
                source_root=source_root,
                destination_root=destination_root,
                output=output,
            )

        stream = apply_sync_plan(
            stream,
            source_root=source_root,
            destination_root=destination_root,
            semaphore=io_semaphore,
        )
        total = await count_stream(
            stream,
            predicate=lambda operation: operation.action is not SyncAction.SKIP,
        )
        print(
            f"deploy {workspace.name}: {total} files copied",
            file=output,
        )
