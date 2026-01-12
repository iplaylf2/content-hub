from __future__ import annotations

from pathlib import Path
import pytest

from contentctl.cli_parser import AdoptContext, DeployContext, parse_cli


def test_parse_cli_deploy_workspace(tmp_path: Path) -> None:
    ctx = parse_cli(["deploy", "docs", "--path", "api"], tmp_path)

    assert isinstance(ctx, DeployContext)
    assert ctx.command == "deploy"
    assert ctx.workspaces == ["docs"]
    assert ctx.all_workspaces is False
    assert ctx.path == "api"
    assert ctx.config_path == (tmp_path / "content-hub.yaml").resolve()


def test_parse_cli_deploy_all_workspaces(tmp_path: Path) -> None:
    ctx = parse_cli(["deploy", "--all-workspaces"], tmp_path)

    assert isinstance(ctx, DeployContext)
    assert ctx.command == "deploy"
    assert ctx.workspaces == []
    assert ctx.all_workspaces is True
    assert ctx.path == "."


def test_parse_cli_adopt_workspace(tmp_path: Path) -> None:
    ctx = parse_cli(["adopt", "docs"], tmp_path)

    assert isinstance(ctx, AdoptContext)
    assert ctx.command == "adopt"
    assert ctx.workspace == "docs"
    assert ctx.path == "."


def test_parse_cli_rejects_both_deploy_targets(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        parse_cli(["deploy", "docs", "--all-workspaces"], tmp_path)

    assert excinfo.value.code == 2


def test_parse_cli_requires_deploy_target(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        parse_cli(["deploy"], tmp_path)

    assert excinfo.value.code == 2


def test_parse_cli_rejects_empty_path(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        parse_cli(["deploy", "docs", "--path", "   "], tmp_path)

    assert excinfo.value.code == 2


def test_parse_cli_rejects_empty_workspace_adopt(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        parse_cli(["adopt", ""], tmp_path)

    assert excinfo.value.code == 2
