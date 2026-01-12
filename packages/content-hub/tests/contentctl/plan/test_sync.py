from __future__ import annotations

from pathlib import Path

import pytest

from contentctl.plan import SyncAction, SyncError, plan_sync
from tests.contentctl.fixtures import fixture_path


@pytest.mark.parametrize(
    ("path", "destination_name"),
    [
        (str(Path("/") / "abs"), "destination_dir"),
        ("../escape", "destination_dir"),
        (".", "source_dir"),
    ],
)
def test_plan_sync_rejects_invalid_paths(
    path: str,
    destination_name: str,
) -> None:
    source_root = fixture_path("plan_sync", "source_dir")
    destination_root = fixture_path("plan_sync", destination_name)

    with pytest.raises(SyncError):
        plan_sync(
            source_root=source_root,
            destination_root=destination_root,
            path=path,
            source_include=(),
            source_exclude=(),
            destination_include=(),
            destination_exclude=(),
        )


def test_plan_sync_rejects_missing_source(tmp_path: Path) -> None:
    source_root = tmp_path / "missing"
    destination_root = tmp_path / "destination"

    with pytest.raises(SyncError):
        plan_sync(
            source_root=source_root,
            destination_root=destination_root,
            path=".",
            source_include=(),
            source_exclude=(),
            destination_include=(),
            destination_exclude=(),
        )


def test_plan_sync_applies_include_exclude() -> None:
    source_root = fixture_path("plan_sync", "source_dir")
    destination_root = fixture_path("plan_sync", "destination_dir")

    plan = plan_sync(
        source_root=source_root,
        destination_root=destination_root,
        path=".",
        source_include=("*.txt", "**/*.txt"),
        source_exclude=("sub/*",),
        destination_include=("*.txt", "**/*.txt"),
        destination_exclude=(),
    )

    sources = {op.source.name for op in plan.operations}
    destinations = {op.destination.name for op in plan.operations}

    assert sources == {"guide.txt"}
    assert destinations == {"guide.txt"}


def test_plan_sync_file_source_replaces() -> None:
    source_root = fixture_path("plan_sync", "source_single")
    destination_root = fixture_path("plan_sync", "destination_single")

    plan = plan_sync(
        source_root=source_root,
        destination_root=destination_root,
        path="note.txt",
        source_include=(),
        source_exclude=(),
        destination_include=(),
        destination_exclude=(),
    )

    assert len(plan.operations) == 1
    op = plan.operations[0]
    assert op.source == source_root / "note.txt"
    assert op.destination == destination_root / "note.txt"
    assert op.action is SyncAction.REPLACE


def test_plan_sync_file_source_excluded() -> None:
    source_root = fixture_path("plan_sync", "source_single")
    destination_root = fixture_path("plan_sync", "destination_single")

    plan = plan_sync(
        source_root=source_root,
        destination_root=destination_root,
        path="note.txt",
        source_include=(),
        source_exclude=("*.txt",),
        destination_include=(),
        destination_exclude=(),
    )

    assert plan.operations == ()


def test_plan_sync_reports_destination_skips() -> None:
    source_root = fixture_path("plan_sync", "source_dir")
    destination_root = fixture_path("plan_sync", "destination_dir")

    plan = plan_sync(
        source_root=source_root,
        destination_root=destination_root,
        path=".",
        source_include=(),
        source_exclude=(),
        destination_include=("*.txt", "**/*.txt"),
        destination_exclude=("sub/*",),
    )

    actions = {
        str(op.destination.relative_to(destination_root)): op.action
        for op in plan.operations
    }

    assert actions["guide.txt"] is SyncAction.COPY
    assert actions["readme.md"] is SyncAction.SKIP
    assert actions["sub/chapter.txt"] is SyncAction.SKIP


@pytest.mark.parametrize(
    ("source_root", "destination_root", "path"),
    [
        ("source_dir", "source_dir", "."),
        ("source_dir", "source_dir/sub", "."),
        ("source_dir/sub", "source_dir", "."),
    ],
)
def test_plan_sync_rejects_overlapping_paths(
    source_root: str,
    destination_root: str,
    path: str,
) -> None:
    with pytest.raises(SyncError):
        plan_sync(
            source_root=fixture_path("plan_sync", source_root),
            destination_root=fixture_path("plan_sync", destination_root),
            path=path,
            source_include=(),
            source_exclude=(),
            destination_include=(),
            destination_exclude=(),
        )


def test_plan_sync_file_destination_exclude_marks_skip() -> None:
    source_root = fixture_path("plan_sync", "source_single")
    destination_root = fixture_path("plan_sync", "destination_single")
    plan = plan_sync(
        source_root=source_root,
        destination_root=destination_root,
        path="note.txt",
        source_include=(),
        source_exclude=(),
        destination_include=(),
        destination_exclude=("*.txt",),
    )

    assert len(plan.operations) == 1
    assert plan.operations[0].action is SyncAction.SKIP
