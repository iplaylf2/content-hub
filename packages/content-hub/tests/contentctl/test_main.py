from pathlib import Path
from unittest.mock import AsyncMock, create_autospec

import pytest

from tests.contentctl.fixtures import DEFAULT_PATH, make_workspace
from contentctl.cli_parser import AdoptContext, DeployContext
from contentctl.config import ResolvedConfig
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

    def load_config_side_effect(_path: Path) -> dict[str, object]:
        if failure == "load_config":
            raise mainmod.ConfigError(message)
        return {}

    def resolve_config_side_effect(
        _cfg: dict[str, object], _path: Path
    ) -> ResolvedConfig:
        if failure == "resolve_config":
            raise mainmod.ConfigError(message)
        return _resolved_config()

    parse_cli_mock = create_autospec(mainmod.parse_cli, return_value=ctx)
    load_config_mock = create_autospec(
        mainmod.load_config, side_effect=load_config_side_effect
    )
    resolve_config_mock = create_autospec(
        mainmod.resolve_config, side_effect=resolve_config_side_effect
    )

    monkeypatch.setattr(mainmod, "parse_cli", parse_cli_mock)
    monkeypatch.setattr(mainmod, "load_config", load_config_mock)
    monkeypatch.setattr(mainmod, "resolve_config", resolve_config_mock)

    with pytest.raises(SystemExit) as excinfo:
        mainmod.main()

    assert excinfo.value.code == 2
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    "message",
    [
        "sync failed",
        "operation error",
    ],
)
def test_main_exits_on_sync_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    message: str,
) -> None:
    ctx = _deploy_ctx()
    _patch_main_context(monkeypatch, ctx=ctx, resolved=_resolved_config())

    async def raise_sync_error(_ctx: object, _resolved: object) -> None:
        raise mainmod.SyncError(message)

    monkeypatch.setattr(mainmod, "_dispatch", raise_sync_error)

    with pytest.raises(SystemExit) as excinfo:
        mainmod.main()

    assert excinfo.value.code == 1
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    ("workspaces", "message"),
    [
        (["missing"], "unknown workspace"),
        (["invalid", "notfound"], "unknown workspace"),
    ],
)
def test_main_exits_on_dispatch_config_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    workspaces: list[str],
    message: str,
) -> None:
    ctx = _deploy_ctx(all_workspaces=False, workspaces=workspaces)

    select_workspaces_mock = create_autospec(
        mainmod.select_workspaces, side_effect=mainmod.ConfigError(message)
    )

    _patch_main_context(monkeypatch, ctx=ctx, resolved=_resolved_config())
    monkeypatch.setattr(mainmod, "select_workspaces", select_workspaces_mock)

    with pytest.raises(SystemExit) as excinfo:
        mainmod.main()

    assert excinfo.value.code == 1
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    "verbose",
    [True, False],
)
def test_main_dispatches_deploy_all_workspaces(
    monkeypatch: pytest.MonkeyPatch,
    verbose: bool,
) -> None:
    ctx = _deploy_ctx(verbose=verbose)

    run_deploy_mock = AsyncMock(spec=mainmod.run_deploy)
    monkeypatch.setattr(mainmod, "run_deploy", run_deploy_mock)
    _patch_main_context(monkeypatch, ctx=ctx, resolved=_resolved_config())

    mainmod.main()

    assert run_deploy_mock.call_count == 1
    assert "workspaces" in run_deploy_mock.call_args.kwargs


@pytest.mark.parametrize(
    "workspaces",
    [
        ["alpha", "zeta"],
    ],
)
def test_main_dispatches_deploy_selected_workspaces(
    monkeypatch: pytest.MonkeyPatch,
    workspaces: list[str],
) -> None:
    ctx = _deploy_ctx(all_workspaces=False, workspaces=workspaces)
    resolved = _resolved_config()
    selected = [make_workspace(name, f"/{name}") for name in workspaces]

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

    select_workspaces_mock.assert_called_once_with(resolved, workspaces)
    assert run_deploy_mock.call_count == 1


@pytest.mark.parametrize(
    ("dry_run", "verbose"),
    [
        (True, True),
        (True, False),
        (False, True),
        (False, False),
    ],
)
def test_main_dispatches_adopt_workspace(
    monkeypatch: pytest.MonkeyPatch,
    dry_run: bool,
    verbose: bool,
) -> None:
    ctx: AdoptContext = _adopt_ctx(dry_run=dry_run, verbose=verbose)

    run_adopt_mock = AsyncMock(spec=mainmod.run_adopt)
    monkeypatch.setattr(mainmod, "run_adopt", run_adopt_mock)
    _patch_main_context(monkeypatch, ctx=ctx, resolved=_resolved_config())

    mainmod.main()

    assert run_adopt_mock.call_count == 1
    assert "workspace" in run_adopt_mock.call_args.kwargs


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
