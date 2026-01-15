from pathlib import Path
import pytest

from tests.contentctl.fixtures import DEFAULT_CONFIG_NAME, DEFAULT_PATH
from contentctl.cli_parser import AdoptContext, DeployContext, parse_cli


@pytest.mark.parametrize(
    (
        "argv",
        "ctx_type",
        "command",
        "path",
        "all_workspaces",
        "workspaces",
        "workspace",
    ),
    [
        (
            ["deploy", "docs", "--path", "api"],
            DeployContext,
            "deploy",
            "api",
            False,
            ["docs"],
            None,
        ),
        (
            ["deploy", "--all-workspaces"],
            DeployContext,
            "deploy",
            DEFAULT_PATH,
            True,
            [],
            None,
        ),
        (["adopt", "docs"], AdoptContext, "adopt", DEFAULT_PATH, None, None, "docs"),
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
    workspace: str | None,
) -> None:
    ctx = parse_cli(argv, tmp_path)

    assert isinstance(ctx, ctx_type)
    assert ctx.command == command
    assert ctx.path == path
    assert ctx.config_path == (tmp_path / DEFAULT_CONFIG_NAME).resolve()
    if isinstance(ctx, DeployContext):
        assert ctx.all_workspaces is all_workspaces
        assert ctx.workspaces == workspaces
    else:
        assert ctx.workspace == workspace


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
    with pytest.raises(SystemExit):
        parse_cli(argv, tmp_path)


@pytest.mark.parametrize(
    ("config_arg", "use_absolute"),
    [
        ("config.yaml", False),
        ("custom/path/config.yaml", False),
        ("config.yaml", True),
    ],
)
def test_parse_cli_accepts_config_path(
    tmp_path: Path,
    config_arg: str,
    use_absolute: bool,
) -> None:
    config_path = tmp_path / config_arg
    arg = str(config_path) if use_absolute else config_arg
    ctx = parse_cli(["--config", arg, "deploy", "docs"], tmp_path)

    if use_absolute:
        assert ctx.config_path == config_path.resolve()
    else:
        assert ctx.config_path == (tmp_path / config_arg).resolve()


@pytest.mark.parametrize(
    ("flags", "expected_dry_run", "expected_verbose"),
    [
        (["--dry-run", "--verbose"], True, True),
        (["--dry-run"], True, False),
        (["--verbose"], False, True),
        ([], False, False),
    ],
)
def test_parse_cli_sets_flags(
    tmp_path: Path,
    flags: list[str],
    expected_dry_run: bool,
    expected_verbose: bool,
) -> None:
    ctx = parse_cli([*flags, "deploy", "docs"], tmp_path)

    assert ctx.dry_run is expected_dry_run
    assert ctx.verbose is expected_verbose
