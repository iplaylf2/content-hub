from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from tests.contentctl.execute.fixtures import (
    SOURCE_ROOT,
    DESTINATION_ROOT,
    make_plan,
    make_sync_op,
)
from contentctl.execute.sync import apply_sync_plan, print_sync_plan
from contentctl.plan.sync import SyncAction


def test_apply_sync_plan_copies_non_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    copy_calls: list[tuple[Path, Path]] = []

    def fake_copy2(src: Path, dst: Path) -> None:
        copy_calls.append((src, dst))

    mkdir_calls: list[Path] = []

    def fake_mkdir(self: Path, parents: bool = False, exist_ok: bool = False) -> None:
        mkdir_calls.append(self)

    monkeypatch.setattr("contentctl.execute.sync.shutil.copy2", fake_copy2)
    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    plan = make_plan(
        make_sync_op("guide.txt", SyncAction.COPY),
        make_sync_op("drafts.txt", SyncAction.SKIP),
    )

    apply_sync_plan(plan)

    assert copy_calls == [
        (SOURCE_ROOT / "guide.txt", DESTINATION_ROOT / "guide.txt"),
    ]
    assert mkdir_calls


def test_print_sync_plan_formats_lines() -> None:
    plan = make_plan(
        make_sync_op("guide.txt", SyncAction.COPY),
        make_sync_op("drafts.txt", SyncAction.SKIP),
    )

    output = StringIO()
    print_sync_plan(plan, output)

    lines = output.getvalue().splitlines()
    assert lines == [
        "COPY    /virtual/source/guide.txt -> /virtual/destination/guide.txt",
        "SKIP    /virtual/source/drafts.txt -> /virtual/destination/drafts.txt",
    ]


def test_apply_sync_plan_all_skip_does_not_create_dirs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    copy_calls: list[tuple[Path, Path]] = []

    def fake_copy2(src: Path, dst: Path) -> None:
        copy_calls.append((src, dst))

    mkdir_calls: list[Path] = []

    def fake_mkdir(self: Path, parents: bool = False, exist_ok: bool = False) -> None:
        mkdir_calls.append(self)

    monkeypatch.setattr("contentctl.execute.sync.shutil.copy2", fake_copy2)
    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    plan = make_plan(
        make_sync_op("drafts.txt", SyncAction.SKIP),
        make_sync_op("notes.txt", SyncAction.SKIP),
    )

    apply_sync_plan(plan)

    assert copy_calls == []
    assert mkdir_calls == []
