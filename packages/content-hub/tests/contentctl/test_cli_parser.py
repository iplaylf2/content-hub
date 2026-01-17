from pathlib import Path

import pytest

from contentctl.cli_parser import AdoptContext, DeployContext, parse_cli


DEFAULT_CONFIG_NAME = "content-hub.yaml"
VIRTUAL_WORKSPACE = "virtual-workspace"
VIRTUAL_SUBDIR = "virtual-subdir"
VIRTUAL_CONFIG_NAME = "virtual-config.yaml"


@pytest.mark.parametrize(
    (
        "argv",
        "ctx_type",
        "command",
        "path",
        "all_workspaces",
        "workspaces",
        "workspace",
        "config_name",
    ),
    [
        (
            ["deploy", VIRTUAL_WORKSPACE, "--path", VIRTUAL_SUBDIR],
            DeployContext,
            "deploy",
            VIRTUAL_SUBDIR,
            False,
            [VIRTUAL_WORKSPACE],
            None,
            DEFAULT_CONFIG_NAME,
        ),
        (
            ["deploy", "--all-workspaces"],
            DeployContext,
            "deploy",
            ".",
            True,
            [],
            None,
            DEFAULT_CONFIG_NAME,
        ),
        (
            ["adopt", VIRTUAL_WORKSPACE],
            AdoptContext,
            "adopt",
            ".",
            None,
            None,
            VIRTUAL_WORKSPACE,
            DEFAULT_CONFIG_NAME,
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
    config_name: str,
) -> None:
    ctx = parse_cli(argv, fixture_dir)

    assert isinstance(ctx, ctx_type)
    assert ctx.command == command
    assert ctx.path == path
    assert ctx.config_path == (fixture_dir / config_name).resolve()
    if isinstance(ctx, DeployContext):
        assert ctx.all_workspaces is all_workspaces
        assert ctx.workspaces == workspaces
    else:
        assert ctx.workspace == workspace


@pytest.mark.parametrize(
    "argv",
    [
        ["deploy", VIRTUAL_WORKSPACE, "--all-workspaces"],
        ["deploy"],
        ["deploy", ""],
        ["deploy", VIRTUAL_WORKSPACE, "--path", "   "],
        ["adopt", ""],
    ],
)
def test_parse_cli_rejects_invalid_args(fixture_dir: Path, argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        parse_cli(argv, fixture_dir)


@pytest.mark.parametrize(
    ("config_arg", "use_absolute", "workspace"),
    [
        (VIRTUAL_CONFIG_NAME, False, VIRTUAL_WORKSPACE),
        ("virtual/custom/path/config.yaml", False, VIRTUAL_WORKSPACE),
        (VIRTUAL_CONFIG_NAME, True, VIRTUAL_WORKSPACE),
    ],
)
def test_parse_cli_accepts_config_path(
    fixture_dir: Path,
    config_arg: str,
    use_absolute: bool,
    workspace: str,
) -> None:
    config_path = fixture_dir / config_arg
    arg = str(config_path) if use_absolute else config_arg
    ctx = parse_cli(["--config", arg, "deploy", workspace], fixture_dir)

    if use_absolute:
        assert ctx.config_path == config_path.resolve()
    else:
        assert ctx.config_path == (fixture_dir / config_arg).resolve()


@pytest.mark.parametrize(
    (
        "pre_flags",
        "post_flags",
        "workspace",
        "expected_dry_run",
        "expected_verbose",
        "expected_delete",
    ),
    [
        (["--dry-run", "--verbose"], [], VIRTUAL_WORKSPACE, True, True, False),
        (["--dry-run"], [], VIRTUAL_WORKSPACE, True, False, False),
        (["--verbose"], [], VIRTUAL_WORKSPACE, False, True, False),
        ([], ["--delete"], VIRTUAL_WORKSPACE, False, False, True),
        ([], [], VIRTUAL_WORKSPACE, False, False, False),
        (["--dry-run"], ["--delete"], VIRTUAL_WORKSPACE, True, False, True),
    ],
)
def test_parse_cli_sets_flags(
    fixture_dir: Path,
    pre_flags: list[str],
    post_flags: list[str],
    workspace: str,
    expected_dry_run: bool,
    expected_verbose: bool,
    expected_delete: bool,
) -> None:
    ctx = parse_cli(
        [*pre_flags, "deploy", workspace, *post_flags],
        fixture_dir,
    )

    assert isinstance(ctx, DeployContext)
    assert ctx.dry_run is expected_dry_run
    assert ctx.verbose is expected_verbose
    assert ctx.allow_delete is expected_delete
