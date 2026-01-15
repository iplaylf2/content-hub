from pathlib import Path
from typing import TextIO

import yaml


def run_init(
    path: Path,
    dry_run: bool,
    verbose: bool,
    output: TextIO,
) -> None:
    target_dir = path
    config_file = target_dir / "content-hub.yaml"

    if config_file.exists():
        raise FileExistsError(
            f"Configuration file already exists: {config_file}\n"
            "Remove it first or use a different path."
        )

    config_content = _generate_config_template()

    if verbose or dry_run:
        print(f"Creating config file: {config_file}", file=output)

    if dry_run:
        print("\nConfig content:", file=output)
        print(config_content, file=output)
        return

    # Ensure directory exists
    target_dir.mkdir(parents=True, exist_ok=True)

    # Write config file
    config_file.write_text(config_content, encoding="utf-8")

    print(f"✓ Created {config_file}", file=output)


def _generate_config_template() -> str:
    config = {
        "origin": "origin",
        "workspaces": {
            "docs": "./docs",
        },
    }

    return yaml.dump(
        config,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
