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


def test_apply_sync_plan_copies_non_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    copy_calls: list[tuple[Path, Path]] = []

    def fake_copy2(src: Path, dst: Path) -> None:
        copy_calls.append((src, dst))

    mkdir_calls: list[Path] = []

    def fake_mkdir(self: Path, parents: bool = False, exist_ok: bool = False) -> None:
        mkdir_calls.append(self)

    monkeypatch.setattr("contentctl.execute.sync.shutil.copy2", fake_copy2)
    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    stream = make_stream(
        make_sync_op("guide.txt", SyncAction.COPY),
        make_sync_op("drafts.txt", SyncAction.SKIP),
    )

    observed = apply_sync_plan(
        stream,
        source_root=SOURCE_ROOT,
        destination_root=DESTINATION_ROOT,
        semaphore=asyncio.Semaphore(2),
    )
    _drain_stream(observed)

    assert copy_calls == [
        (SOURCE_ROOT / "guide.txt", DESTINATION_ROOT / "guide.txt"),
    ]
    assert mkdir_calls


def test_print_sync_plan_formats_lines() -> None:
    stream = make_stream(
        make_sync_op("guide.txt", SyncAction.COPY),
        make_sync_op("drafts.txt", SyncAction.SKIP),
    )

    output = StringIO()
    observed = print_sync_plan(
        stream,
        source_root=SOURCE_ROOT,
        destination_root=DESTINATION_ROOT,
        output=output,
    )
    _drain_stream(observed)

    lines = output.getvalue().splitlines()
    assert lines == [
        "COPY    /virtual/source/guide.txt -> /virtual/destination/guide.txt",
        "SKIP    /virtual/source/drafts.txt -> /virtual/destination/drafts.txt",
    ]


def _drain_stream(stream: AsyncIterator[SyncOperation]) -> None:
    async def consume() -> None:
        async for _ in stream:
            pass

    asyncio.run(consume())
