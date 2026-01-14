from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from io import StringIO
from pathlib import Path
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
    executed: list[bool] = []

    async def record_execute(*args: object, **kwargs: object) -> int:
        dry_run = kwargs.get("dry_run")
        executed.append(bool(dry_run))
        return 1

    plan_sync_mock = create_autospec(
        deploy_mod.plan_sync,
        side_effect=_fake_plan_sync,
    )
    monkeypatch.setattr(deploy_mod, "resolve_sync_paths", _fake_resolve_sync_paths)
    monkeypatch.setattr(deploy_mod, "plan_sync", plan_sync_mock)
    monkeypatch.setattr(deploy_mod, "execute_sync_operation", record_execute)

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
    assert len(executed) == 1
    assert executed[0] is True


def test_run_adopt_applies_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed: list[tuple[bool, bool]] = []

    async def record_execute(*args: object, **kwargs: object) -> int:
        dry_run = kwargs.get("dry_run")
        verbose = kwargs.get("verbose")
        executed.append((bool(dry_run), bool(verbose)))
        operation_name = kwargs.get("operation_name", "")
        workspace_name = kwargs.get("workspace_name", "")
        output = kwargs.get("output")
        if output and hasattr(output, "write"):
            from typing import cast, TextIO

            print(
                f"{operation_name} {workspace_name}: 1 files copied",
                file=cast(TextIO, output),
            )
        return 1

    plan_sync_mock = create_autospec(
        adopt_mod.plan_sync,
        side_effect=_fake_plan_sync,
    )
    monkeypatch.setattr(adopt_mod, "resolve_sync_paths", _fake_resolve_sync_paths)
    monkeypatch.setattr(adopt_mod, "plan_sync", plan_sync_mock)
    monkeypatch.setattr(adopt_mod, "execute_sync_operation", record_execute)

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
    assert len(executed) == 1
    assert executed[0] == (False, False)


@pytest.mark.parametrize(
    ("dry_run", "verbose"),
    [
        (True, False),
        (False, True),
    ],
)
def test_run_adopt_prints_plan_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    dry_run: bool,
    verbose: bool,
) -> None:
    executed: list[tuple[bool, bool]] = []

    async def record_execute(*args: object, **kwargs: object) -> int:
        dry_run = kwargs.get("dry_run")
        verbose = kwargs.get("verbose")
        executed.append((bool(dry_run), bool(verbose)))
        return 1

    plan_sync_mock = create_autospec(
        adopt_mod.plan_sync,
        side_effect=_fake_plan_sync,
    )
    monkeypatch.setattr(adopt_mod, "resolve_sync_paths", _fake_resolve_sync_paths)
    monkeypatch.setattr(adopt_mod, "plan_sync", plan_sync_mock)
    monkeypatch.setattr(adopt_mod, "execute_sync_operation", record_execute)

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
    assert len(executed) == 1
    assert executed[0] == (dry_run, verbose)


def test_run_deploy_verbose_prints_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed: list[tuple[bool, bool]] = []

    async def record_execute(*args: object, **kwargs: object) -> int:
        dry_run = kwargs.get("dry_run")
        verbose = kwargs.get("verbose")
        executed.append((bool(dry_run), bool(verbose)))
        return 1

    plan_sync_mock = create_autospec(
        deploy_mod.plan_sync,
        side_effect=_fake_plan_sync,
    )
    monkeypatch.setattr(deploy_mod, "resolve_sync_paths", _fake_resolve_sync_paths)
    monkeypatch.setattr(deploy_mod, "plan_sync", plan_sync_mock)
    monkeypatch.setattr(deploy_mod, "execute_sync_operation", record_execute)

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
    assert len(executed) == 2
    assert all(dry_run is False and verbose is True for dry_run, verbose in executed)


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
