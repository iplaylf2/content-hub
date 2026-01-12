from __future__ import annotations

from pathlib import Path
import pytest

from contentctl.cli_parser import AdoptContext, DeployContext, parse_cli


@pytest.mark.parametrize(
    ("argv", "ctx_type", "command", "path", "all_workspaces", "workspaces"),
    [
        (
            ["deploy", "docs", "--path", "api"],
            DeployContext,
            "deploy",
            "api",
            False,
            ["docs"],
        ),
        (["deploy", "--all-workspaces"], DeployContext, "deploy", ".", True, []),
        (["adopt", "docs"], AdoptContext, "adopt", ".", None, None),
    ],
)
def test_parse_cli_success(
    tmp_path: Path,
    argv: list[str],
    ctx_type: type[DeployContext | AdoptContext],
    command: str,
    path: str,
    all_workspaces: bool | None,
    workspaces: list[str] | None,
) -> None:
    ctx = parse_cli(argv, tmp_path)

    assert isinstance(ctx, ctx_type)
    assert ctx.command == command
    assert ctx.path == path
    assert ctx.config_path == (tmp_path / "content-hub.yaml").resolve()
    if isinstance(ctx, DeployContext):
        assert ctx.all_workspaces is all_workspaces
        assert ctx.workspaces == workspaces
    else:
        assert ctx.workspace == "docs"


@pytest.mark.parametrize(
    "argv",
    [
        ["deploy", "docs", "--all-workspaces"],
        ["deploy"],
        ["deploy", ""],
        ["deploy", "docs", "--path", "   "],
        ["adopt", ""],
    ],
)
def test_parse_cli_rejects_invalid_args(tmp_path: Path, argv: list[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        parse_cli(argv, tmp_path)

    assert excinfo.value.code == 2


def test_parse_cli_accepts_absolute_config_path(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    ctx = parse_cli(["--config", str(config_path), "deploy", "docs"], tmp_path)

    assert ctx.config_path == config_path.resolve()
