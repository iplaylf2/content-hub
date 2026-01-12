from __future__ import annotations

from pathlib import Path

import pytest

from contentctl.plan import SyncAction, SyncError, plan_sync
from tests.contentctl.fixtures import fixture_path


@pytest.mark.parametrize(
    ("path", "target_name"),
    [
        (str(Path("/") / "abs"), "target_dir"),
        ("../escape", "target_dir"),
        (".", "source_dir"),
    ],
)
def test_plan_sync_rejects_invalid_paths(path: str, target_name: str) -> None:
    source_root = fixture_path("plan_sync", "source_dir")
    target_root = fixture_path("plan_sync", target_name)

    with pytest.raises(SyncError):
        plan_sync(
            source_root=source_root,
            target_root=target_root,
            path=path,
            source_include=(),
            source_exclude=(),
            target_include=(),
            target_exclude=(),
        )


def test_plan_sync_rejects_missing_source(tmp_path: Path) -> None:
    source_root = tmp_path / "missing"
    target_root = tmp_path / "target"

    with pytest.raises(SyncError):
        plan_sync(
            source_root=source_root,
            target_root=target_root,
            path=".",
            source_include=(),
            source_exclude=(),
            target_include=(),
            target_exclude=(),
        )


def test_plan_sync_applies_include_exclude() -> None:
    source_root = fixture_path("plan_sync", "source_dir")
    target_root = fixture_path("plan_sync", "target_dir")

    plan = plan_sync(
        source_root=source_root,
        target_root=target_root,
        path=".",
        source_include=("*.txt", "**/*.txt"),
        source_exclude=("sub/*",),
        target_include=("*.txt", "**/*.txt"),
        target_exclude=(),
    )

    sources = {op.source.name for op in plan.operations}
    destinations = {op.destination.name for op in plan.operations}

    assert sources == {"guide.txt"}
    assert destinations == {"guide.txt"}


def test_plan_sync_file_source() -> None:
    source_root = fixture_path("plan_sync", "source_single")
    target_root = fixture_path("plan_sync", "target_single")

    plan = plan_sync(
        source_root=source_root,
        target_root=target_root,
        path="note.txt",
        source_include=(),
        source_exclude=(),
        target_include=(),
        target_exclude=(),
    )

    assert len(plan.operations) == 1
    assert plan.operations[0].source == source_root / "note.txt"
    assert plan.operations[0].destination == target_root / "note.txt"


def test_plan_sync_file_source_excluded() -> None:
    source_root = fixture_path("plan_sync", "source_single")
    target_root = fixture_path("plan_sync", "target_single")

    plan = plan_sync(
        source_root=source_root,
        target_root=target_root,
        path="note.txt",
        source_include=(),
        source_exclude=("*.txt",),
        target_include=(),
        target_exclude=(),
    )

    assert plan.operations == ()


def test_plan_sync_reports_target_skips() -> None:
    source_root = fixture_path("plan_sync", "source_dir")
    target_root = fixture_path("plan_sync", "target_dir")

    plan = plan_sync(
        source_root=source_root,
        target_root=target_root,
        path=".",
        source_include=(),
        source_exclude=(),
        target_include=("*.txt", "**/*.txt"),
        target_exclude=("sub/*",),
    )

    actions = {
        str(op.destination.relative_to(target_root)): op.action
        for op in plan.operations
    }

    assert actions["guide.txt"] is SyncAction.COPY
    assert actions["readme.md"] is SyncAction.SKIP
    assert actions["sub/chapter.txt"] is SyncAction.SKIP


def test_plan_sync_marks_replace() -> None:
    source_root = fixture_path("plan_sync", "source_single")
    target_root = fixture_path("plan_sync", "target_single")

    plan = plan_sync(
        source_root=source_root,
        target_root=target_root,
        path="note.txt",
        source_include=(),
        source_exclude=(),
        target_include=(),
        target_exclude=(),
    )

    assert len(plan.operations) == 1
    assert plan.operations[0].action is SyncAction.REPLACE


@pytest.mark.parametrize(
    ("source_root", "target_root", "path"),
    [
        ("source_dir", "source_dir", "."),
        ("source_dir", "source_dir/sub", "."),
        ("source_dir/sub", "source_dir", "."),
    ],
)
def test_plan_sync_rejects_overlapping_paths(
    source_root: str,
    target_root: str,
    path: str,
) -> None:
    with pytest.raises(SyncError):
        plan_sync(
            source_root=fixture_path("plan_sync", source_root),
            target_root=fixture_path("plan_sync", target_root),
            path=path,
            source_include=(),
            source_exclude=(),
            target_include=(),
            target_exclude=(),
        )


def test_plan_sync_file_target_exclude_marks_skip() -> None:
    source_root = fixture_path("plan_sync", "source_single")
    target_root = fixture_path("plan_sync", "target_single")
    plan = plan_sync(
        source_root=source_root,
        target_root=target_root,
        path="note.txt",
        source_include=(),
        source_exclude=(),
        target_include=(),
        target_exclude=("*.txt",),
    )

    assert len(plan.operations) == 1
    assert plan.operations[0].action is SyncAction.SKIP
