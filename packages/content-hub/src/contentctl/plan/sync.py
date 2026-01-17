from __future__ import annotations

import asyncio
import glob
import os
import re
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from contentctl.utils.concurrent import Emit, Spawn, stream_concurrently

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator


async def plan_sync(
    source_path: Path,
    destination_path: Path,
    source_include: tuple[str, ...],
    source_exclude: tuple[str, ...],
    destination_include: tuple[str, ...],
    destination_exclude: tuple[str, ...],
    semaphore: asyncio.Semaphore,
    *,
    allow_delete: bool = False,
) -> AsyncIterator[SyncOperation]:
    if source_path.is_file():
        operation = _plan_sync_single_file(
            source_path,
            destination_path,
            source_include,
            source_exclude,
            destination_include,
            destination_exclude,
        )
        if operation:
            yield operation
        return

    async for operation in _plan_sync_directories(
        source_path,
        destination_path,
        source_include,
        source_exclude,
        destination_include,
        destination_exclude,
        semaphore,
        allow_delete=allow_delete,
    ):
        yield operation


def resolve_sync_paths(
    source_root: Path,
    destination_root: Path,
    path: str,
) -> tuple[Path, Path]:
    source_path = _resolve_subpath(source_root, path)
    destination_path = _resolve_subpath(destination_root, path)
    _validate_sync_paths(source_path, destination_path)
    return source_path, destination_path


class SyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class SyncOperation:
    relative: Path
    action: SyncAction


class SyncAction(str, Enum):
    COPY = "COPY"
    REPLACE = "REPLACE"
    SKIP = "SKIP"
    DELETE = "DELETE"


@dataclass(frozen=True)
class _DirectoryEntries:
    files: set[Path]
    subdirs: set[Path]


def _plan_sync_single_file(
    source_path: Path,
    destination_path: Path,
    source_include: tuple[str, ...],
    source_exclude: tuple[str, ...],
    destination_include: tuple[str, ...],
    destination_exclude: tuple[str, ...],
) -> SyncOperation | None:
    rel_path = Path(source_path.name)

    if not _is_managed(rel_path, source_include, source_exclude):
        return None

    if not _is_managed(rel_path, destination_include, destination_exclude):
        return SyncOperation(relative=rel_path, action=SyncAction.SKIP)

    action = SyncAction.REPLACE if destination_path.exists() else SyncAction.COPY
    return SyncOperation(relative=rel_path, action=action)


async def _plan_sync_directories(
    source_root: Path,
    destination_root: Path,
    source_include: tuple[str, ...],
    source_exclude: tuple[str, ...],
    destination_include: tuple[str, ...],
    destination_exclude: tuple[str, ...],
    semaphore: asyncio.Semaphore,
    *,
    allow_delete: bool,
) -> AsyncIterator[SyncOperation]:
    source_prune_exclude = _prune_exclude_patterns(source_exclude)
    destination_prune_exclude = _prune_exclude_patterns(destination_exclude)

    async def process_directory_pair(
        source_dir: Path | None,
        dest_dir: Path | None,
        rel_dir: Path,
        *,
        source_pruned: bool,
        dest_pruned: bool,
    ) -> AsyncIterator[Emit[SyncOperation] | Spawn[SyncOperation]]:
        if source_dir is not None and not source_pruned:
            source_entries = await _scan_directory_single(source_dir, semaphore)
        else:
            source_entries = _DirectoryEntries(files=set(), subdirs=set())

        if dest_dir is not None and not (allow_delete and dest_pruned):
            dest_entries = await _scan_directory_single(dest_dir, semaphore)
        else:
            dest_entries = _DirectoryEntries(files=set(), subdirs=set())

        for operation in _plan_file_propagation(
            rel_dir,
            source_entries.files,
            dest_entries.files,
            source_include,
            source_exclude,
            destination_include,
            destination_exclude,
        ):
            yield Emit(operation)

        if allow_delete:
            for operation in _plan_file_cleanup(
                rel_dir,
                source_entries.files,
                dest_entries.files,
                source_include,
                source_exclude,
            ):
                yield Emit(operation)

        all_subdir_names = source_entries.subdirs | dest_entries.subdirs

        for subdir_name in all_subdir_names:
            subdir_rel_path = rel_dir / subdir_name

            in_source = subdir_name in source_entries.subdirs
            in_dest = subdir_name in dest_entries.subdirs

            source_subdir = (
                (source_dir / subdir_name) if (source_dir and in_source) else None
            )
            dest_subdir = (dest_dir / subdir_name) if (dest_dir and in_dest) else None

            sub_source_pruned = _should_prune_dir(subdir_rel_path, source_prune_exclude)
            sub_dest_pruned = _should_prune_dir(
                subdir_rel_path, destination_prune_exclude
            )

            if sub_source_pruned and (not allow_delete or sub_dest_pruned):
                continue

            yield Spawn(
                process_directory_pair(
                    source_subdir,
                    dest_subdir,
                    subdir_rel_path,
                    source_pruned=sub_source_pruned,
                    dest_pruned=sub_dest_pruned,
                )
            )

    async for operation in stream_concurrently(
        process_directory_pair(
            source_root,
            destination_root,
            Path("."),
            source_pruned=False,
            dest_pruned=False,
        )
    ):
        yield operation


async def _scan_directory_single(
    source_dir: Path,
    semaphore: asyncio.Semaphore,
) -> _DirectoryEntries:
    async with semaphore:
        source_subdirs, source_files = await asyncio.to_thread(
            _list_directory_entries, source_dir
        )

    return _DirectoryEntries(
        files={f.relative_to(source_dir) for f in source_files},
        subdirs={d.relative_to(source_dir) for d in source_subdirs},
    )


def _plan_file_propagation(
    rel_dir: Path,
    source_files: set[Path],
    dest_files: set[Path],
    source_include: tuple[str, ...],
    source_exclude: tuple[str, ...],
    destination_include: tuple[str, ...],
    destination_exclude: tuple[str, ...],
) -> Iterator[SyncOperation]:
    for file_name in source_files:
        file_rel_path = rel_dir / file_name

        if not _is_managed(file_rel_path, source_include, source_exclude):
            continue

        if not _is_managed(file_rel_path, destination_include, destination_exclude):
            yield SyncOperation(relative=file_rel_path, action=SyncAction.SKIP)
            continue

        action = SyncAction.REPLACE if file_name in dest_files else SyncAction.COPY
        yield SyncOperation(relative=file_rel_path, action=action)


def _plan_file_cleanup(
    rel_dir: Path,
    source_files: set[Path],
    dest_files: set[Path],
    source_include: tuple[str, ...],
    source_exclude: tuple[str, ...],
) -> Iterator[SyncOperation]:
    for file_name in dest_files - source_files:
        file_rel_path = rel_dir / file_name

        if _is_managed(file_rel_path, source_include, source_exclude):
            yield SyncOperation(relative=file_rel_path, action=SyncAction.DELETE)


def _list_directory_entries(path: Path) -> tuple[list[Path], list[Path]]:
    subdirs: list[Path] = []
    files: list[Path] = []
    with os.scandir(path) as iterator:
        for entry in iterator:
            if entry.is_dir(follow_symlinks=False):
                subdirs.append(Path(entry.path))
            else:
                files.append(Path(entry.path))
    return subdirs, files


def _resolve_subpath(base: Path, subpath: str) -> Path:
    candidate = Path(subpath)
    if candidate.is_absolute():
        raise SyncError(f"path must be relative: {subpath}")
    resolved = (base / candidate).resolve()
    base_resolved = base.resolve()
    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise SyncError(f"path escapes base directory: {subpath}")
    return resolved


def _validate_sync_paths(source_path: Path, destination_path: Path) -> None:
    if _paths_overlap(source_path, destination_path):
        raise SyncError(
            "source and destination paths overlap: "
            f"{source_path} <-> {destination_path}"
        )
    if not source_path.exists():
        raise SyncError(f"source path not found: {source_path}")


def _paths_overlap(path_a: Path, path_b: Path) -> bool:
    return path_a == path_b or path_a in path_b.parents or path_b in path_a.parents


def _is_managed(
    rel_path: Path,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
) -> bool:
    if exclude and any(_matches_pattern(rel_path, pattern) for pattern in exclude):
        return False
    return not include or any(
        _matches_pattern(rel_path, pattern) for pattern in include
    )


def _prune_exclude_patterns(exclude: tuple[str, ...]) -> tuple[str, ...]:
    if not exclude:
        return ()
    patterns: list[str] = []
    for pattern in exclude:
        if pattern.endswith("/**"):
            base_pattern = pattern[:-3]
            if base_pattern:
                patterns.append(base_pattern)
            continue
        if not _has_glob_magic(pattern):
            literal = pattern[:-1] if pattern.endswith("/") else pattern
            if literal:
                patterns.append(literal)
    return tuple(patterns)


def _should_prune_dir(
    rel_dir: Path,
    prune_exclude: tuple[str, ...],
) -> bool:
    if not prune_exclude:
        return False
    return any(_matches_pattern(rel_dir, pattern) for pattern in prune_exclude)


def _matches_pattern(rel_path: Path, pattern: str) -> bool:
    matcher = _compile_glob(pattern)
    return bool(matcher.match(rel_path.as_posix()))


def _has_glob_magic(pattern: str) -> bool:
    return any(char in pattern for char in "*?[")


@lru_cache(maxsize=256)
def _compile_glob(pattern: str) -> re.Pattern[str]:
    return re.compile(
        glob.translate(
            pattern,
            recursive=True,
            include_hidden=True,
            seps=("/",),
        )
    )
