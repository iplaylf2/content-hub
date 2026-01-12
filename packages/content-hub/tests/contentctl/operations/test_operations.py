from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import TextIO
from unittest.mock import create_autospec

import pytest

from tests.contentctl.fixtures import DEFAULT_PATH, make_workspace
from contentctl.config import Workspace
from contentctl.operations import adopt as adopt_mod
from contentctl.operations import deploy as deploy_mod
from contentctl.operations.adopt import run_adopt
from contentctl.operations.deploy import run_deploy
from contentctl.plan.sync import SyncAction, SyncOperation, SyncPlan


def test_run_deploy_dry_run_prints_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _fake_plan()
    printed: list[SyncPlan] = []

    def record_print(plan_arg: SyncPlan, _output: TextIO) -> None:
        printed.append(plan_arg)

    plan_sync_mock = create_autospec(deploy_mod.plan_sync, return_value=plan)
    print_sync_plan_mock = create_autospec(
        deploy_mod.print_sync_plan,
        side_effect=record_print,
    )
    apply_sync_plan_mock = create_autospec(
        deploy_mod.apply_sync_plan,
        side_effect=AssertionError("apply should not run"),
    )
    monkeypatch.setattr(deploy_mod, "plan_sync", plan_sync_mock)
    monkeypatch.setattr(deploy_mod, "print_sync_plan", print_sync_plan_mock)
    monkeypatch.setattr(deploy_mod, "apply_sync_plan", apply_sync_plan_mock)

    output = StringIO()
    run_deploy(
        workspaces=[make_workspace("docs", "/ws")],
        origin=ORIGIN,
        path=DEFAULT_PATH,
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

    def record_apply(plan_arg: SyncPlan) -> None:
        applied.append(plan_arg)

    def record_print(plan_arg: SyncPlan, _output: TextIO) -> None:
        printed.append(plan_arg)

    plan_sync_mock = create_autospec(adopt_mod.plan_sync, return_value=plan)
    apply_sync_plan_mock = create_autospec(
        adopt_mod.apply_sync_plan,
        side_effect=record_apply,
    )
    print_sync_plan_mock = create_autospec(
        adopt_mod.print_sync_plan,
        side_effect=record_print,
    )
    monkeypatch.setattr(adopt_mod, "plan_sync", plan_sync_mock)
    monkeypatch.setattr(adopt_mod, "apply_sync_plan", apply_sync_plan_mock)
    monkeypatch.setattr(adopt_mod, "print_sync_plan", print_sync_plan_mock)

    output = StringIO()
    run_adopt(
        workspace=make_workspace("docs", "/ws"),
        origin=ORIGIN,
        path=DEFAULT_PATH,
        dry_run=False,
        verbose=False,
        output=output,
    )

    text = output.getvalue()
    assert "adopt docs:" in text
    assert f"{len(plan.operations)} files copied" in text
    assert applied == [plan]
    assert printed == []


def test_run_adopt_dry_run_prints_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _fake_plan()
    printed: list[SyncPlan] = []

    def record_print(plan_arg: SyncPlan, _output: TextIO) -> None:
        printed.append(plan_arg)

    plan_sync_mock = create_autospec(adopt_mod.plan_sync, return_value=plan)
    print_sync_plan_mock = create_autospec(
        adopt_mod.print_sync_plan,
        side_effect=record_print,
    )
    apply_sync_plan_mock = create_autospec(
        adopt_mod.apply_sync_plan,
        side_effect=AssertionError("apply should not run"),
    )
    monkeypatch.setattr(adopt_mod, "plan_sync", plan_sync_mock)
    monkeypatch.setattr(adopt_mod, "print_sync_plan", print_sync_plan_mock)
    monkeypatch.setattr(adopt_mod, "apply_sync_plan", apply_sync_plan_mock)

    output = StringIO()
    run_adopt(
        workspace=make_workspace("docs", "/ws"),
        origin=ORIGIN,
        path=DEFAULT_PATH,
        dry_run=True,
        verbose=False,
        output=output,
    )

    text = output.getvalue()
    assert "adopt docs:" in text
    assert f"{len(plan.operations)} files planned" in text
    assert printed == [plan]


def test_run_adopt_verbose_prints_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _fake_plan()
    applied: list[SyncPlan] = []
    printed: list[SyncPlan] = []

    def record_apply(plan_arg: SyncPlan) -> None:
        applied.append(plan_arg)

    def record_print(plan_arg: SyncPlan, _output: TextIO) -> None:
        printed.append(plan_arg)

    plan_sync_mock = create_autospec(adopt_mod.plan_sync, return_value=plan)
    apply_sync_plan_mock = create_autospec(
        adopt_mod.apply_sync_plan,
        side_effect=record_apply,
    )
    print_sync_plan_mock = create_autospec(
        adopt_mod.print_sync_plan,
        side_effect=record_print,
    )
    monkeypatch.setattr(adopt_mod, "plan_sync", plan_sync_mock)
    monkeypatch.setattr(adopt_mod, "apply_sync_plan", apply_sync_plan_mock)
    monkeypatch.setattr(adopt_mod, "print_sync_plan", print_sync_plan_mock)

    output = StringIO()
    run_adopt(
        workspace=make_workspace("docs", "/ws"),
        origin=ORIGIN,
        path=DEFAULT_PATH,
        dry_run=False,
        verbose=True,
        output=output,
    )

    text = output.getvalue()
    assert "adopt docs:" in text
    assert f"{len(plan.operations)} files copied" in text
    assert applied == [plan]
    assert printed == [plan]


def test_run_deploy_verbose_prints_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _fake_plan()
    applied: list[SyncPlan] = []
    printed: list[SyncPlan] = []

    def record_apply(plan_arg: SyncPlan) -> None:
        applied.append(plan_arg)

    def record_print(plan_arg: SyncPlan, _output: TextIO) -> None:
        printed.append(plan_arg)

    plan_sync_mock = create_autospec(deploy_mod.plan_sync, return_value=plan)
    apply_sync_plan_mock = create_autospec(
        deploy_mod.apply_sync_plan,
        side_effect=record_apply,
    )
    print_sync_plan_mock = create_autospec(
        deploy_mod.print_sync_plan,
        side_effect=record_print,
    )
    monkeypatch.setattr(deploy_mod, "plan_sync", plan_sync_mock)
    monkeypatch.setattr(deploy_mod, "apply_sync_plan", apply_sync_plan_mock)
    monkeypatch.setattr(deploy_mod, "print_sync_plan", print_sync_plan_mock)

    output = StringIO()
    run_deploy(
        workspaces=[
            make_workspace("docs", "/ws"),
            make_workspace("assets", "/assets"),
        ],
        origin=ORIGIN,
        path=DEFAULT_PATH,
        dry_run=False,
        verbose=True,
        output=output,
    )

    text = output.getvalue()
    assert "deploy docs:" in text
    assert "deploy assets:" in text
    assert f"{len(plan.operations)} files copied" in text
    assert applied == [plan, plan]
    assert printed == [plan, plan]


def _fake_plan() -> SyncPlan:
    return SyncPlan(
        source_path=Path("/virtual/source"),
        target_path=Path("/virtual/target"),
        operations=(
            SyncOperation(
                source=Path("/virtual/source/guide.txt"),
                destination=Path("/virtual/target/guide.txt"),
                action=SyncAction.COPY,
            ),
        ),
    )


ORIGIN = Workspace(name="", path=Path("/origin"), include=(), exclude=())
