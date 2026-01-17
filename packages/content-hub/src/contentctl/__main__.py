import asyncio
import sys
from pathlib import Path

from .config import (
    ConfigError,
    ResolvedConfig,
    load_config,
    resolve_config,
    select_all_workspaces,
    select_workspaces,
)
from .gateway import AdoptContext, DeployContext, InitContext, parse_cli
from .operations import SyncError, run_adopt, run_deploy, run_init


def main() -> None:
    ctx = parse_cli(sys.argv[1:], Path.cwd())

    # Init command doesn't require existing config
    if isinstance(ctx, InitContext):
        try:
            run_init(
                path=ctx.path,
                config_filename=ctx.config_filename,
                dry_run=ctx.dry_run,
                verbose=ctx.verbose,
                output=sys.stdout,
            )
        except (ConfigError, FileExistsError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(1)
        return

    try:
        raw_config = load_config(ctx.config_path)
        resolved = resolve_config(raw_config, ctx.config_path)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        asyncio.run(_dispatch(ctx, resolved))
    except (ConfigError, SyncError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


async def _dispatch(
    ctx: AdoptContext | DeployContext,
    resolved: ResolvedConfig,
) -> None:
    match ctx:
        case DeployContext():
            if ctx.all_workspaces:
                workspaces = select_all_workspaces(resolved)
            else:
                workspaces = select_workspaces(resolved, ctx.workspaces)
            await run_deploy(
                workspaces=workspaces,
                origin=resolved.origin,
                path=ctx.path,
                dry_run=ctx.dry_run,
                verbose=ctx.verbose,
                allow_delete=ctx.allow_delete,
                output=sys.stdout,
            )
        case AdoptContext():
            workspaces = select_workspaces(resolved, [ctx.workspace])
            await run_adopt(
                workspace=workspaces[0],
                origin=resolved.origin,
                path=ctx.path,
                dry_run=ctx.dry_run,
                verbose=ctx.verbose,
                output=sys.stdout,
            )


if __name__ == "__main__":
    main()
