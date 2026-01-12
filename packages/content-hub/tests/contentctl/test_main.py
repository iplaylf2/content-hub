from __future__ import annotations

from pathlib import Path
from typing import TypedDict, cast

import pytest

from contentctl.cli_parser import DeployContext
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

    def fake_parse_cli(_argv: list[str], _cwd: Path) -> DeployContext:
        return ctx

    def fake_load_config(_path: Path) -> dict[str, object]:
        return {}

    def fake_resolve_config(_cfg: dict[str, object], _path: Path) -> ResolvedConfig:
        return _resolved_config()

    monkeypatch.setattr(mainmod, "parse_cli", fake_parse_cli)
    monkeypatch.setattr(mainmod, "load_config", fake_load_config)
    monkeypatch.setattr(mainmod, "resolve_config", fake_resolve_config)

    def raise_sync_error(_ctx: object, _resolved: object) -> None:
        raise mainmod.SyncError("sync failed")

    monkeypatch.setattr(mainmod, "_dispatch", raise_sync_error)

    with pytest.raises(SystemExit) as excinfo:
        mainmod.main()

    assert excinfo.value.code == 1
    assert "sync failed" in capsys.readouterr().err


def test_main_dispatches_deploy_all_workspaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _deploy_ctx(verbose=True)

    def fake_parse_cli(_argv: list[str], _cwd: Path) -> DeployContext:
        return ctx

    def fake_load_config(_path: Path) -> dict[str, object]:
        return {}

    def fake_resolve_config(_cfg: dict[str, object], _path: Path) -> ResolvedConfig:
        return _resolved_config()

    class _DeployCall(TypedDict):
        workspaces: list[Workspace]
        path: str
        dry_run: bool
        verbose: bool

    called: list[_DeployCall] = []

    def fake_run_deploy(**kwargs: object) -> None:
        called.append(cast(_DeployCall, kwargs))

    monkeypatch.setattr(mainmod, "parse_cli", fake_parse_cli)
    monkeypatch.setattr(mainmod, "load_config", fake_load_config)
    monkeypatch.setattr(mainmod, "resolve_config", fake_resolve_config)
    monkeypatch.setattr(mainmod, "run_deploy", fake_run_deploy)

    mainmod.main()

    assert len(called) == 1
    deploy_call = called[0]
    workspaces = deploy_call["workspaces"]
    names = [ws.name for ws in workspaces]
    assert names == ["alpha", "zeta"]
    assert deploy_call["path"] == "."
    assert deploy_call["dry_run"] is False
    assert deploy_call["verbose"] is True


def _deploy_ctx(
    *,
    all_workspaces: bool = True,
    workspaces: list[str] | None = None,
    path: str = ".",
    dry_run: bool = False,
    verbose: bool = False,
) -> DeployContext:
    return DeployContext(
        command="deploy",
        config_path=Path("/config.yaml"),
        all_workspaces=all_workspaces,
        workspaces=workspaces or [],
        path=path,
        dry_run=dry_run,
        verbose=verbose,
    )


def _resolved_config() -> ResolvedConfig:
    return ResolvedConfig(
        origin=Workspace(name="", path=Path("/origin"), include=(), exclude=()),
        workspaces={
            "zeta": Workspace(name="zeta", path=Path("/zeta"), include=(), exclude=()),
            "alpha": Workspace(
                name="alpha", path=Path("/alpha"), include=(), exclude=()
            ),
        },
    )
