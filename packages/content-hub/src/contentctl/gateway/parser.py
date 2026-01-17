"""CLI parsing and context resolution for contentctl."""

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from .defaults import (
    DEFAULT_CONFIG_FILENAME,
    DEFAULT_CONFIG_PATH,
    DEFAULT_INIT_DIR,
    DEFAULT_WORKSPACE_SUBPATH,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def parse_cli(argv: list[str], cwd: Path) -> CliContext:
    parser = _build_parser()
    args = parser.parse_args(argv)

    config_path = _resolve_config_path(cwd, args.config)

    if not args.path.strip():
        parser.error("path is required.")

    match args.command:
        case "deploy":
            workspaces = list(args.workspace or [])
            all_workspaces = bool(args.all_workspaces)
            _validate_deploy_workspaces(
                parser,
                workspaces,
                all_workspaces=all_workspaces,
            )
            return DeployContext(
                command="deploy",
                config_path=config_path,
                all_workspaces=all_workspaces,
                workspaces=workspaces,
                path=args.path,
                allow_delete=args.delete,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
        case "adopt":
            workspace = args.workspace
            _validate_adopt_workspace(parser, workspace)
            return AdoptContext(
                command="adopt",
                config_path=config_path,
                workspace=workspace,
                path=args.path,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
        case "init":
            init_path = Path(args.path)
            if not init_path.is_absolute():
                init_path = cwd / init_path
            return InitContext(
                command="init",
                config_path=config_path,
                config_filename=DEFAULT_CONFIG_FILENAME,
                path=init_path.resolve(),
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
        case _:
            parser.error(f"unknown command: {args.command}")


@dataclass(frozen=True)
class BaseContext:
    config_path: Path
    dry_run: bool
    verbose: bool


@dataclass(frozen=True)
class DeployContext(BaseContext):
    command: Literal["deploy"]
    all_workspaces: bool
    workspaces: list[str]
    path: str
    allow_delete: bool


@dataclass(frozen=True)
class AdoptContext(BaseContext):
    command: Literal["adopt"]
    workspace: str
    path: str


@dataclass(frozen=True)
class InitContext(BaseContext):
    command: Literal["init"]
    path: Path
    config_filename: str


CliContext = DeployContext | AdoptContext | InitContext


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contentctl",
        description="sync directory content between an origin and workspaces.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--config",
        dest="config",
        default=DEFAULT_CONFIG_PATH,
        help="path to the content-hub config file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show planned operations without writing changes.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="show detailed operation output.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_deploy_parser(subparsers.add_parser)
    _add_adopt_parser(subparsers.add_parser)
    _add_init_parser(subparsers.add_parser)
    return parser


def _resolve_config_path(cwd: Path, config_arg: str) -> Path:
    config_path = Path(config_arg)
    if not config_path.is_absolute():
        config_path = cwd / config_path
    return config_path.resolve()


def _validate_deploy_workspaces(
    parser: argparse.ArgumentParser,
    workspaces: list[str],
    *,
    all_workspaces: bool,
) -> None:
    if all_workspaces and workspaces:
        parser.error("use workspace list or --all-workspaces, not both.")
    if not all_workspaces and not workspaces:
        parser.error("workspace is required unless --all-workspaces is set.")
    for workspace in workspaces:
        if not workspace.strip():
            parser.error("workspace cannot be empty.")


def _validate_adopt_workspace(
    parser: argparse.ArgumentParser,
    workspace: str,
) -> None:
    if not workspace.strip():
        parser.error("workspace cannot be empty.")


def _add_deploy_parser(
    add_parser: Callable[..., argparse.ArgumentParser],
) -> None:
    parser = add_parser(
        "deploy",
        help="deploy content from origin to workspace.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--all-workspaces",
        action="store_true",
        help="target all workspaces in the config.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="delete workspace files missing in origin.",
    )
    _add_workspace_arg(parser, nargs="*")
    _add_path_arg(parser)


def _add_adopt_parser(
    add_parser: Callable[..., argparse.ArgumentParser],
) -> None:
    parser = add_parser(
        "adopt",
        help="adopt content from workspace to origin.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _add_workspace_arg(parser)
    _add_path_arg(parser)


def _add_init_parser(
    add_parser: Callable[..., argparse.ArgumentParser],
) -> None:
    parser = add_parser(
        "init",
        help=f"create a new {DEFAULT_CONFIG_FILENAME} config file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=DEFAULT_INIT_DIR,
        help=f"target directory for {DEFAULT_CONFIG_FILENAME}.",
    )


def _add_workspace_arg(
    parser: argparse.ArgumentParser,
    nargs: str | None = None,
) -> None:
    parser.add_argument(
        "workspace",
        nargs=nargs,
        help="workspace alias from the config.",
    )


def _add_path_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-p",
        "--path",
        default=DEFAULT_WORKSPACE_SUBPATH,
        help="relative subpath under origin and workspace roots.",
    )
