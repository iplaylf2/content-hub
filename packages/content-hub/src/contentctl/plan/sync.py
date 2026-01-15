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
    delete: bool = False,
) -> AsyncIterator[SyncOperation]:
    source_files = _select_files(
        source_path,
        source_include,
        source_exclude,
        semaphore,
    )

    destination_root = (
        destination_path.parent if source_path.is_file() else destination_path
    )

    if delete and destination_root.exists():
        source_root = source_path if source_path.is_dir() else source_path.parent
        destination_files = _select_files(
            destination_path,
            destination_include,
            destination_exclude,
            semaphore,
        )
        async for operation in _plan_operations_with_delete(
            source_files,
            source_root,
            source_include,
            source_exclude,
            destination_files,
            destination_root,
            destination_include,
            destination_exclude,
            semaphore,
        ):
            yield operation
    else:
        async for operation in _plan_operations(
            source_files,
            destination_root,
            destination_include,
            destination_exclude,
            semaphore,
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


async def _select_files(
    path: Path,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
    scan_semaphore: asyncio.Semaphore,
) -> AsyncIterator[Path]:
    if path.is_file():
        rel_path = Path(path.name)
        if _is_selected(rel_path, include, exclude):
            yield rel_path
        return

    prune_exclude = _prune_exclude_patterns(exclude)
    async for file in _list_directory_files(path, prune_exclude, scan_semaphore):
        rel_path = file.relative_to(path)
        if _is_selected(rel_path, include, exclude):
            yield rel_path


async def _plan_operations(
    source_files: AsyncIterable[Path],
    destination_root: Path,
    destination_include: tuple[str, ...],
    destination_exclude: tuple[str, ...],
    semaphore: asyncio.Semaphore,
) -> AsyncIterator[SyncOperation]:
    async def decide(rel_path: Path) -> SyncOperation:
        if not _is_selected(rel_path, destination_include, destination_exclude):
            return SyncOperation(relative=rel_path, action=SyncAction.SKIP)

        destination = destination_root / rel_path
        exists = await asyncio.to_thread(destination.exists)
        action = SyncAction.REPLACE if exists else SyncAction.COPY
        return SyncOperation(relative=rel_path, action=action)

    async for operation in map_concurrent(source_files, decide, semaphore):
        yield operation


async def _plan_operations_with_delete(
    source_files: AsyncIterable[Path],
    source_root: Path,
    source_include: tuple[str, ...],
    source_exclude: tuple[str, ...],
    destination_files: AsyncIterable[Path],
    destination_root: Path,
    destination_include: tuple[str, ...],
    destination_exclude: tuple[str, ...],
    semaphore: asyncio.Semaphore,
) -> AsyncIterator[SyncOperation]:
    async def build(
        tg: asyncio.TaskGroup,
        queue: asyncio.Queue[SyncOperation | BaseException | None],
    ) -> None:
        async def plan_propagation() -> None:
            sync_ops = _plan_operations(
                source_files,
                destination_root,
                destination_include,
                destination_exclude,
                semaphore,
            )
            async for operation in sync_ops:
                await queue.put(operation)

        async def plan_cleanup() -> None:
            async for rel_path in destination_files:
                if _is_selected(rel_path, source_include, source_exclude):
                    source_file = source_root / rel_path
                    exists = await asyncio.to_thread(source_file.exists)
                    if not exists:
                        await queue.put(
                            SyncOperation(relative=rel_path, action=SyncAction.DELETE)
                        )

        tg.create_task(plan_propagation())
        tg.create_task(plan_cleanup())

    async for operation in stream_taskgroup(build):
        yield operation


def _paths_overlap(path_a: Path, path_b: Path) -> bool:
    return path_a == path_b or path_a in path_b.parents or path_b in path_a.parents


async def _list_directory_files(
    root: Path,
    prune_exclude: tuple[str, ...],
    scan_semaphore: asyncio.Semaphore,
) -> AsyncIterator[Path]:
    async def build(
        tg: asyncio.TaskGroup,
        queue: asyncio.Queue[Path | BaseException | None],
    ) -> None:
        async def scan_dir(path: Path) -> None:
            rel_dir = path.relative_to(root)
            if _should_prune_dir(rel_dir, prune_exclude):
                return
            async with scan_semaphore:
                subdirs, files = await asyncio.to_thread(_list_directory_entries, path)
            for subdir in subdirs:
                rel_subdir = subdir.relative_to(root)
                if _should_prune_dir(rel_subdir, prune_exclude):
                    continue
                tg.create_task(scan_dir(subdir))
            for file in files:
                await queue.put(file)

        tg.create_task(scan_dir(root))

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
