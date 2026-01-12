"""Planning for sync operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
from pathlib import PurePosixPath


def plan_sync(
    source_root: Path,
    target_root: Path,
    path: str,
    source_include: tuple[str, ...],
    source_exclude: tuple[str, ...],
    target_include: tuple[str, ...],
    target_exclude: tuple[str, ...],
) -> SyncPlan:
    source_path = _resolve_subpath(source_root, path)
    target_path = _resolve_subpath(target_root, path)
    source_is_dir = source_path.is_dir()

    if _paths_overlap(source_path, target_path):
        raise SyncError(
            f"Source and target paths overlap: {source_path} <-> {target_path}"
        )

    if not source_path.exists():
        raise SyncError(f"Source path not found: {source_path}")

    operations = _plan_copy_operations(
        source_path=source_path,
        target_path=target_path,
        source_include=source_include,
        source_exclude=source_exclude,
        target_include=target_include,
        target_exclude=target_exclude,
    )
    return SyncPlan(
        source_path=source_path,
        target_path=target_path,
        source_is_dir=source_is_dir,
        operations=tuple(operations),
    )


class SyncError(RuntimeError):
    """Raised when a sync operation cannot be completed."""


@dataclass(frozen=True)
class SyncPlan:
    source_path: Path
    target_path: Path
    source_is_dir: bool
    operations: tuple["SyncOperation", ...]


@dataclass(frozen=True)
class SyncOperation:
    source: Path
    destination: Path
    action: "SyncAction"


class SyncAction(str, Enum):
    COPY = "COPY"
    REPLACE = "REPLACE"
    SKIP = "SKIP"


def _resolve_subpath(base: Path, subpath: str) -> Path:
    candidate = Path(subpath)
    if candidate.is_absolute():
        raise SyncError(f"Path must be relative: {subpath}")
    resolved = (base / candidate).resolve()
    base_resolved = base.resolve()
    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise SyncError(f"Path escapes base directory: {subpath}")
    return resolved


def _paths_overlap(path_a: Path, path_b: Path) -> bool:
    return path_a == path_b or path_a in path_b.parents or path_b in path_a.parents


def _plan_copy_operations(
    source_path: Path,
    target_path: Path,
    source_include: tuple[str, ...],
    source_exclude: tuple[str, ...],
    target_include: tuple[str, ...],
    target_exclude: tuple[str, ...],
) -> list[SyncOperation]:
    if source_path.is_file():
        rel_to_root = Path(source_path.name)
        if not _is_selected(rel_to_root, source_include, source_exclude):
            return []
        if not _is_selected(rel_to_root, target_include, target_exclude):
            return [
                SyncOperation(
                    source=source_path,
                    destination=target_path,
                    action=SyncAction.SKIP,
                )
            ]
        action = SyncAction.REPLACE if target_path.exists() else SyncAction.COPY
        return [
            SyncOperation(
                source=source_path,
                destination=target_path,
                action=action,
            )
        ]

    ops: list[SyncOperation] = []
    for dirpath, _dirnames, filenames in os.walk(source_path):
        for filename in filenames:
            source_file = Path(dirpath) / filename
            rel_to_root = source_file.relative_to(source_path)
            if not _is_selected(rel_to_root, source_include, source_exclude):
                continue
            if not _is_selected(rel_to_root, target_include, target_exclude):
                ops.append(
                    SyncOperation(
                        source=source_file,
                        destination=target_path / rel_to_root,
                        action=SyncAction.SKIP,
                    )
                )
                continue
            destination = target_path / rel_to_root
            action = SyncAction.REPLACE if destination.exists() else SyncAction.COPY
            ops.append(
                SyncOperation(
                    source=source_file,
                    destination=destination,
                    action=action,
                )
            )
    return ops


def _is_selected(
    rel_path: Path,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
) -> bool:
    rel_posix = PurePosixPath(rel_path.as_posix())
    if exclude and any(rel_posix.match(pattern) for pattern in exclude):
        return False
    if include and not any(rel_posix.match(pattern) for pattern in include):
        return False
    return True
