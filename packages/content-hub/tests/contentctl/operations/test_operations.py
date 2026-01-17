import asyncio
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, TextIO, cast
from unittest.mock import create_autospec

import pytest
from contentctl.operations import adopt as adopt_mod
from contentctl.operations import deploy as deploy_mod
from contentctl.operations.adopt import run_adopt
from contentctl.operations.deploy import run_deploy
from contentctl.plan.sync import SyncAction, SyncOperation

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from tests.contentctl.fixture_types import MakeWorkspace
    from tests.fixture_types import FixturePath


@pytest.mark.parametrize(
    (
        "source",
        "dest",
        "workspace_name",
        "workspace_root",
        "origin_root",
        "sync_path",
        "planned_filename",
        "dry_run",
        "verbose",
    ),
    [
        (
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_single"),
            "docs",
            "/ws",
            "/origin",
            ".",
            "guide.txt",
            True,
            True,
        ),
        (
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_single"),
            "docs",
            "/ws",
            "/origin",
            ".",
            "guide.txt",
            True,
            False,
        ),
        (
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_single"),
            "docs",
            "/ws",
            "/origin",
            ".",
            "guide.txt",
            False,
            True,
        ),
        (
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_single"),
            "docs",
            "/ws",
            "/origin",
            ".",
            "guide.txt",
            False,
            False,
        ),
    ],
)
def test_run_adopt_applies_plan(
    monkeypatch: pytest.MonkeyPatch,
    fixture_path: FixturePath,
    make_workspace: MakeWorkspace,
    source: tuple[str, str],
    dest: tuple[str, str],
    workspace_name: str,
    workspace_root: str,
    origin_root: str,
    sync_path: str,
    planned_filename: str,
    *,
    dry_run: bool,
    verbose: bool,
) -> None:
    execute_calls: list[tuple[bool, bool]] = []

    async def observe_execute(*_args: object, **kwargs: object) -> int:
        execute_calls.append((bool(kwargs.get("dry_run")), bool(kwargs.get("verbose"))))
        if output := kwargs.get("output"):
            operation_name = kwargs.get("operation_name", "")
            workspace_name = kwargs.get("workspace_name", "")
            print(
                f"{operation_name} {workspace_name}: 1 files copied",
                file=cast("TextIO", output),
            )
        return 1

    execute_mock = create_autospec(
        adopt_mod.execute_sync_operation,
        side_effect=observe_execute,
    )

    def plan_sync_side_effect(
        *_args: object,
        **_kwargs: object,
    ) -> AsyncIterator[SyncOperation]:
        async def iter_ops() -> AsyncIterator[SyncOperation]:
            yield SyncOperation(
                relative=Path(planned_filename),
                action=SyncAction.COPY,
            )

        return iter_ops()

    plan_sync_mock = create_autospec(
        adopt_mod.plan_sync,
        side_effect=plan_sync_side_effect,
    )
    resolve_sync_paths_mock = create_autospec(
        adopt_mod.resolve_sync_paths,
        return_value=(
            fixture_path(*source),
            fixture_path(*dest),
        ),
    )

    monkeypatch.setattr(adopt_mod, "resolve_sync_paths", resolve_sync_paths_mock)
    monkeypatch.setattr(adopt_mod, "plan_sync", plan_sync_mock)
    monkeypatch.setattr(adopt_mod, "execute_sync_operation", execute_mock)

    output = StringIO()
    asyncio.run(
        run_adopt(
            workspace=make_workspace(workspace_name, workspace_root),
            origin=make_workspace("", origin_root),
            path=sync_path,
            dry_run=dry_run,
            verbose=verbose,
            output=output,
        )
    )

    text = output.getvalue()
    assert f"adopt {workspace_name}:" in text
    assert "1 files copied" in text
    assert execute_calls == [(dry_run, verbose)]


@pytest.mark.parametrize(
    (
        "workspace_names",
        "source_fixture",
        "destination_fixture",
        "workspace_root_prefix",
        "origin_root",
        "sync_path",
        "planned_filename",
        "resolved_source_root",
        "resolved_destination_root",
        "dry_run",
        "verbose",
        "allow_delete",
    ),
    [
        (
            ("docs", "assets"),
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_single"),
            "/",
            "/origin",
            ".",
            "guide.txt",
            "/source",
            "/destination",
            True,
            True,
            True,
        ),
        (
            ("docs", "assets"),
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_single"),
            "/",
            "/origin",
            ".",
            "guide.txt",
            "/source",
            "/destination",
            True,
            False,
            False,
        ),
        (
            ("docs", "assets"),
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_single"),
            "/",
            "/origin",
            ".",
            "guide.txt",
            "/source",
            "/destination",
            False,
            True,
            False,
        ),
        (
            ("docs", "assets"),
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_single"),
            "/",
            "/origin",
            ".",
            "guide.txt",
            "/source",
            "/destination",
            False,
            False,
            True,
        ),
    ],
)
def test_run_deploy_applies_plan(
    monkeypatch: pytest.MonkeyPatch,
    fixture_path: FixturePath,
    make_workspace: MakeWorkspace,
    workspace_names: tuple[str, ...],
    source_fixture: tuple[str, ...],
    destination_fixture: tuple[str, ...],
    workspace_root_prefix: str,
    origin_root: str,
    sync_path: str,
    planned_filename: str,
    resolved_source_root: str,
    resolved_destination_root: str,
    *,
    dry_run: bool,
    verbose: bool,
    allow_delete: bool,
) -> None:
    execute_calls: list[tuple[str, bool, bool]] = []
    allow_delete_calls: list[bool] = []

    async def observe_execute(*_args: object, **kwargs: object) -> int:
        execute_calls.append(
            (
                str(kwargs.get("workspace_name", "")),
                bool(kwargs.get("dry_run")),
                bool(kwargs.get("verbose")),
            )
        )
        return 1

    def plan_sync_side_effect(
        *_args: object,
        **kwargs: object,
    ) -> AsyncIterator[SyncOperation]:
        allow_delete_calls.append(bool(kwargs.get("allow_delete")))

        async def iter_ops() -> AsyncIterator[SyncOperation]:
            yield SyncOperation(
                relative=Path(planned_filename),
                action=SyncAction.COPY,
            )

        return iter_ops()

    resolve_sync_paths_mock = create_autospec(
        deploy_mod.resolve_sync_paths,
        return_value=(
            fixture_path(*source_fixture),
            fixture_path(*destination_fixture),
        ),
    )
    resolve_sync_roots_mock = create_autospec(
        deploy_mod.resolve_sync_roots,
        return_value=(Path(resolved_source_root), Path(resolved_destination_root)),
    )
    plan_sync_mock = create_autospec(
        deploy_mod.plan_sync,
        side_effect=plan_sync_side_effect,
    )
    execute_mock = create_autospec(
        deploy_mod.execute_sync_operation,
        side_effect=observe_execute,
    )

    monkeypatch.setattr(deploy_mod, "resolve_sync_paths", resolve_sync_paths_mock)
    monkeypatch.setattr(deploy_mod, "resolve_sync_roots", resolve_sync_roots_mock)
    monkeypatch.setattr(deploy_mod, "plan_sync", plan_sync_mock)
    monkeypatch.setattr(deploy_mod, "execute_sync_operation", execute_mock)

    workspaces = [
        make_workspace(name, f"{workspace_root_prefix}{name}")
        for name in workspace_names
    ]
    origin = make_workspace("", origin_root)

    output = StringIO()
    asyncio.run(
        run_deploy(
            workspaces=workspaces,
            origin=origin,
            path=sync_path,
            dry_run=dry_run,
            verbose=verbose,
            allow_delete=allow_delete,
            output=output,
        )
    )

    text = output.getvalue()
    if verbose or dry_run:
        assert all(f"deploy {name}:" in text for name in workspace_names)
    else:
        assert text == ""

    assert execute_calls == [(name, dry_run, verbose) for name in workspace_names]
    assert allow_delete_calls == [allow_delete, allow_delete]
