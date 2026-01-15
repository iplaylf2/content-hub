# content-hub

content-hub is a CLI tool for distributing and collecting directory content across multiple locations. Define the origin and workspaces in a config file, then trigger sync actions with simple commands to keep content flow controlled and repeatable.

Good fit when:

- one source needs to be delivered to multiple directories or teams
- directory copy flows should be configured and reusable
- content paths must be managed without reshaping the structure

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

Edit it to define your content flow. Run content flows:

```bash
contentctl deploy docs              # copy origin → workspace
contentctl deploy docs --delete     # sync origin → workspace and remove unmanaged files
contentctl adopt docs               # copy workspace → origin
```

The `--delete` flag removes files in the workspace that don't exist in origin, but only within the managed scope defined by the intersection of origin and workspace include/exclude patterns.

## Config Notes

- `origin` defines the source directory
- `workspaces` maps aliases to workspace paths
- add `include`/`exclude` (glob patterns) when needed; `${VAR}` env substitution is supported
