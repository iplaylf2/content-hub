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
