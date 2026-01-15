import asyncio
import shutil
from collections.abc import AsyncIterator
from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import pytest

from contentctl.execute.sync import apply_sync_plan, print_sync_plan
from contentctl.plan.sync import SyncAction, SyncOperation
from tests.contentctl.execute.fixtures import (
    DESTINATION_ROOT,
    SOURCE_ROOT,
    make_stream,
    make_sync_op,
)


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
    operations: list[tuple[str, SyncAction]],
    expected_actions: list[tuple[str, str]],
) -> None:
    copied_files: list[tuple[Path, Path]] = []
    created_dirs: list[Path] = []

    def track_copy(src: Path, dst: Path) -> None:
        copied_files.append((src, dst))

    def track_mkdir(self: Path, *args: object, **kwargs: object) -> None:
        created_dirs.append(self)

    copy2_mock = Mock(spec=shutil.copy2, side_effect=track_copy)

    monkeypatch.setattr("contentctl.execute.sync.shutil.copy2", copy2_mock)
    monkeypatch.setattr(Path, "mkdir", track_mkdir)

    stream = make_stream(*[make_sync_op(path, action) for path, action in operations])

    observed = apply_sync_plan(
        stream,
        source_root=SOURCE_ROOT,
        destination_root=DESTINATION_ROOT,
        semaphore=asyncio.Semaphore(2),
    )
    _drain_stream(observed)

    expected_copies = [
        (SOURCE_ROOT / src, DESTINATION_ROOT / dst) for src, dst in expected_actions
    ]
    assert copied_files == expected_copies
    assert created_dirs


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
    operations: list[tuple[str, SyncAction]],
    expected_lines: list[str],
) -> None:
    stream = make_stream(*[make_sync_op(path, action) for path, action in operations])

    output = StringIO()
    observed = print_sync_plan(
        stream,
        source_root=SOURCE_ROOT,
        destination_root=DESTINATION_ROOT,
        output=output,
    )
    _drain_stream(observed)

    lines = output.getvalue().splitlines()
    assert lines == expected_lines


def _drain_stream(stream: AsyncIterator[SyncOperation]) -> None:
    async def consume() -> None:
        async for _ in stream:
            pass

    asyncio.run(consume())
