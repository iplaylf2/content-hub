"""Module entry point for `python -m contentctl`."""

from __future__ import annotations

import sys
from pathlib import Path

from contentctl.cli_parser import parse_cli
from contentctl.config_loader import ConfigError, load_config


def main() -> None:
    ctx = parse_cli(sys.argv[1:], Path.cwd())

    try:
        _config = load_config(ctx.config_path)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    match ctx.command:
        case "deploy":
            raise NotImplementedError("deploy is not implemented yet")
        case "adopt":
            raise NotImplementedError("adopt is not implemented yet")
        case _:
            print(f"Unknown command: {ctx.command}", file=sys.stderr)
            sys.exit(2)


if __name__ == "__main__":
    main()
