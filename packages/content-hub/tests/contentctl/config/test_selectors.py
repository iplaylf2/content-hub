from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from contentctl.config import ResolvedConfig, select_workspaces

if TYPE_CHECKING:
    from tests.contentctl.fixture_types import MakeWorkspace


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
    make_workspace: MakeWorkspace,
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
