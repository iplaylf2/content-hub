import asyncio
from collections.abc import AsyncIterable, AsyncIterator
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
import glob
import os
from pathlib import Path
import re

from contentctl.utils import map_concurrent, stream_taskgroup


async def plan_sync(
    source_path: Path,
    destination_path: Path,
    source_include: tuple[str, ...],
    source_exclude: tuple[str, ...],
    destination_include: tuple[str, ...],
    destination_exclude: tuple[str, ...],
    semaphore: asyncio.Semaphore,
) -> AsyncIterator[SyncOperation]:
    source_entries = _stream_source_entries(
        source_path,
        source_include,
        source_exclude,
        semaphore,
    )

    destination_root = (
        destination_path.parent if source_path.is_file() else destination_path
    )
    async for operation in _determine_actions(
        source_entries,
        destination_path=destination_root,
        destination_include=destination_include,
        destination_exclude=destination_exclude,
        action_semaphore=semaphore,
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


def _resolve_subpath(base: Path, subpath: str) -> Path:
    candidate = Path(subpath)
    if candidate.is_absolute():
        raise SyncError(f"Path must be relative: {subpath}")
    resolved = (base / candidate).resolve()
    base_resolved = base.resolve()
    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise SyncError(f"Path escapes base directory: {subpath}")
    return resolved


def _validate_sync_paths(source_path: Path, destination_path: Path) -> None:
    if _paths_overlap(source_path, destination_path):
        raise SyncError(
            "Source and destination paths overlap: "
            f"{source_path} <-> {destination_path}"
        )
    if not source_path.exists():
        raise SyncError(f"Source path not found: {source_path}")


async def _stream_source_entries(
    source_path: Path,
    source_include: tuple[str, ...],
    source_exclude: tuple[str, ...],
    scan_semaphore: asyncio.Semaphore,
) -> AsyncIterator[Path]:
    if source_path.is_file():
        rel_path = Path(source_path.name)
        if _is_selected(rel_path, source_include, source_exclude):
            yield rel_path
        return
    prune_exclude = _prune_exclude_patterns(source_exclude)
    async for source_file in _scan_source_files(
        source_path,
        prune_exclude,
        scan_semaphore,
    ):
        rel_path = source_file.relative_to(source_path)
        if _is_selected(rel_path, source_include, source_exclude):
            yield rel_path


async def _determine_actions(
    entries: AsyncIterable[Path],
    destination_path: Path,
    destination_include: tuple[str, ...],
    destination_exclude: tuple[str, ...],
    action_semaphore: asyncio.Semaphore,
) -> AsyncIterator[SyncOperation]:
    def decide(rel_path: Path) -> SyncOperation:
        destination = destination_path / rel_path
        if not _is_selected(rel_path, destination_include, destination_exclude):
            return SyncOperation(
                relative=rel_path,
                action=SyncAction.SKIP,
            )
        exists = destination.exists()
        action = SyncAction.REPLACE if exists else SyncAction.COPY
        return SyncOperation(
            relative=rel_path,
            action=action,
        )

    async def decide_async(rel_path: Path) -> SyncOperation:
        return await asyncio.to_thread(decide, rel_path)

    async for operation in map_concurrent(entries, decide_async, action_semaphore):
        yield operation


def _paths_overlap(path_a: Path, path_b: Path) -> bool:
    return path_a == path_b or path_a in path_b.parents or path_b in path_a.parents


async def _scan_source_files(
    source_path: Path,
    prune_exclude: tuple[str, ...],
    scan_semaphore: asyncio.Semaphore,
) -> AsyncIterator[Path]:
    async def build(
        tg: asyncio.TaskGroup,
        queue: asyncio.Queue[Path | BaseException | None],
    ) -> None:
        async def scan_dir(path: Path) -> None:
            rel_dir = path.relative_to(source_path)
            if _should_prune_dir(rel_dir, prune_exclude):
                return
            async with scan_semaphore:
                subdirs, files = await asyncio.to_thread(_list_directory_entries, path)
            for subdir in subdirs:
                rel_subdir = subdir.relative_to(source_path)
                if _should_prune_dir(rel_subdir, prune_exclude):
                    continue
                tg.create_task(scan_dir(subdir))
            for file in files:
                await queue.put(file)

        tg.create_task(scan_dir(source_path))

    async for path in stream_taskgroup(build):
        yield path


def _is_selected(
    rel_path: Path,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
) -> bool:
    if exclude and any(_matches_pattern(rel_path, pattern) for pattern in exclude):
        return False
    if include and not any(_matches_pattern(rel_path, pattern) for pattern in include):
        return False
    return True


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
    for pattern in prune_exclude:
        if _matches_pattern(rel_dir, pattern):
            return True
    return False


def _matches_pattern(rel_path: Path, pattern: str) -> bool:
    matcher = _compile_glob(pattern)
    return bool(matcher.match(rel_path.as_posix()))


def _has_glob_magic(pattern: str) -> bool:
    return any(char in pattern for char in "*?[")


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
