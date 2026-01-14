from __future__ import annotations

from pathlib import Path

import pytest

from contentctl.config import ResolvedConfig, select_workspaces
from tests.contentctl.fixtures import make_workspace


@pytest.mark.parametrize(
    ("selection_order", "expected_order"),
    [
        (["zeta", "alpha"], ["zeta", "alpha"]),
        (["alpha", "zeta"], ["alpha", "zeta"]),
        (["alpha"], ["alpha"]),
        (["zeta"], ["zeta"]),
    ],
)
def test_select_workspaces_preserves_order(
    selection_order: list[str],
    expected_order: list[str],
) -> None:
    resolved = ResolvedConfig(
        origin=make_workspace("", Path("/origin")),
        workspaces={
            "alpha": make_workspace("alpha", Path("/alpha")),
            "zeta": make_workspace("zeta", Path("/zeta")),
        },
    )

    selected = select_workspaces(resolved, selection_order)

    assert [workspace.name for workspace in selected] == expected_order
