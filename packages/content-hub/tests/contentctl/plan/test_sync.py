from __future__ import annotations

from pathlib import Path

import pytest

from contentctl.plan import SyncAction, SyncError, plan_sync
from conftest import FIXTURES_ROOT


def test_plan_sync_rejects_absolute_path() -> None:
    source_root = _fixture_path("source_dir")
    target_root = _fixture_path("target_dir")

    with pytest.raises(SyncError):
        plan_sync(
            source_root=source_root,
            target_root=target_root,
            path=str(Path("/") / "abs"),
            source_include=(),
            source_exclude=(),
            target_include=(),
            target_exclude=(),
        )


def test_plan_sync_rejects_path_escape() -> None:
    source_root = _fixture_path("source_dir")
    target_root = _fixture_path("target_dir")

    with pytest.raises(SyncError):
        plan_sync(
            source_root=source_root,
            target_root=target_root,
            path="../escape",
            source_include=(),
            source_exclude=(),
            target_include=(),
            target_exclude=(),
        )


def test_plan_sync_rejects_overlapping_paths() -> None:
    source_root = _fixture_path("source_dir")

    with pytest.raises(SyncError):
        plan_sync(
            source_root=source_root,
            target_root=source_root,
            path=".",
            source_include=(),
            source_exclude=(),
            target_include=(),
            target_exclude=(),
        )


def test_plan_sync_applies_include_exclude() -> None:
    source_root = _fixture_path("source_dir")
    target_root = _fixture_path("target_dir")

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

    assert sources == {"a.txt"}
    assert destinations == {"a.txt"}


def test_plan_sync_file_source() -> None:
    source_root = _fixture_path("source_single")
    target_root = _fixture_path("target_single")

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


def test_plan_sync_reports_target_skips() -> None:
    source_root = _fixture_path("source_dir")
    target_root = _fixture_path("target_dir")

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

    assert actions["a.txt"] is SyncAction.COPY
    assert actions["b.md"] is SyncAction.SKIP
    assert actions["sub/c.txt"] is SyncAction.SKIP


def test_plan_sync_marks_replace(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    source_root.mkdir()
    target_root.mkdir()

    source_file = source_root / "note.txt"
    source_file.write_text("new", encoding="utf-8")
    target_file = target_root / "note.txt"
    target_file.write_text("existing", encoding="utf-8")

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


def _fixture_path(name: str) -> Path:
    return FIXTURES_ROOT / "plan_sync" / name
