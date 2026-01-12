from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from contentctl.config import Workspace
from contentctl.operations.adopt import run_adopt
from contentctl.operations.deploy import run_deploy
from contentctl.plan.sync import SyncAction, SyncOperation, SyncPlan


def test_run_deploy_dry_run_prints_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _fake_plan()
    printed: list[SyncPlan] = []

    def fake_plan_sync(**_kwargs: object) -> SyncPlan:
        return plan

    def fake_print_sync_plan(plan_arg: SyncPlan, _output: StringIO) -> None:
        printed.append(plan_arg)

    def fail_apply_sync_plan(_plan: SyncPlan) -> None:
        raise AssertionError("apply should not run")

    monkeypatch.setattr("contentctl.operations.deploy.plan_sync", fake_plan_sync)
    monkeypatch.setattr(
        "contentctl.operations.deploy.print_sync_plan", fake_print_sync_plan
    )
    monkeypatch.setattr(
        "contentctl.operations.deploy.apply_sync_plan", fail_apply_sync_plan
    )

    output = StringIO()
    run_deploy(
        workspaces=[Workspace(name="docs", path=Path("/ws"), include=(), exclude=())],
        origin=Workspace(name="", path=Path("/origin"), include=(), exclude=()),
        path=".",
        dry_run=True,
        verbose=False,
        output=output,
    )

    text = output.getvalue()
    assert "deploy docs:" in text
    assert f"{len(plan.operations)} files planned" in text
    assert printed == [plan]


def test_run_adopt_applies_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _fake_plan()
    applied: list[SyncPlan] = []
    printed: list[SyncPlan] = []

    def fake_plan_sync(**_kwargs: object) -> SyncPlan:
        return plan

    def fake_apply_sync_plan(plan_arg: SyncPlan) -> None:
        applied.append(plan_arg)

    def fake_print_sync_plan(plan_arg: SyncPlan, _output: StringIO) -> None:
        printed.append(plan_arg)

    monkeypatch.setattr("contentctl.operations.adopt.plan_sync", fake_plan_sync)
    monkeypatch.setattr(
        "contentctl.operations.adopt.apply_sync_plan", fake_apply_sync_plan
    )
    monkeypatch.setattr(
        "contentctl.operations.adopt.print_sync_plan", fake_print_sync_plan
    )

    output = StringIO()
    run_adopt(
        workspace=Workspace(name="docs", path=Path("/ws"), include=(), exclude=()),
        origin=Workspace(name="", path=Path("/origin"), include=(), exclude=()),
        path=".",
        dry_run=False,
        verbose=False,
        output=output,
    )

    text = output.getvalue()
    assert "adopt docs:" in text
    assert f"{len(plan.operations)} files copied" in text
    assert applied == [plan]
    assert printed == []


def _fake_plan() -> SyncPlan:
    return SyncPlan(
        source_path=Path("/virtual/source"),
        target_path=Path("/virtual/target"),
        source_is_dir=True,
        operations=(
            SyncOperation(
                source=Path("/virtual/source/a.txt"),
                destination=Path("/virtual/target/a.txt"),
                action=SyncAction.COPY,
            ),
            SyncOperation(
                source=Path("/virtual/source/b.txt"),
                destination=Path("/virtual/target/b.txt"),
                action=SyncAction.SKIP,
            ),
        ),
    )
