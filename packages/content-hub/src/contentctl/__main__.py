"""Module entry point for `python -m contentctl`."""

from __future__ import annotations

import sys
from pathlib import Path

from contentctl.cli_parser import AdoptContext, DeployContext, parse_cli
from contentctl.config import ConfigError, load_config, resolve_config


def main() -> None:
    ctx = parse_cli(sys.argv[1:], Path.cwd())

    try:
        raw_config = load_config(ctx.config_path)
        resolve_config(raw_config, ctx.config_path)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    match ctx:
        case DeployContext():
            raise NotImplementedError("deploy is not implemented yet")
        case AdoptContext():
            raise NotImplementedError("adopt is not implemented yet")


if __name__ == "__main__":
    main()
