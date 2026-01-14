from __future__ import annotations

import asyncio
from io import StringIO
from pathlib import Path

import pytest

from tests.contentctl.execute.fixtures import (
    SOURCE_ROOT,
    DESTINATION_ROOT,
    make_stream,
    make_sync_op,
)
from contentctl.execute.sync import apply_sync_plan, print_sync_plan
from collections.abc import AsyncIterator

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
    operations: list[tuple[str, SyncAction]],
    expected_actions: list[tuple[str, str]],
) -> None:
    copy_calls: list[tuple[Path, Path]] = []

    def fake_copy2(src: Path, dst: Path) -> None:
        copy_calls.append((src, dst))

    mkdir_calls: list[Path] = []

    def fake_mkdir(self: Path, parents: bool = False, exist_ok: bool = False) -> None:
        mkdir_calls.append(self)

    monkeypatch.setattr("contentctl.execute.sync.shutil.copy2", fake_copy2)
    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    stream = make_stream(*[make_sync_op(path, action) for path, action in operations])

    observed = apply_sync_plan(
        stream,
        source_root=SOURCE_ROOT,
        destination_root=DESTINATION_ROOT,
        semaphore=asyncio.Semaphore(2),
    )
    _drain_stream(observed)

    assert copy_calls == [
        (SOURCE_ROOT / src, DESTINATION_ROOT / dst) for src, dst in expected_actions
    ]
    assert mkdir_calls


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
