import asyncio
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import create_autospec

import pytest
from contentctl.plan import SyncAction, SyncError, plan_sync, resolve_sync_paths
from contentctl.plan.sync import SyncOperation

if TYPE_CHECKING:
    from tests.fixture_types import FixturePath

type PlanSemaphores = Callable[[], dict[str, Any]]
type CollectOperations = Callable[[AsyncIterator[SyncOperation]], list[SyncOperation]]


@pytest.mark.parametrize(
    ("source", "dest", "path"),
    [
        (
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_single"),
            str(Path("/") / "abs"),
        ),
        (
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_single"),
            "../escape",
        ),
        (("nonexistent_source",), ("nonexistent_destination",), "."),
        (("plan_sync", "source_multi"), ("plan_sync", "source_multi"), "."),
        (("plan_sync", "source_multi"), ("plan_sync", "source_multi", "sub"), "."),
        (("plan_sync", "source_multi", "sub"), ("plan_sync", "source_multi"), "."),
    ],
)
def test_resolve_sync_paths_rejects_invalid_inputs(
    fixture_path: FixturePath,
    source: tuple[str, ...],
    dest: tuple[str, ...],
    path: str,
) -> None:
    with pytest.raises(SyncError):
        resolve_sync_paths(
            source_root=fixture_path(*source),
            destination_root=fixture_path(*dest),
            path=path,
        )


@pytest.mark.parametrize(
    (
        "source",
        "dest",
        "source_include",
        "source_exclude",
        "destination_include",
        "destination_exclude",
        "sync_path",
        "expected_files",
    ),
    [
        (
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_single"),
            ("*.txt", "**/*.txt"),
            ("sub/*",),
            ("*.txt", "**/*.txt"),
            (),
            ".",
            {"guide.txt"},
        ),
    ],
)
def test_plan_sync_applies_include_exclude(
    fixture_path: FixturePath,
    plan_semaphores: PlanSemaphores,
    collect_operations: CollectOperations,
    source: tuple[str, ...],
    dest: tuple[str, ...],
    source_include: tuple[str, ...],
    source_exclude: tuple[str, ...],
    destination_include: tuple[str, ...],
    destination_exclude: tuple[str, ...],
    sync_path: str,
    expected_files: set[str],
) -> None:
    source_root = fixture_path(*source)
    destination_root = fixture_path(*dest)

    source_path, destination_path = resolve_sync_paths(
        source_root=source_root,
        destination_root=destination_root,
        path=sync_path,
    )
    operations = plan_sync(
        source_path=source_path,
        destination_path=destination_path,
        source_include=source_include,
        source_exclude=source_exclude,
        destination_include=destination_include,
        destination_exclude=destination_exclude,
        **plan_semaphores(),
    )

    collected = collect_operations(operations)
    paths = {op.relative.name for op in collected}

    assert paths == expected_files


@pytest.mark.parametrize(
    (
        "source",
        "dest",
        "filename",
        "source_exclude",
        "expected_count",
        "expected_action",
    ),
    [
        (
            ("plan_sync", "source_single"),
            ("plan_sync", "destination_single"),
            "note.txt",
            (),
            1,
            SyncAction.REPLACE,
        ),
        (
            ("plan_sync", "source_single"),
            ("plan_sync", "destination_single"),
            "note.txt",
            ("*.txt",),
            0,
            None,
        ),
    ],
)
def test_plan_sync_file_source(
    fixture_path: FixturePath,
    plan_semaphores: PlanSemaphores,
    collect_operations: CollectOperations,
    make_sync_op: Callable[[str, SyncAction], SyncOperation],
    source: tuple[str, ...],
    dest: tuple[str, ...],
    filename: str,
    source_exclude: tuple[str, ...],
    expected_count: int,
    expected_action: SyncAction | None,
) -> None:
    source_root = fixture_path(*source)
    destination_root = fixture_path(*dest)

    source_path, destination_path = resolve_sync_paths(
        source_root=source_root,
        destination_root=destination_root,
        path=filename,
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
        expected = [make_sync_op(filename, expected_action)]
        assert collected == expected
    else:
        assert collected == []


@pytest.mark.parametrize(
    (
        "source",
        "dest",
        "destination_include",
        "destination_exclude",
        "sync_path",
        "expected_actions",
    ),
    [
        (
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_single"),
            ("*.txt", "**/*.txt"),
            ("sub/*",),
            ".",
            {
                "guide.txt": SyncAction.COPY,
                "readme.md": SyncAction.SKIP,
                "sub/chapter.txt": SyncAction.SKIP,
            },
        ),
        (
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_single"),
            (),
            ("*.txt", "**/*.txt"),
            ".",
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
    source: tuple[str, ...],
    dest: tuple[str, ...],
    destination_include: tuple[str, ...],
    destination_exclude: tuple[str, ...],
    sync_path: str,
    expected_actions: dict[str, SyncAction],
) -> None:
    source_root = fixture_path(*source)
    destination_root = fixture_path(*dest)
    source_path, destination_path = resolve_sync_paths(
        source_root=source_root,
        destination_root=destination_root,
        path=sync_path,
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

    expected = dict(expected_actions)
    assert {k: v for k, v in actions.items() if k in expected} == expected


@pytest.mark.parametrize(
    ("source", "dest", "sync_path", "expected_actions"),
    [
        (
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_with_extra"),
            ".",
            {
                "old.txt": SyncAction.DELETE,
                "guide.txt": SyncAction.REPLACE,
            },
        ),
    ],
)
def test_plan_sync_with_delete_removes_unmanaged_files(
    fixture_path: FixturePath,
    plan_semaphores: PlanSemaphores,
    collect_operations: CollectOperations,
    source: tuple[str, ...],
    dest: tuple[str, ...],
    sync_path: str,
    expected_actions: dict[str, SyncAction],
) -> None:
    source_root = fixture_path(*source)
    destination_root = fixture_path(*dest)

    source_path, destination_path = resolve_sync_paths(
        source_root=source_root,
        destination_root=destination_root,
        path=sync_path,
    )
    operations = plan_sync(
        source_path=source_path,
        destination_path=destination_path,
        source_include=(),
        source_exclude=(),
        destination_include=(),
        destination_exclude=(),
        allow_delete=True,
        **plan_semaphores(),
    )

    collected = collect_operations(operations)
    actions = {str(op.relative): op.action for op in collected}

    assert all(actions.get(file) is action for file, action in expected_actions.items())


@pytest.mark.parametrize(
    ("source", "dest", "sync_path", "missing_file", "expected_file", "expected_action"),
    [
        (
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_with_extra"),
            ".",
            "old.txt",
            "guide.txt",
            SyncAction.REPLACE,
        ),
    ],
)
def test_plan_sync_without_delete_keeps_extra_files(
    fixture_path: FixturePath,
    plan_semaphores: PlanSemaphores,
    collect_operations: CollectOperations,
    source: tuple[str, ...],
    dest: tuple[str, ...],
    sync_path: str,
    missing_file: str,
    expected_file: str,
    expected_action: SyncAction,
) -> None:
    source_root = fixture_path(*source)
    destination_root = fixture_path(*dest)

    source_path, destination_path = resolve_sync_paths(
        source_root=source_root,
        destination_root=destination_root,
        path=sync_path,
    )
    operations = plan_sync(
        source_path=source_path,
        destination_path=destination_path,
        source_include=(),
        source_exclude=(),
        destination_include=(),
        destination_exclude=(),
        allow_delete=False,
        **plan_semaphores(),
    )

    collected = collect_operations(operations)
    actions = {str(op.relative): op.action for op in collected}

    assert missing_file not in actions
    assert actions[expected_file] is expected_action


@pytest.mark.parametrize(
    (
        "source",
        "dest",
        "source_include",
        "destination_include",
        "sync_path",
        "expected_actions",
    ),
    [
        (
            ("plan_sync", "source_multi"),
            ("plan_sync", "destination_with_extra"),
            ("*.txt", "**/*.txt"),
            ("*.txt", "**/*.txt"),
            ".",
            {
                "old.txt": SyncAction.DELETE,
                "guide.txt": SyncAction.REPLACE,
                "readme.md": None,
            },
        ),
    ],
)
def test_plan_sync_with_delete_respects_selector_intersection(
    fixture_path: FixturePath,
    plan_semaphores: PlanSemaphores,
    collect_operations: CollectOperations,
    source: tuple[str, ...],
    dest: tuple[str, ...],
    source_include: tuple[str, ...],
    destination_include: tuple[str, ...],
    sync_path: str,
    expected_actions: dict[str, SyncAction | None],
) -> None:
    source_root = fixture_path(*source)
    destination_root = fixture_path(*dest)

    source_path, destination_path = resolve_sync_paths(
        source_root=source_root,
        destination_root=destination_root,
        path=sync_path,
    )
    operations = plan_sync(
        source_path=source_path,
        destination_path=destination_path,
        source_include=source_include,
        source_exclude=(),
        destination_include=destination_include,
        destination_exclude=(),
        allow_delete=True,
        **plan_semaphores(),
    )

    collected = collect_operations(operations)
    actions = {str(op.relative): op.action for op in collected}

    assert all(
        (file not in actions) if action is None else (actions.get(file) is action)
        for file, action in expected_actions.items()
    )


@pytest.mark.parametrize(
    ("source", "dest", "filename"),
    [
        (
            ("plan_sync", "source_single"),
            ("plan_sync", "destination_single"),
            "note.txt",
        ),
    ],
)
def test_plan_sync_file_source_copies_when_destination_missing(
    fixture_path: FixturePath,
    plan_semaphores: PlanSemaphores,
    collect_operations: CollectOperations,
    make_sync_op: Callable[[str, SyncAction], SyncOperation],
    monkeypatch: pytest.MonkeyPatch,
    source: tuple[str, ...],
    dest: tuple[str, ...],
    filename: str,
) -> None:
    source_root = fixture_path(*source)
    destination_root = fixture_path(*dest)

    source_path, destination_path = resolve_sync_paths(
        source_root=source_root,
        destination_root=destination_root,
        path=filename,
    )

    def exists_stub(self: Path) -> bool:
        return self != destination_path

    exists_mock = create_autospec(Path.exists, side_effect=exists_stub)
    monkeypatch.setattr(Path, "exists", exists_mock)

    operations = plan_sync(
        source_path=source_path,
        destination_path=destination_path,
        source_include=(),
        source_exclude=(),
        destination_include=(),
        destination_exclude=(),
        **plan_semaphores(),
    )

    collected = collect_operations(operations)
    assert collected == [make_sync_op(filename, SyncAction.COPY)]


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
