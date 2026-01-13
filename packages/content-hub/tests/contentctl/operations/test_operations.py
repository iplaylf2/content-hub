from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from io import StringIO
from pathlib import Path
from typing import TextIO
from unittest.mock import create_autospec

import pytest

from tests.contentctl.fixtures import DEFAULT_PATH, fixture_path, make_workspace
from contentctl.config import Workspace
from contentctl.operations import adopt as adopt_mod
from contentctl.operations import deploy as deploy_mod
from contentctl.operations.adopt import run_adopt
from contentctl.operations.deploy import run_deploy
from contentctl.plan.sync import SyncAction, SyncOperation


def test_run_deploy_dry_run_prints_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    printed: list[AsyncIterator[SyncOperation]] = []

    def record_print(
        stream: AsyncIterator[SyncOperation],
        source_root: Path,
        destination_root: Path,
        output: TextIO,
    ) -> AsyncIterator[SyncOperation]:
        printed.append(stream)
        return stream

    plan_sync_mock = create_autospec(
        deploy_mod.plan_sync,
        side_effect=_fake_plan_sync,
    )
    monkeypatch.setattr(deploy_mod, "resolve_sync_paths", _fake_resolve_sync_paths)

    def fail_apply(
        _stream: AsyncIterator[SyncOperation],
        source_root: Path,
        destination_root: Path,
        semaphore: asyncio.Semaphore,
    ) -> AsyncIterator[SyncOperation]:
        raise AssertionError("apply should not run")

    monkeypatch.setattr(deploy_mod, "plan_sync", plan_sync_mock)
    monkeypatch.setattr(deploy_mod, "print_sync_plan", record_print)
    monkeypatch.setattr(deploy_mod, "apply_sync_plan", fail_apply)

    output = StringIO()
    asyncio.run(
        run_deploy(
            workspaces=[make_workspace("docs", "/ws")],
            origin=ORIGIN,
            path=DEFAULT_PATH,
            dry_run=True,
            verbose=False,
            output=output,
        )
    )

    text = output.getvalue()
    assert "deploy docs:" in text
    assert "1 files planned" in text
    assert len(printed) == 1


def test_run_adopt_applies_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    applied: list[AsyncIterator[SyncOperation]] = []
    printed: list[AsyncIterator[SyncOperation]] = []

    def record_apply(
        stream: AsyncIterator[SyncOperation],
        source_root: Path,
        destination_root: Path,
        semaphore: asyncio.Semaphore,
    ) -> AsyncIterator[SyncOperation]:
        applied.append(stream)
        return stream

    def record_print(
        stream: AsyncIterator[SyncOperation],
        source_root: Path,
        destination_root: Path,
        output: TextIO,
    ) -> AsyncIterator[SyncOperation]:
        printed.append(stream)
        return stream

    plan_sync_mock = create_autospec(
        adopt_mod.plan_sync,
        side_effect=_fake_plan_sync,
    )
    monkeypatch.setattr(adopt_mod, "resolve_sync_paths", _fake_resolve_sync_paths)
    monkeypatch.setattr(adopt_mod, "plan_sync", plan_sync_mock)
    monkeypatch.setattr(adopt_mod, "apply_sync_plan", record_apply)
    monkeypatch.setattr(adopt_mod, "print_sync_plan", record_print)

    output = StringIO()
    asyncio.run(
        run_adopt(
            workspace=make_workspace("docs", "/ws"),
            origin=ORIGIN,
            path=DEFAULT_PATH,
            dry_run=False,
            verbose=False,
            output=output,
        )
    )

    text = output.getvalue()
    assert "adopt docs:" in text
    assert "1 files copied" in text
    assert len(applied) == 1
    assert printed == []


@pytest.mark.parametrize(
    ("dry_run", "verbose", "expects_apply", "summary"),
    [
        (True, False, False, "planned"),
        (False, True, True, "copied"),
    ],
)
def test_run_adopt_prints_plan_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    dry_run: bool,
    verbose: bool,
    expects_apply: bool,
    summary: str,
) -> None:
    applied: list[AsyncIterator[SyncOperation]] = []
    printed: list[AsyncIterator[SyncOperation]] = []

    def record_print(
        stream: AsyncIterator[SyncOperation],
        source_root: Path,
        destination_root: Path,
        output: TextIO,
    ) -> AsyncIterator[SyncOperation]:
        printed.append(stream)
        return stream

    plan_sync_mock = create_autospec(
        adopt_mod.plan_sync,
        side_effect=_fake_plan_sync,
    )
    monkeypatch.setattr(adopt_mod, "resolve_sync_paths", _fake_resolve_sync_paths)

    def maybe_apply(
        stream: AsyncIterator[SyncOperation],
        source_root: Path,
        destination_root: Path,
        semaphore: asyncio.Semaphore,
    ) -> AsyncIterator[SyncOperation]:
        if not expects_apply:
            raise AssertionError("apply should not run")
        applied.append(stream)
        return stream

    monkeypatch.setattr(adopt_mod, "plan_sync", plan_sync_mock)
    monkeypatch.setattr(adopt_mod, "apply_sync_plan", maybe_apply)
    monkeypatch.setattr(adopt_mod, "print_sync_plan", record_print)

    output = StringIO()
    asyncio.run(
        run_adopt(
            workspace=make_workspace("docs", "/ws"),
            origin=ORIGIN,
            path=DEFAULT_PATH,
            dry_run=dry_run,
            verbose=verbose,
            output=output,
        )
    )

    text = output.getvalue()
    assert "adopt docs:" in text
    assert f"1 files {summary}" in text
    assert len(applied) == (1 if expects_apply else 0)
    assert len(printed) == 1


def test_run_deploy_verbose_prints_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    applied: list[AsyncIterator[SyncOperation]] = []
    printed: list[AsyncIterator[SyncOperation]] = []

    def record_apply(
        stream: AsyncIterator[SyncOperation],
        source_root: Path,
        destination_root: Path,
        semaphore: asyncio.Semaphore,
    ) -> AsyncIterator[SyncOperation]:
        applied.append(stream)
        return stream

    def record_print(
        stream: AsyncIterator[SyncOperation],
        source_root: Path,
        destination_root: Path,
        output: TextIO,
    ) -> AsyncIterator[SyncOperation]:
        printed.append(stream)
        return stream

    plan_sync_mock = create_autospec(
        deploy_mod.plan_sync,
        side_effect=_fake_plan_sync,
    )
    monkeypatch.setattr(deploy_mod, "resolve_sync_paths", _fake_resolve_sync_paths)
    monkeypatch.setattr(deploy_mod, "plan_sync", plan_sync_mock)
    monkeypatch.setattr(deploy_mod, "apply_sync_plan", record_apply)
    monkeypatch.setattr(deploy_mod, "print_sync_plan", record_print)

    output = StringIO()
    asyncio.run(
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
    )

    text = output.getvalue()
    assert "deploy docs:" in text
    assert "deploy assets:" in text
    assert "1 files copied" in text
    assert len(applied) == 2
    assert len(printed) == 2


def _fake_stream() -> AsyncIterator[SyncOperation]:
    async def iter_ops() -> AsyncIterator[SyncOperation]:
        yield SyncOperation(
            relative=Path("guide.txt"),
            action=SyncAction.COPY,
        )

    return iter_ops()


def _fake_plan_sync(
    *_args: object,
    **_kwargs: object,
) -> AsyncIterator[SyncOperation]:
    return _fake_stream()


def _fake_resolve_sync_paths(
    *_args: object,
    **_kwargs: object,
) -> tuple[Path, Path]:
    return (
        fixture_path("plan_sync", "source_dir"),
        fixture_path("plan_sync", "destination_dir"),
    )


ORIGIN = Workspace(name="", path=Path("/origin"), include=(), exclude=())
