from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from contentctl.execute.sync import apply_sync_plan, print_sync_plan
from contentctl.plan.sync import SyncAction, SyncOperation, SyncPlan


def test_apply_sync_plan_copies_non_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    copy_calls: list[tuple[Path, Path]] = []

    def fake_copy2(src: Path, dst: Path) -> None:
        copy_calls.append((src, dst))

    mkdir_calls: list[Path] = []

    def fake_mkdir(self: Path, parents: bool = False, exist_ok: bool = False) -> None:
        mkdir_calls.append(self)

    monkeypatch.setattr("contentctl.execute.sync.shutil.copy2", fake_copy2)
    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    plan = SyncPlan(
        source_path=Path("/virtual/source"),
        target_path=Path("/virtual/target"),
        source_is_dir=True,
        operations=(
            SyncOperation(
                source=Path("/virtual/source/a.txt"),
                destination=Path("/virtual/target/a.txt"),
                action=SyncAction.COPY,
            ),
            SyncOperation(
                source=Path("/virtual/source/b.txt"),
                destination=Path("/virtual/target/b.txt"),
                action=SyncAction.SKIP,
            ),
            SyncOperation(
                source=Path("/virtual/source/c.txt"),
                destination=Path("/virtual/target/c.txt"),
                action=SyncAction.REPLACE,
            ),
        ),
    )

    apply_sync_plan(plan)

    assert copy_calls == [
        (Path("/virtual/source/a.txt"), Path("/virtual/target/a.txt")),
        (Path("/virtual/source/c.txt"), Path("/virtual/target/c.txt")),
    ]
    assert mkdir_calls


def test_print_sync_plan_formats_lines() -> None:
    plan = SyncPlan(
        source_path=Path("/virtual/source"),
        target_path=Path("/virtual/target"),
        source_is_dir=False,
        operations=(
            SyncOperation(
                source=Path("/virtual/source/a.txt"),
                destination=Path("/virtual/target/a.txt"),
                action=SyncAction.COPY,
            ),
            SyncOperation(
                source=Path("/virtual/source/b.txt"),
                destination=Path("/virtual/target/b.txt"),
                action=SyncAction.SKIP,
            ),
        ),
    )

    output = StringIO()
    print_sync_plan(plan, output)

    lines = output.getvalue().splitlines()
    assert lines == [
        "COPY    /virtual/source/a.txt -> /virtual/target/a.txt",
        "SKIP    /virtual/source/b.txt -> /virtual/target/b.txt",
    ]


def test_apply_sync_plan_no_ops_does_not_create_dirs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mkdir_calls: list[Path] = []

    def fake_mkdir(self: Path, parents: bool = False, exist_ok: bool = False) -> None:
        mkdir_calls.append(self)

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    plan = SyncPlan(
        source_path=Path("/virtual/source/note.txt"),
        target_path=Path("/virtual/target/note.txt"),
        source_is_dir=False,
        operations=(),
    )

    apply_sync_plan(plan)

    assert mkdir_calls == []
