"""Adopt operation implementation."""

from __future__ import annotations

from typing import TextIO

from contentctl.config import Workspace
from contentctl.execute.sync import apply_sync_plan, print_sync_plan
from contentctl.plan.sync import plan_sync


def run_adopt(
    workspace: Workspace,
    origin: Workspace,
    path: str,
    dry_run: bool,
    verbose: bool,
    output: TextIO,
) -> None:
    plan = plan_sync(
        source_root=workspace.path,
        destination_root=origin.path,
        path=path,
        source_include=workspace.include,
        source_exclude=workspace.exclude,
        destination_include=origin.include,
        destination_exclude=origin.exclude,
    )
    if verbose or dry_run:
        print(
            f"adopt {workspace.name}: {plan.source_path} -> {plan.destination_path}",
            file=output,
        )
    if dry_run:
        print_sync_plan(plan, output)
        print(
            f"adopt {workspace.name}: {len(plan.operations)} files planned",
            file=output,
        )
        return
    apply_sync_plan(plan)
    if verbose:
        print_sync_plan(plan, output)
    print(
        f"adopt {workspace.name}: {len(plan.operations)} files copied",
        file=output,
    )
