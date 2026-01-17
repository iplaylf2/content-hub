# content-hub

content-hub is a CLI tool for syncing directory content between an origin and workspaces. Define the origin and workspaces in a config file, then run deploy/adopt commands to keep content flow controlled and repeatable.

Good fit when:

- one source needs to reach multiple directories or teams
- directory sync flows should be configured and reusable
- content paths must be managed without reshaping structure

## Quick Start

Requires Python 3.14+.

```bash
pip install content-hub
```

Initialize a new project:

```bash
contentctl init
```

This creates `content-hub.yaml`:

```yaml
origin: origin
workspaces:
  docs: ./docs
```

Edit it to define your content flow. Run sync flows:

```bash
contentctl deploy docs              # deploy origin → workspace
contentctl deploy docs --delete     # deploy + remove unmanaged workspace files
contentctl adopt docs               # adopt workspace → origin
contentctl deploy docs --dry-run    # show planned operations without changes
```

Managed scope means paths under each root that match include/exclude globs.

The `--delete` flag removes files in the workspace that don't exist in origin, but only within the managed scope.

## Config Notes

- `origin` sets the primary content directory
- `workspaces` maps aliases to workspace paths
- `${VAR}` environment variable expansion is supported in config values
- `include`/`exclude` are glob patterns matched under the root directory
