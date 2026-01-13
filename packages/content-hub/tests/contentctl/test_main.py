from __future__ import annotations

from pathlib import Path
from typing import TypedDict, cast
from unittest.mock import AsyncMock, create_autospec

import pytest

from tests.contentctl.fixtures import DEFAULT_PATH, make_workspace
from contentctl.cli_parser import AdoptContext, DeployContext
from contentctl.config import ResolvedConfig, Workspace
import contentctl.__main__ as mainmod


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        ("load_config", "bad config"),
        ("resolve_config", "resolve failed"),
    ],
)
def test_main_exits_on_config_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
    message: str,
) -> None:
    ctx = _deploy_ctx()

    def fake_parse_cli(_argv: list[str], _cwd: Path) -> DeployContext:
        return ctx

    def fake_load_config(_path: Path) -> dict[str, object]:
        if failure == "load_config":
            raise mainmod.ConfigError(message)
        return {}

    def fake_resolve_config(_cfg: dict[str, object], _path: Path) -> ResolvedConfig:
        if failure == "resolve_config":
            raise mainmod.ConfigError(message)
        return _resolved_config()

    monkeypatch.setattr(mainmod, "parse_cli", fake_parse_cli)
    monkeypatch.setattr(mainmod, "load_config", fake_load_config)
    monkeypatch.setattr(mainmod, "resolve_config", fake_resolve_config)

    with pytest.raises(SystemExit) as excinfo:
        mainmod.main()

    assert excinfo.value.code == 2
    assert message in capsys.readouterr().err


def test_main_exits_on_sync_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ctx = _deploy_ctx()

    _patch_main_context(monkeypatch, ctx=ctx, resolved=_resolved_config())

    async def raise_sync_error(_ctx: object, _resolved: object) -> None:
        raise mainmod.SyncError("sync failed")

    monkeypatch.setattr(mainmod, "_dispatch", raise_sync_error)

    with pytest.raises(SystemExit) as excinfo:
        mainmod.main()

    assert excinfo.value.code == 1
    assert "sync failed" in capsys.readouterr().err


def test_main_exits_on_dispatch_config_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ctx = _deploy_ctx(all_workspaces=False, workspaces=["missing"])

    def fake_select_workspaces(
        _resolved: ResolvedConfig, _workspaces: list[str]
    ) -> list[Workspace]:
        raise mainmod.ConfigError("unknown workspace")

    _patch_main_context(monkeypatch, ctx=ctx, resolved=_resolved_config())
    monkeypatch.setattr(mainmod, "select_workspaces", fake_select_workspaces)

    with pytest.raises(SystemExit) as excinfo:
        mainmod.main()

    assert excinfo.value.code == 1
    assert "unknown workspace" in capsys.readouterr().err


def test_main_dispatches_deploy_all_workspaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _deploy_ctx(verbose=True)

    class _DeployCall(TypedDict):
        workspaces: list[Workspace]
        path: str
        dry_run: bool
        verbose: bool

    run_deploy_mock = AsyncMock(spec=mainmod.run_deploy)
    monkeypatch.setattr(mainmod, "run_deploy", run_deploy_mock)
    _patch_main_context(monkeypatch, ctx=ctx, resolved=_resolved_config())

    mainmod.main()

    assert run_deploy_mock.call_count == 1
    deploy_call = cast(_DeployCall, run_deploy_mock.call_args.kwargs)
    workspaces = deploy_call["workspaces"]
    names = [ws.name for ws in workspaces]
    assert names == ["alpha", "zeta"]
    assert deploy_call["path"] == DEFAULT_PATH
    assert deploy_call["dry_run"] is False
    assert deploy_call["verbose"] is True


def test_main_dispatches_deploy_selected_workspaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _deploy_ctx(all_workspaces=False, workspaces=["alpha", "zeta"])
    resolved = _resolved_config()
    selected = [
        make_workspace("alpha", "/alpha"),
        make_workspace("zeta", "/zeta"),
    ]

    select_workspaces_mock = create_autospec(
        mainmod.select_workspaces, return_value=selected
    )
    select_all_workspaces_mock = create_autospec(
        mainmod.select_all_workspaces,
        side_effect=AssertionError("select_all_workspaces should not run"),
    )
    run_deploy_mock = AsyncMock(spec=mainmod.run_deploy)
    monkeypatch.setattr(mainmod, "select_workspaces", select_workspaces_mock)
    monkeypatch.setattr(mainmod, "select_all_workspaces", select_all_workspaces_mock)
    monkeypatch.setattr(mainmod, "run_deploy", run_deploy_mock)
    _patch_main_context(monkeypatch, ctx=ctx, resolved=resolved)

    mainmod.main()

    select_workspaces_mock.assert_called_once_with(resolved, ["alpha", "zeta"])
    deploy_call = run_deploy_mock.call_args.kwargs
    assert deploy_call["workspaces"] == selected
    assert deploy_call["path"] == DEFAULT_PATH
    assert deploy_call["dry_run"] is False
    assert deploy_call["verbose"] is False


def test_main_dispatches_adopt_workspace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx: AdoptContext = _adopt_ctx(dry_run=True, verbose=True)

    class _AdoptCall(TypedDict):
        workspace: Workspace
        path: str
        dry_run: bool
        verbose: bool

    run_adopt_mock = AsyncMock(spec=mainmod.run_adopt)
    monkeypatch.setattr(mainmod, "run_adopt", run_adopt_mock)
    _patch_main_context(monkeypatch, ctx=ctx, resolved=_resolved_config())

    mainmod.main()

    assert run_adopt_mock.call_count == 1
    adopt_call = cast(_AdoptCall, run_adopt_mock.call_args.kwargs)
    assert adopt_call["workspace"].name == "alpha"
    assert adopt_call["path"] == "docs"
    assert adopt_call["dry_run"] is True
    assert adopt_call["verbose"] is True


CONFIG_PATH = Path("/config.yaml")


def _deploy_ctx(
    all_workspaces: bool = True,
    workspaces: list[str] | None = None,
    path: str = DEFAULT_PATH,
    dry_run: bool = False,
    verbose: bool = False,
) -> DeployContext:
    return DeployContext(
        command="deploy",
        config_path=CONFIG_PATH,
        all_workspaces=all_workspaces,
        workspaces=workspaces or [],
        path=path,
        dry_run=dry_run,
        verbose=verbose,
    )


def _adopt_ctx(
    workspace: str = "alpha",
    path: str = "docs",
    dry_run: bool = False,
    verbose: bool = False,
) -> AdoptContext:
    return AdoptContext(
        command="adopt",
        config_path=CONFIG_PATH,
        workspace=workspace,
        path=path,
        dry_run=dry_run,
        verbose=verbose,
    )


def _resolved_config() -> ResolvedConfig:
    return ResolvedConfig(
        origin=make_workspace("", "/origin"),
        workspaces={
            "zeta": make_workspace("zeta", "/zeta"),
            "alpha": make_workspace("alpha", "/alpha"),
        },
    )


def _patch_main_context(
    monkeypatch: pytest.MonkeyPatch,
    ctx: AdoptContext | DeployContext,
    resolved: ResolvedConfig,
) -> None:
    monkeypatch.setattr(
        mainmod,
        "parse_cli",
        create_autospec(mainmod.parse_cli, return_value=ctx),
    )
    monkeypatch.setattr(
        mainmod,
        "load_config",
        create_autospec(mainmod.load_config, return_value={}),
    )
    monkeypatch.setattr(
        mainmod,
        "resolve_config",
        create_autospec(mainmod.resolve_config, return_value=resolved),
    )
