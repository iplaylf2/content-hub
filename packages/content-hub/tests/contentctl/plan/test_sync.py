import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from contentctl.plan import SyncAction, SyncError, plan_sync, resolve_sync_paths
from tests.contentctl.fixtures import fixture_path
from contentctl.plan.sync import SyncOperation


@pytest.mark.parametrize(
    "path",
    [
        str(Path("/") / "abs"),
        "../escape",
    ],
)
def test_resolve_sync_paths_rejects_invalid_paths(
    path: str,
) -> None:
    source_root = fixture_path("plan_sync", "source_dir")
    destination_root = fixture_path("plan_sync", "destination_single")

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
    destination_root = fixture_path("plan_sync", "destination_single")

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


@pytest.mark.parametrize(
    ("source_exclude", "expected_count", "expected_action"),
    [
        ((), 1, SyncAction.REPLACE),
        (("*.txt",), 0, None),
    ],
)
def test_plan_sync_file_source(
    source_exclude: tuple[str, ...],
    expected_count: int,
    expected_action: SyncAction | None,
) -> None:
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
        source_exclude=source_exclude,
        destination_include=(),
        destination_exclude=(),
        **_plan_semaphores(),
    )

    collected = _collect_operations(operations)
    assert len(collected) == expected_count
    if expected_count > 0:
        op = collected[0]
        assert op.relative == Path("note.txt")
        assert op.action is expected_action


@pytest.mark.parametrize(
    ("destination_include", "destination_exclude", "expected_actions"),
    [
        (
            ("*.txt", "**/*.txt"),
            ("sub/*",),
            {
                "guide.txt": SyncAction.COPY,
                "readme.md": SyncAction.SKIP,
                "sub/chapter.txt": SyncAction.SKIP,
            },
        ),
        (
            (),
            ("*.txt", "**/*.txt"),
            {
                "guide.txt": SyncAction.SKIP,
                "sub/chapter.txt": SyncAction.SKIP,
                "readme.md": SyncAction.COPY,
            },
        ),
    ],
)
def test_plan_sync_destination_filtering(
    destination_include: tuple[str, ...],
    destination_exclude: tuple[str, ...],
    expected_actions: dict[str, SyncAction],
) -> None:
    source_root = fixture_path("plan_sync", "source_dir")
    destination_root = fixture_path("plan_sync", "destination_single")
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
        destination_include=destination_include,
        destination_exclude=destination_exclude,
        **_plan_semaphores(),
    )

    actions = {str(op.relative): op.action for op in _collect_operations(operations)}

    for file, expected_action in expected_actions.items():
        assert actions[file] is expected_action


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
