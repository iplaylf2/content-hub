"""Module entry point for `python -m contentctl`."""

from __future__ import annotations

import argparse
import sys


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="contentctl",
        description="Manage directory content across multiple locations.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("deploy", help="Copy content from source to target.")
    subparsers.add_parser("adopt", help="Copy content from target to source.")

    return parser.parse_args(argv)


def main() -> None:
    args = parse_args(sys.argv[1:])

    if args.command == "deploy":
        raise NotImplementedError("deploy is not implemented yet")
    if args.command == "adopt":
        raise NotImplementedError("adopt is not implemented yet")

    print(f"Unknown command: {args.command}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
