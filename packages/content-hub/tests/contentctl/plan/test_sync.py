from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from contentctl.plan import SyncAction, SyncError, plan_sync, resolve_sync_paths
from tests.contentctl.fixtures import fixture_path
from contentctl.plan.sync import SyncOperation


@pytest.mark.parametrize(
    ("path", "destination_name"),
    [
        (str(Path("/") / "abs"), "destination_dir"),
        ("../escape", "destination_dir"),
    ],
)
def test_resolve_sync_paths_rejects_invalid_paths(
    path: str,
    destination_name: str,
) -> None:
    source_root = fixture_path("plan_sync", "source_dir")
    destination_root = fixture_path("plan_sync", destination_name)

    with pytest.raises(SyncError):
        resolve_sync_paths(
            source_root=source_root,
            destination_root=destination_root,
            path=path,
        )


def test_resolve_sync_paths_rejects_missing_source(tmp_path: Path) -> None:
    source_root = tmp_path / "missing"
    destination_root = tmp_path / "destination"

    with pytest.raises(SyncError):
        resolve_sync_paths(
            source_root=source_root,
            destination_root=destination_root,
            path=".",
        )


def test_plan_sync_applies_include_exclude() -> None:
    source_root = fixture_path("plan_sync", "source_dir")
    destination_root = fixture_path("plan_sync", "destination_dir")

    source_path, destination_path = resolve_sync_paths(
        source_root=source_root,
        destination_root=destination_root,
        path=".",
    )
    operations = plan_sync(
        source_path=source_path,
        destination_path=destination_path,
        source_include=("*.txt", "**/*.txt"),
        source_exclude=("sub/*",),
        destination_include=("*.txt", "**/*.txt"),
        destination_exclude=(),
        **_plan_semaphores(),
    )

    collected = _collect_operations(operations)
    paths = {op.relative.name for op in collected}

    assert paths == {"guide.txt"}


def test_plan_sync_file_source_replaces() -> None:
    source_root = fixture_path("plan_sync", "source_single")
    destination_root = fixture_path("plan_sync", "destination_single")

    source_path, destination_path = resolve_sync_paths(
        source_root=source_root,
        destination_root=destination_root,
        path="note.txt",
    )
    operations = plan_sync(
        source_path=source_path,
        destination_path=destination_path,
        source_include=(),
        source_exclude=(),
        destination_include=(),
        destination_exclude=(),
        **_plan_semaphores(),
    )

    collected = _collect_operations(operations)
    assert len(collected) == 1
    op = collected[0]
    assert op.relative == Path("note.txt")
    assert op.action is SyncAction.REPLACE


def test_plan_sync_file_source_excluded() -> None:
    source_root = fixture_path("plan_sync", "source_single")
    destination_root = fixture_path("plan_sync", "destination_single")

    source_path, destination_path = resolve_sync_paths(
        source_root=source_root,
        destination_root=destination_root,
        path="note.txt",
    )
    operations = plan_sync(
        source_path=source_path,
        destination_path=destination_path,
        source_include=(),
        source_exclude=("*.txt",),
        destination_include=(),
        destination_exclude=(),
        **_plan_semaphores(),
    )

    collected = _collect_operations(operations)
    assert collected == []


def test_plan_sync_reports_destination_skips() -> None:
    source_root = fixture_path("plan_sync", "source_dir")
    destination_root = fixture_path("plan_sync", "destination_dir")

    source_path, destination_path = resolve_sync_paths(
        source_root=source_root,
        destination_root=destination_root,
        path=".",
    )
    operations = plan_sync(
        source_path=source_path,
        destination_path=destination_path,
        source_include=(),
        source_exclude=(),
        destination_include=("*.txt", "**/*.txt"),
        destination_exclude=("sub/*",),
        **_plan_semaphores(),
    )

    actions = {str(op.relative): op.action for op in _collect_operations(operations)}

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
def test_resolve_sync_paths_rejects_overlapping_paths(
    source_root: str,
    destination_root: str,
    path: str,
) -> None:
    with pytest.raises(SyncError):
        resolve_sync_paths(
            source_root=fixture_path("plan_sync", source_root),
            destination_root=fixture_path("plan_sync", destination_root),
            path=path,
        )


def test_plan_sync_file_destination_exclude_marks_skip() -> None:
    source_root = fixture_path("plan_sync", "source_single")
    destination_root = fixture_path("plan_sync", "destination_single")
    source_path, destination_path = resolve_sync_paths(
        source_root=source_root,
        destination_root=destination_root,
        path="note.txt",
    )
    operations = plan_sync(
        source_path=source_path,
        destination_path=destination_path,
        source_include=(),
        source_exclude=(),
        destination_include=(),
        destination_exclude=("*.txt",),
        **_plan_semaphores(),
    )

    collected = _collect_operations(operations)
    assert len(collected) == 1
    assert collected[0].action is SyncAction.SKIP


def _plan_semaphores() -> dict[str, asyncio.Semaphore]:
    return {
        "semaphore": asyncio.Semaphore(2),
    }


def _collect_operations(
    operations: AsyncIterator[SyncOperation],
) -> list[SyncOperation]:
    async def collect() -> list[SyncOperation]:
        return [operation async for operation in operations]

    return asyncio.run(collect())
