from __future__ import annotations

from pathlib import Path

from contentctl.config import ResolvedConfig, select_workspaces
from tests.contentctl.fixtures import make_workspace


def test_select_workspaces_preserves_order() -> None:
    resolved = ResolvedConfig(
        origin=make_workspace("", Path("/origin")),
        workspaces={
            "alpha": make_workspace("alpha", Path("/alpha")),
            "zeta": make_workspace("zeta", Path("/zeta")),
        },
    )

    selected = select_workspaces(resolved, ["zeta", "alpha"])

    assert [workspace.name for workspace in selected] == ["zeta", "alpha"]
