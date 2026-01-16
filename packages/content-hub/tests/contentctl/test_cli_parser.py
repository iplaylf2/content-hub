from pathlib import Path

import pytest

from contentctl.cli_parser import AdoptContext, DeployContext, parse_cli


DEFAULT_CONFIG_NAME = "content-hub.yaml"


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
            ["deploy", "virtual-workspace", "--path", "virtual-subdir"],
            DeployContext,
            "deploy",
            "virtual-subdir",
            False,
            ["virtual-workspace"],
            None,
        ),
        (
            ["deploy", "--all-workspaces"],
            DeployContext,
            "deploy",
            ".",
            True,
            [],
            None,
        ),
        (
            ["adopt", "virtual-workspace"],
            AdoptContext,
            "adopt",
            ".",
            None,
            None,
            "virtual-workspace",
        ),
    ],
)
def test_parse_cli_success(
    fixture_dir: Path,
    argv: list[str],
    ctx_type: type[DeployContext | AdoptContext],
    command: str,
    path: str,
    all_workspaces: bool | None,
    workspaces: list[str] | None,
    workspace: str | None,
) -> None:
    ctx = parse_cli(argv, fixture_dir)

    assert isinstance(ctx, ctx_type)
    assert ctx.command == command
    assert ctx.path == path
    assert ctx.config_path == (fixture_dir / DEFAULT_CONFIG_NAME).resolve()
    if isinstance(ctx, DeployContext):
        assert ctx.all_workspaces is all_workspaces
        assert ctx.workspaces == workspaces
    else:
        assert ctx.workspace == workspace


@pytest.mark.parametrize(
    "argv",
    [
        ["deploy", "virtual-workspace", "--all-workspaces"],
        ["deploy"],
        ["deploy", ""],
        ["deploy", "virtual-workspace", "--path", "   "],
        ["adopt", ""],
    ],
)
def test_parse_cli_rejects_invalid_args(fixture_dir: Path, argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        parse_cli(argv, fixture_dir)


@pytest.mark.parametrize(
    ("config_arg", "use_absolute"),
    [
        ("config.yaml", False),
        ("custom/path/config.yaml", False),
        ("config.yaml", True),
    ],
)
def test_parse_cli_accepts_config_path(
    fixture_dir: Path,
    config_arg: str,
    use_absolute: bool,
) -> None:
    config_path = fixture_dir / config_arg
    arg = str(config_path) if use_absolute else config_arg
    ctx = parse_cli(["--config", arg, "deploy", "virtual-workspace"], fixture_dir)

    if use_absolute:
        assert ctx.config_path == config_path.resolve()
    else:
        assert ctx.config_path == (fixture_dir / config_arg).resolve()


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
    fixture_dir: Path,
    flags: list[str],
    expected_dry_run: bool,
    expected_verbose: bool,
) -> None:
    ctx = parse_cli([*flags, "deploy", "virtual-workspace"], fixture_dir)

    assert ctx.dry_run is expected_dry_run
    assert ctx.verbose is expected_verbose


@pytest.mark.parametrize(
    ("argv", "expected_delete"),
    [
        (["deploy", "virtual-workspace", "--delete"], True),
        (["deploy", "virtual-workspace"], False),
    ],
)
def test_parse_cli_sets_delete_flag(
    fixture_dir: Path,
    argv: list[str],
    expected_delete: bool,
) -> None:
    ctx = parse_cli(argv, fixture_dir)

    assert isinstance(ctx, DeployContext)
    assert ctx.allow_delete is expected_delete
