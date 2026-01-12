from __future__ import annotations

from pathlib import Path

import pytest

from contentctl.cli_parser import DeployContext
from contentctl.config import ResolvedConfig, Workspace
import contentctl.__main__ as mainmod


def test_main_exits_on_config_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ctx = DeployContext(
        command="deploy",
        config_path=Path("/config.yaml"),
        all_workspaces=True,
        workspaces=[],
        path=".",
        dry_run=False,
        verbose=False,
    )

    def fake_parse_cli(_argv: list[str], _cwd: Path) -> DeployContext:
        return ctx

    monkeypatch.setattr(mainmod, "parse_cli", fake_parse_cli)

    def raise_config_error(_config_path: Path) -> None:
        raise mainmod.ConfigError("bad config")

    monkeypatch.setattr(mainmod, "load_config", raise_config_error)

    with pytest.raises(SystemExit) as excinfo:
        mainmod.main()

    assert excinfo.value.code == 2
    assert "bad config" in capsys.readouterr().err


def test_main_exits_on_resolve_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ctx = DeployContext(
        command="deploy",
        config_path=Path("/config.yaml"),
        all_workspaces=True,
        workspaces=[],
        path=".",
        dry_run=False,
        verbose=False,
    )

    def fake_parse_cli(_argv: list[str], _cwd: Path) -> DeployContext:
        return ctx

    def fake_load_config(_path: Path) -> dict[str, object]:
        return {}

    def raise_config_error(_config: dict[str, object], _path: Path) -> ResolvedConfig:
        raise mainmod.ConfigError("resolve failed")

    monkeypatch.setattr(mainmod, "parse_cli", fake_parse_cli)
    monkeypatch.setattr(mainmod, "load_config", fake_load_config)
    monkeypatch.setattr(mainmod, "resolve_config", raise_config_error)

    with pytest.raises(SystemExit) as excinfo:
        mainmod.main()

    assert excinfo.value.code == 2
    assert "resolve failed" in capsys.readouterr().err


def test_main_exits_on_sync_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ctx = DeployContext(
        command="deploy",
        config_path=Path("/config.yaml"),
        all_workspaces=True,
        workspaces=[],
        path=".",
        dry_run=False,
        verbose=False,
    )

    def fake_parse_cli(_argv: list[str], _cwd: Path) -> DeployContext:
        return ctx

    def fake_load_config(_path: Path) -> dict[str, object]:
        return {}

    def fake_resolve_config(_cfg: dict[str, object], _path: Path) -> ResolvedConfig:
        return ResolvedConfig(
            origin=Workspace(name="", path=Path("/origin"), include=(), exclude=()),
            workspaces={},
        )

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
