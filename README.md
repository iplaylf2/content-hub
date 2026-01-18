# content-hub

content-hub is a CLI tool that syncs directory content between one origin and one or more workspaces, driven by a config file.

## Quick Start

Requires Python 3.14+.

```bash
pip install content-hub
```

Initialize a config:

```bash
contentctl init
```

This creates `content-hub.yaml`:

```yaml
origin: origin
workspaces:
  docs: ./docs
```

Run sync flows:

```bash
contentctl deploy docs              # deploy origin → workspace
contentctl deploy docs --delete     # deploy + remove workspace files missing in origin
contentctl adopt docs               # adopt workspace → origin
contentctl deploy docs --dry-run    # show planned operations without changes
```

Behavior:

- `--path` is relative to the origin/workspace roots (default `.`).
- `--delete` removes workspace files missing in origin, filtered by `include`/`exclude` globs.

## Config Notes

- `origin` sets the primary content directory.
- `workspaces` maps aliases to workspace paths.
- `${VAR}` environment variable expansion is supported in config values.
