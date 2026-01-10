"""CLI parsing and context resolution for contentctl."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


def parse_cli(argv: list[str], cwd: Path) -> CliContext:
    parser = _build_parser()
    args = parser.parse_args(argv)

    config_path = _resolve_config_path(args.config, cwd)

    targets = list(args.target or [])
    _validate_targets(targets, args.all, parser)

    return CliContext(
        command=args.command,
        config_path=config_path,
        all_workspaces=args.all,
        targets=targets,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contentctl",
        description="Manage directory content across multiple locations.",
    )
    parser.add_argument(
        "-c",
        "--config",
        dest="config",
        default="content-hub.yaml",
        help="Path to the config file. Defaults to content-hub.yaml in the current directory.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Copy content from source to target.",
    )
    adopt_parser = subparsers.add_parser(
        "adopt",
        help="Copy content from target to source.",
    )
    _add_target_args(deploy_parser)
    _add_target_args(adopt_parser)
    return parser


def _resolve_config_path(config_arg: str, cwd: Path) -> Path:
    config_path = Path(config_arg)
    if not config_path.is_absolute():
        config_path = cwd / config_path
    return config_path.resolve()


def _validate_targets(
    targets: list[str], all_workspaces: bool, parser: argparse.ArgumentParser
) -> None:
    if all_workspaces and targets:
        parser.error("Use either workspace targets or --all, not both.")
    if not all_workspaces and not targets:
        parser.error("One or more workspace targets or --all is required.")
    for target in targets:
        if not target.strip():
            parser.error("Workspace target cannot be empty.")


def _add_target_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Target all workspaces defined in the config.",
    )
    parser.add_argument(
        "target",
        nargs="*",
        help="Workspace or workspace/path to target.",
    )


@dataclass(frozen=True)
class CliContext:
    """Resolved CLI inputs and environment context."""

    command: str
    config_path: Path
    all_workspaces: bool
    targets: list[str]
