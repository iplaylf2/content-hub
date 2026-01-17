from pathlib import Path

import pytest
from contentctl.gateway import AdoptContext, DeployContext, InitContext, parse_cli
from contentctl.gateway.defaults import (
    DEFAULT_CONFIG_FILENAME,
    DEFAULT_CONFIG_PATH,
    DEFAULT_INIT_DIR,
)

VIRTUAL_WORKSPACE = "virtual-workspace"
VIRTUAL_SUBDIR = "virtual-subdir"
VIRTUAL_CONFIG_PATH = "virtual-config.yaml"


@pytest.mark.parametrize(
    (
        "argv",
        "ctx_type",
        "command",
        "path",
        "workspaces",
        "workspace",
        "config_name",
        "all_workspaces",
    ),
    [
        (
            [
                "--config",
                VIRTUAL_CONFIG_PATH,
                "deploy",
                VIRTUAL_WORKSPACE,
                "--path",
                VIRTUAL_SUBDIR,
            ],
            DeployContext,
            "deploy",
            VIRTUAL_SUBDIR,
            [VIRTUAL_WORKSPACE],
            None,
            VIRTUAL_CONFIG_PATH,
            False,
        ),
        (
            [
                "--config",
                VIRTUAL_CONFIG_PATH,
                "deploy",
                "--all-workspaces",
            ],
            DeployContext,
            "deploy",
            ".",
            [],
            None,
            VIRTUAL_CONFIG_PATH,
            True,
        ),
        (
            [
                "--config",
                VIRTUAL_CONFIG_PATH,
                "adopt",
                VIRTUAL_WORKSPACE,
            ],
            AdoptContext,
            "adopt",
            ".",
            None,
            VIRTUAL_WORKSPACE,
            VIRTUAL_CONFIG_PATH,
            None,
        ),
    ],
)
def test_parse_cli_success(
    fixture_dir: Path,
    argv: list[str],
    ctx_type: type[DeployContext | AdoptContext],
    command: str,
    path: str,
    workspaces: list[str] | None,
    workspace: str | None,
    config_name: str,
    *,
    all_workspaces: bool | None,
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
    ("config_arg", "workspace", "use_absolute"),
    [
        (VIRTUAL_CONFIG_PATH, VIRTUAL_WORKSPACE, False),
        ("virtual/custom/path/config.yaml", VIRTUAL_WORKSPACE, False),
        (VIRTUAL_CONFIG_PATH, VIRTUAL_WORKSPACE, True),
    ],
)
def test_parse_cli_accepts_config_path(
    fixture_dir: Path,
    config_arg: str,
    workspace: str,
    *,
    use_absolute: bool,
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
    *,
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


@pytest.mark.parametrize(
    ("argv", "expected_path", "expected_is_absolute"),
    [
        (["init"], Path(DEFAULT_INIT_DIR), False),
        (["init", "virtual-subdir"], Path("virtual-subdir"), False),
        (["init", "/virtual/abs"], Path("/virtual/abs"), True),
    ],
)
def test_parse_cli_init_resolves_paths(
    fixture_dir: Path,
    argv: list[str],
    expected_path: Path,
    *,
    expected_is_absolute: bool,
) -> None:
    ctx = parse_cli(argv, fixture_dir)

    assert isinstance(ctx, InitContext)
    if expected_is_absolute:
        assert ctx.path == expected_path
    else:
        assert ctx.path == (fixture_dir / expected_path).resolve()
    assert ctx.config_path == (fixture_dir / DEFAULT_CONFIG_PATH).resolve()
    assert ctx.config_filename == DEFAULT_CONFIG_FILENAME


@pytest.mark.parametrize(
    ("flags", "expected_dry_run", "expected_verbose"),
    [
        (["--dry-run", "--verbose"], True, True),
        (["--dry-run"], True, False),
        (["--verbose"], False, True),
        ([], False, False),
    ],
)
def test_parse_cli_init_sets_flags(
    fixture_dir: Path,
    flags: list[str],
    *,
    expected_dry_run: bool,
    expected_verbose: bool,
) -> None:
    ctx = parse_cli([*flags, "init"], fixture_dir)

    assert isinstance(ctx, InitContext)
    assert ctx.dry_run is expected_dry_run
    assert ctx.verbose is expected_verbose
