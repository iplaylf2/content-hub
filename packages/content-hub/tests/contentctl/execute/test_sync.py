import asyncio
import shutil
from collections.abc import AsyncIterator, Callable
from io import StringIO
from pathlib import Path
from unittest.mock import create_autospec

import pytest

from contentctl.execute.sync import apply_sync_plan, print_sync_plan
from contentctl.plan.sync import SyncAction, SyncOperation


@pytest.mark.parametrize(
    ("operations", "expected_actions"),
    [
        (
            [("guide.txt", SyncAction.COPY), ("drafts.txt", SyncAction.SKIP)],
            [("guide.txt", "guide.txt")],
        ),
        (
            [("readme.md", SyncAction.REPLACE), ("index.html", SyncAction.SKIP)],
            [("readme.md", "readme.md")],
        ),
    ],
)
def test_apply_sync_plan_copies_non_skip(
    monkeypatch: pytest.MonkeyPatch,
    source_root: Path,
    destination_root: Path,
    make_sync_op: Callable[[str, SyncAction], SyncOperation],
    make_stream: Callable[..., AsyncIterator[SyncOperation]],
    drain_stream: Callable[[AsyncIterator[SyncOperation]], None],
    operations: list[tuple[str, SyncAction]],
    expected_actions: list[tuple[str, str]],
) -> None:
    observed_copies: list[tuple[Path, Path]] = []

    def observe_copy(src: Path, dst: Path) -> None:
        observed_copies.append((src, dst))

    copy2_mock = create_autospec(shutil.copy2, side_effect=observe_copy)
    mkdir_mock = create_autospec(Path.mkdir)

    monkeypatch.setattr("contentctl.execute.sync.shutil.copy2", copy2_mock)
    monkeypatch.setattr(Path, "mkdir", mkdir_mock)

    stream = make_stream(*[make_sync_op(path, action) for path, action in operations])

    observed = apply_sync_plan(
        stream,
        source_root=source_root,
        destination_root=destination_root,
        semaphore=asyncio.Semaphore(2),
    )
    drain_stream(observed)

    expected_copies = [
        (source_root / src, destination_root / dst) for src, dst in expected_actions
    ]
    assert observed_copies == expected_copies


@pytest.mark.parametrize(
    ("operations", "expected_lines"),
    [
        (
            [("guide.txt", SyncAction.COPY), ("drafts.txt", SyncAction.SKIP)],
            [
                "COPY    /virtual/source/guide.txt -> /virtual/destination/guide.txt",
                "SKIP    /virtual/source/drafts.txt -> /virtual/destination/drafts.txt",
            ],
        ),
        (
            [("readme.md", SyncAction.REPLACE)],
            [
                "REPLACE /virtual/source/readme.md -> /virtual/destination/readme.md",
            ],
        ),
    ],
)
def test_print_sync_plan_formats_lines(
    source_root: Path,
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
        source_root=source_root,
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
