import asyncio
import shutil
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import create_autospec

import pytest
from contentctl.execute.sync import apply_sync_plan, print_sync_plan
from contentctl.plan.sync import SyncAction, SyncOperation

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable


@pytest.mark.parametrize(
    ("operations", "expected_copies", "expected_deletions"),
    [
        (
            [("guide.txt", SyncAction.COPY), ("drafts.txt", SyncAction.SKIP)],
            [("guide.txt", "guide.txt")],
            [],
        ),
        (
            [("readme.md", SyncAction.REPLACE), ("index.html", SyncAction.SKIP)],
            [("readme.md", "readme.md")],
            [],
        ),
        (
            [("old.txt", SyncAction.DELETE), ("keep.txt", SyncAction.SKIP)],
            [],
            ["old.txt"],
        ),
        (
            [("a.txt", SyncAction.DELETE), ("b.txt", SyncAction.DELETE)],
            [],
            ["a.txt", "b.txt"],
        ),
    ],
)
def test_apply_sync_plan_applies_actions(
    monkeypatch: pytest.MonkeyPatch,
    source_root: Path,
    destination_root: Path,
    make_sync_op: Callable[[str, SyncAction], SyncOperation],
    make_stream: Callable[..., AsyncIterator[SyncOperation]],
    drain_stream: Callable[[AsyncIterator[SyncOperation]], None],
    operations: list[tuple[str, SyncAction]],
    expected_copies: list[tuple[str, str]],
    expected_deletions: list[str],
) -> None:
    observed_copies: list[tuple[Path, Path]] = []
    observed_deletions: list[Path] = []

    def observe_copy(src: Path, dst: Path) -> None:
        observed_copies.append((src, dst))

    def observe_unlink(self: Path) -> None:
        observed_deletions.append(self)

    def exists_stub(_self: Path) -> bool:
        return True

    copy2_mock = create_autospec(shutil.copy2, side_effect=observe_copy)
    mkdir_mock = create_autospec(Path.mkdir)
    unlink_mock = create_autospec(Path.unlink, side_effect=observe_unlink)
    exists_mock = create_autospec(Path.exists, side_effect=exists_stub)

    monkeypatch.setattr("contentctl.execute.sync.shutil.copy2", copy2_mock)
    monkeypatch.setattr(Path, "mkdir", mkdir_mock)
    monkeypatch.setattr(Path, "unlink", unlink_mock)
    monkeypatch.setattr(Path, "exists", exists_mock)

    stream = make_stream(*[make_sync_op(path, action) for path, action in operations])

    observed = apply_sync_plan(
        stream,
        source_root=source_root,
        destination_root=destination_root,
        semaphore=asyncio.Semaphore(2),
    )
    drain_stream(observed)

    expected_copy_paths = [
        (source_root / src, destination_root / dst) for src, dst in expected_copies
    ]
    expected_delete_paths = [destination_root / path for path in expected_deletions]
    assert observed_copies == expected_copy_paths
    assert observed_deletions == expected_delete_paths


@pytest.mark.parametrize(
    "filename",
    [
        "ghost.txt",
        "missing.md",
    ],
)
def test_apply_sync_plan_skips_delete_when_missing(
    monkeypatch: pytest.MonkeyPatch,
    source_root: Path,
    destination_root: Path,
    make_sync_op: Callable[[str, SyncAction], SyncOperation],
    make_stream: Callable[..., AsyncIterator[SyncOperation]],
    drain_stream: Callable[[AsyncIterator[SyncOperation]], None],
    filename: str,
) -> None:
    def exists_stub(_self: Path) -> bool:
        return False

    copy2_mock = create_autospec(shutil.copy2)
    mkdir_mock = create_autospec(Path.mkdir)
    unlink_mock = create_autospec(Path.unlink)
    exists_mock = create_autospec(Path.exists, side_effect=exists_stub)

    monkeypatch.setattr("contentctl.execute.sync.shutil.copy2", copy2_mock)
    monkeypatch.setattr(Path, "mkdir", mkdir_mock)
    monkeypatch.setattr(Path, "unlink", unlink_mock)
    monkeypatch.setattr(Path, "exists", exists_mock)

    stream = make_stream(make_sync_op(filename, SyncAction.DELETE))

    observed = apply_sync_plan(
        stream,
        source_root=source_root,
        destination_root=destination_root,
        semaphore=asyncio.Semaphore(2),
    )
    drain_stream(observed)

    unlink_mock.assert_not_called()
    copy2_mock.assert_not_called()
    mkdir_mock.assert_not_called()


@pytest.mark.parametrize(
    ("operations", "expected_lines"),
    [
        (
            [("guide.txt", SyncAction.COPY), ("drafts.txt", SyncAction.SKIP)],
            [
                "copy    /virtual/destination/guide.txt",
                "skip    /virtual/destination/drafts.txt",
            ],
        ),
        (
            [("readme.md", SyncAction.REPLACE)],
            [
                "replace /virtual/destination/readme.md",
            ],
        ),
        (
            [("old.txt", SyncAction.DELETE)],
            [
                "delete  /virtual/destination/old.txt",
            ],
        ),
    ],
)
def test_print_sync_plan_formats_lines(
    destination_root: Path,
    make_sync_op: Callable[[str, SyncAction], SyncOperation],
    make_stream: Callable[..., AsyncIterator[SyncOperation]],
    drain_stream: Callable[[AsyncIterator[SyncOperation]], None],
    operations: list[tuple[str, SyncAction]],
    expected_lines: list[str],
) -> None:
    stream = make_stream(*[make_sync_op(path, action) for path, action in operations])

    output = StringIO()
    observed = print_sync_plan(
        stream,
        destination_root=destination_root,
        output=output,
    )
    drain_stream(observed)

    lines = output.getvalue().splitlines()
    assert lines == expected_lines


@pytest.fixture
def source_root() -> Path:
    """Virtual source root for sync tests."""
    return Path("/virtual/source")


@pytest.fixture
def destination_root() -> Path:
    """Virtual destination root for sync tests."""
    return Path("/virtual/destination")


@pytest.fixture
def make_stream() -> Callable[..., AsyncIterator[SyncOperation]]:
    """Create an async stream of SyncOperations."""

    def _make(*operations: SyncOperation) -> AsyncIterator[SyncOperation]:
        async def iter_operations() -> AsyncIterator[SyncOperation]:
            for operation in operations:
                yield operation

        return iter_operations()

    return _make


@pytest.fixture
def drain_stream() -> Callable[[AsyncIterator[SyncOperation]], None]:
    """Drain an async stream to completion."""

    def _drain(stream: AsyncIterator[SyncOperation]) -> None:
        async def consume() -> None:
            async for _ in stream:
                pass

        asyncio.run(consume())

    return _drain
