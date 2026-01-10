# content-hub

content-hub is a command-line tool for managing the lifecycle of directory content across multiple locations.

It operates on directories as content units and provides explicit actions for moving them between locations.

## Design stance

content-hub only acts on content that is explicitly selected.
The presence of files or directories alone does not make them part of a workflow.

The tool does not derive meaning from the surrounding environment and treats directories as opaque content.
Interpretation and policy are left to the user.

## Status

This project is in an early stage.
Usage and workflows will be documented as the implementation evolves.

## CLI usage

The CLI exposes a small set of explicit commands for operating on directory content.
All command context is derived from a selected config file.

By default, the CLI looks for `content-hub.yaml` in the current working directory.
This file is a conventional entry point, not an inferred environment.

The CLI itself does not impose rules on content structure or policy.
Instead, the config defines relationships, aliases, and path anchors that determine how commands are interpreted.

### Config and workspace model

A config file primarily registers workspaces.

A workspace is a named path anchor:

- it defines a base path
- relative paths are resolved against it
- it does not imply state, activation, or content semantics

Workspaces exist only in the config.
The CLI does not infer or discover them from the filesystem.

### Command form

All primary commands follow the same structure:

```bash
contentctl deploy <workspace>... [--path <path>] | --all-workspaces [--path <path>]
contentctl adopt <workspace> [--path <path>]
```

Where:

- `<workspace>` is a workspace alias defined in the config (no path suffix)
- `--path` limits the operation to a path within each targeted workspace
- `--all-workspaces` explicitly targets all workspaces defined in the config (deploy only)

`--path` assumes the origin directory and each workspace directory share a compatible structure (e.g., `--path api` maps `origin/api` to `<workspace>/api`).

### Examples

```bash
# show help
contentctl --help

# deploy an entire workspace
contentctl deploy docs

# deploy multiple workspaces
contentctl deploy docs assets

# deploy a path within a workspace
contentctl deploy docs --path api

# deploy a path across all workspaces
contentctl deploy --all-workspaces --path api

# adopt content back from a workspace
contentctl adopt docs

# adopt a path within a workspace
contentctl adopt docs --path api

# use an explicit config file
contentctl deploy docs -c content-hub.yaml
```

In all cases, the selected config defines the available workspaces, their path anchors,
and the policy governing how content is handled.
