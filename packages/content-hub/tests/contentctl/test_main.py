from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Protocol
from unittest.mock import create_autospec

import contentctl.__main__ as mainmod
import pytest
from contentctl.config import ResolvedConfig
from contentctl.gateway import AdoptContext, DeployContext, InitContext
from contentctl.gateway.defaults import DEFAULT_CONFIG_FILENAME

if TYPE_CHECKING:
    from .fixture_types import MakeWorkspace

type DeployCtxFactory = Callable[..., DeployContext]
type AdoptCtxFactory = Callable[..., AdoptContext]


class PatchMainContext(Protocol):
    def __call__(
        self, *, ctx: AdoptContext | DeployContext, resolved: ResolvedConfig
    ) -> None: ...


@pytest.fixture
def config_path() -> Path:
    """Config path for main tests."""
    return Path("/config.yaml")


@pytest.fixture
def deploy_ctx(config_path: Path) -> DeployCtxFactory:
    """Create DeployContext for testing."""

    def _make(
        workspaces: list[str] | None = None,
        path: str = ".",
        *,
        all_workspaces: bool = True,
        dry_run: bool = False,
        verbose: bool = False,
        allow_delete: bool = False,
    ) -> DeployContext:
        return DeployContext(
            command="deploy",
            config_path=config_path,
            all_workspaces=all_workspaces,
            workspaces=workspaces or [],
            path=path,
            dry_run=dry_run,
            verbose=verbose,
            allow_delete=allow_delete,
        )

    return _make


@pytest.fixture
def adopt_ctx(config_path: Path) -> AdoptCtxFactory:
    """Create AdoptContext for testing."""

    def _make(
        workspace: str = "alpha",
        path: str = "docs",
        *,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> AdoptContext:
        return AdoptContext(
            command="adopt",
            config_path=config_path,
            workspace=workspace,
            path=path,
            dry_run=dry_run,
            verbose=verbose,
        )

    return _make


@pytest.fixture
def resolved_config(make_workspace: MakeWorkspace) -> ResolvedConfig:
    """Create a resolved config for testing."""
    return ResolvedConfig(
        origin=make_workspace("", "/origin"),
        workspaces={
            "zeta": make_workspace("zeta", "/zeta"),
            "alpha": make_workspace("alpha", "/alpha"),
        },
    )


@pytest.fixture
def patch_main_context(
    monkeypatch: pytest.MonkeyPatch,
) -> PatchMainContext:
    """Patch main context loading functions."""

    def _patch(
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

    return _patch


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
    deploy_ctx: DeployCtxFactory,
    resolved_config: ResolvedConfig,
    failure: str,
    message: str,
) -> None:
    ctx = deploy_ctx()

    def load_config_side_effect(_path: Path) -> dict[str, object]:
        if failure == "load_config":
            raise mainmod.ConfigError(message)
        return {}

    def resolve_config_side_effect(
        _cfg: dict[str, object], _path: Path
    ) -> ResolvedConfig:
        if failure == "resolve_config":
            raise mainmod.ConfigError(message)
        return resolved_config

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
    deploy_ctx: DeployCtxFactory,
    resolved_config: ResolvedConfig,
    patch_main_context: PatchMainContext,
    message: str,
) -> None:
    ctx = deploy_ctx()
    patch_main_context(ctx=ctx, resolved=resolved_config)

    async def raise_sync_error(*_args: object, **_kwargs: object) -> None:
        raise mainmod.SyncError(message)

    monkeypatch.setattr(mainmod, "run_deploy", raise_sync_error)

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
    deploy_ctx: DeployCtxFactory,
    resolved_config: ResolvedConfig,
    patch_main_context: PatchMainContext,
    workspaces: list[str],
    message: str,
) -> None:
    ctx = deploy_ctx(all_workspaces=False, workspaces=workspaces)

    select_workspaces_mock = create_autospec(
        mainmod.select_workspaces, side_effect=mainmod.ConfigError(message)
    )

    patch_main_context(ctx=ctx, resolved=resolved_config)
    monkeypatch.setattr(mainmod, "select_workspaces", select_workspaces_mock)

    with pytest.raises(SystemExit) as excinfo:
        mainmod.main()

    assert excinfo.value.code == 1
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    ("verbose", "delete"),
    [
        (True, True),
        (True, False),
        (False, True),
        (False, False),
    ],
)
def test_main_dispatches_deploy_with_flags(
    monkeypatch: pytest.MonkeyPatch,
    deploy_ctx: DeployCtxFactory,
    resolved_config: ResolvedConfig,
    patch_main_context: PatchMainContext,
    *,
    verbose: bool,
    delete: bool,
) -> None:
    ctx = deploy_ctx(verbose=verbose, allow_delete=delete)

    run_deploy_mock = create_autospec(mainmod.run_deploy)
    monkeypatch.setattr(mainmod, "run_deploy", run_deploy_mock)
    patch_main_context(ctx=ctx, resolved=resolved_config)

    mainmod.main()

    run_deploy_mock.assert_called_once()
    call_kwargs = run_deploy_mock.call_args.kwargs
    assert "workspaces" in call_kwargs
    assert call_kwargs["verbose"] is verbose
    assert call_kwargs["allow_delete"] is delete


@pytest.mark.parametrize(
    ("workspaces", "workspace_root_prefix"),
    [
        (["alpha", "zeta"], "/"),
    ],
)
def test_main_dispatches_deploy_selected_workspaces(
    monkeypatch: pytest.MonkeyPatch,
    deploy_ctx: DeployCtxFactory,
    make_workspace: MakeWorkspace,
    resolved_config: ResolvedConfig,
    patch_main_context: PatchMainContext,
    workspaces: list[str],
    workspace_root_prefix: str,
) -> None:
    ctx = deploy_ctx(all_workspaces=False, workspaces=workspaces)
    selected = [
        make_workspace(name, f"{workspace_root_prefix}{name}") for name in workspaces
    ]

    select_workspaces_mock = create_autospec(
        mainmod.select_workspaces, return_value=selected
    )
    select_all_workspaces_mock = create_autospec(
        mainmod.select_all_workspaces,
        side_effect=AssertionError("select_all_workspaces should not run"),
    )
    run_deploy_mock = create_autospec(mainmod.run_deploy)
    monkeypatch.setattr(mainmod, "select_workspaces", select_workspaces_mock)
    monkeypatch.setattr(mainmod, "select_all_workspaces", select_all_workspaces_mock)
    monkeypatch.setattr(mainmod, "run_deploy", run_deploy_mock)
    patch_main_context(ctx=ctx, resolved=resolved_config)

    mainmod.main()

    select_workspaces_mock.assert_called_once_with(resolved_config, workspaces)
    run_deploy_mock.assert_called_once()


@pytest.mark.parametrize(
    ("workspace_name", "workspace_path", "dry_run", "verbose"),
    [
        ("alpha", "docs", True, True),
        ("alpha", "docs", True, False),
        ("alpha", "docs", False, True),
        ("alpha", "docs", False, False),
    ],
)
def test_main_dispatches_adopt_workspace(
    monkeypatch: pytest.MonkeyPatch,
    adopt_ctx: AdoptCtxFactory,
    resolved_config: ResolvedConfig,
    patch_main_context: PatchMainContext,
    workspace_name: str,
    workspace_path: str,
    *,
    dry_run: bool,
    verbose: bool,
) -> None:
    ctx: AdoptContext = adopt_ctx(
        workspace=workspace_name,
        path=workspace_path,
        dry_run=dry_run,
        verbose=verbose,
    )

    run_adopt_mock = create_autospec(mainmod.run_adopt)
    monkeypatch.setattr(mainmod, "run_adopt", run_adopt_mock)
    patch_main_context(ctx=ctx, resolved=resolved_config)

    mainmod.main()

    run_adopt_mock.assert_called_once()
    call_kwargs = run_adopt_mock.call_args.kwargs
    assert "workspace" in call_kwargs
    assert call_kwargs["dry_run"] is dry_run
    assert call_kwargs["verbose"] is verbose


@pytest.mark.parametrize(
    ("init_path", "config_filename"),
    [
        (Path("/init"), DEFAULT_CONFIG_FILENAME),
    ],
)
def test_main_runs_init_success(
    monkeypatch: pytest.MonkeyPatch,
    config_path: Path,
    init_path: Path,
    config_filename: str,
) -> None:
    ctx = InitContext(
        command="init",
        config_path=config_path,
        config_filename=config_filename,
        path=init_path,
        dry_run=False,
        verbose=False,
    )

    parse_cli_mock = create_autospec(mainmod.parse_cli, return_value=ctx)
    run_init_mock = create_autospec(mainmod.run_init)

    monkeypatch.setattr(mainmod, "parse_cli", parse_cli_mock)
    monkeypatch.setattr(mainmod, "run_init", run_init_mock)

    mainmod.main()

    run_init_mock.assert_called_once()
    call_kwargs = run_init_mock.call_args.kwargs
    assert call_kwargs["path"] == ctx.path
    assert call_kwargs["config_filename"] == ctx.config_filename


@pytest.mark.parametrize(
    ("exc_type", "message", "init_path", "config_filename"),
    [
        (FileExistsError, "already exists", Path("/init"), DEFAULT_CONFIG_FILENAME),
        (mainmod.ConfigError, "bad config", Path("/init"), DEFAULT_CONFIG_FILENAME),
    ],
)
def test_main_exits_on_init_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    config_path: Path,
    exc_type: type[Exception],
    message: str,
    init_path: Path,
    config_filename: str,
) -> None:
    ctx = InitContext(
        command="init",
        config_path=config_path,
        config_filename=config_filename,
        path=init_path,
        dry_run=False,
        verbose=False,
    )

    def raise_error(*_args: object, **_kwargs: object) -> None:
        raise exc_type(message)

    parse_cli_mock = create_autospec(mainmod.parse_cli, return_value=ctx)
    run_init_mock = create_autospec(mainmod.run_init, side_effect=raise_error)

    monkeypatch.setattr(mainmod, "parse_cli", parse_cli_mock)
    monkeypatch.setattr(mainmod, "run_init", run_init_mock)

    with pytest.raises(SystemExit) as excinfo:
        mainmod.main()

    assert excinfo.value.code == 1
    assert message in capsys.readouterr().err
