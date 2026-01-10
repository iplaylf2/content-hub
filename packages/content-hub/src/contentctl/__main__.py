"""Module entry point for `python -m contentctl`."""

from __future__ import annotations

import sys
from pathlib import Path

from contentctl.cli_parser import parse_cli


def main() -> None:
    ctx = parse_cli(sys.argv[1:], Path.cwd())

    if ctx.command == "deploy":
        raise NotImplementedError("deploy is not implemented yet")
    if ctx.command == "adopt":
        raise NotImplementedError("adopt is not implemented yet")

    print(f"Unknown command: {ctx.command}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
