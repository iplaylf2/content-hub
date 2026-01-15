import asyncio
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, TypeAlias

import pytest

from contentctl.plan import SyncAction, SyncError, plan_sync, resolve_sync_paths
from contentctl.plan.sync import SyncOperation

from tests.fixture_types import FixturePath

PlanSemaphores: TypeAlias = Callable[[], dict[str, Any]]
CollectOperations: TypeAlias = Callable[
    [AsyncIterator[SyncOperation]], list[SyncOperation]
]


@pytest.mark.parametrize(
    "path",
    [
        str(Path("/") / "abs"),
        "../escape",
    ],
)
def test_resolve_sync_paths_rejects_invalid_paths(
    fixture_path: FixturePath,
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


def test_plan_sync_applies_include_exclude(
    fixture_path: FixturePath,
    plan_semaphores: PlanSemaphores,
    collect_operations: CollectOperations,
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
        source_include=("*.txt", "**/*.txt"),
        source_exclude=("sub/*",),
        destination_include=("*.txt", "**/*.txt"),
        destination_exclude=(),
        **plan_semaphores(),
    )

    collected = collect_operations(operations)
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
    fixture_path: FixturePath,
    plan_semaphores: PlanSemaphores,
    collect_operations: CollectOperations,
    make_sync_op: Callable[[str, SyncAction], SyncOperation],
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
        **plan_semaphores(),
    )

    collected = collect_operations(operations)
    if expected_count > 0:
        assert expected_action is not None
        expected = [make_sync_op("note.txt", expected_action)]
        assert collected == expected
    else:
        assert collected == []


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
    fixture_path: FixturePath,
    plan_semaphores: PlanSemaphores,
    collect_operations: CollectOperations,
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
        **plan_semaphores(),
    )

    actions = {str(op.relative): op.action for op in collect_operations(operations)}

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
    fixture_path: FixturePath,
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


@pytest.fixture
def plan_semaphores() -> PlanSemaphores:
    """Create semaphores for async plan operations."""

    def _make() -> dict[str, asyncio.Semaphore]:
        return {"semaphore": asyncio.Semaphore(2)}

    return _make


@pytest.fixture
def collect_operations() -> CollectOperations:
    """Collect operations from async iterator."""

    def _collect(operations: AsyncIterator[SyncOperation]) -> list[SyncOperation]:
        async def collect() -> list[SyncOperation]:
            return [operation async for operation in operations]

        return asyncio.run(collect())

    return _collect


@pytest.fixture
def make_sync_op() -> Callable[[str, SyncAction], SyncOperation]:
    """Create a SyncOperation for testing."""

    def _make(filename: str, action: SyncAction) -> SyncOperation:
        return SyncOperation(relative=Path(filename), action=action)

    return _make
