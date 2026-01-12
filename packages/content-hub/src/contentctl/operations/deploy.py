"""Deploy operation implementation."""

from __future__ import annotations

from typing import Iterable, TextIO

from contentctl.config import Workspace
from contentctl.execute.sync import apply_sync_plan, print_sync_plan
from contentctl.plan.sync import plan_sync


def run_deploy(
    workspaces: Iterable[Workspace],
    origin: Workspace,
    path: str,
    dry_run: bool,
    verbose: bool,
    output: TextIO,
) -> None:
    for workspace in workspaces:
        plan = plan_sync(
            source_root=origin.path,
            destination_root=workspace.path,
            path=path,
            source_include=origin.include,
            source_exclude=origin.exclude,
            destination_include=workspace.include,
            destination_exclude=workspace.exclude,
        )
        if verbose or dry_run:
            print(
                "deploy "
                f"{workspace.name}: {plan.source_path} -> "
                f"{plan.destination_path}",
                file=output,
            )
        if dry_run:
            print_sync_plan(plan, output)
            print(
                f"deploy {workspace.name}: {len(plan.operations)} files planned",
                file=output,
            )
            continue
        apply_sync_plan(plan)
        if verbose:
            print_sync_plan(plan, output)
        print(
            f"deploy {workspace.name}: {len(plan.operations)} files copied",
            file=output,
        )
