"""Concurrency utilities for async streams."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable
import contextlib
import os
from typing import TypeVar

_Item = TypeVar("_Item")
_Result = TypeVar("_Result")
_StreamItem = TypeVar("_StreamItem")
_DEFAULT_BUFFER = 256
_DEFAULT_CONCURRENCY = min(32, (os.cpu_count() or 1) + 4)


def default_concurrency() -> int:
    return _DEFAULT_CONCURRENCY


async def map_concurrent(
    source: AsyncIterable[_Item],
    func: Callable[[_Item], Awaitable[_Result]],
    semaphore: asyncio.Semaphore,
    buffer: int = _DEFAULT_BUFFER,
) -> AsyncIterator[_Result]:
    async def build(
        tg: asyncio.TaskGroup,
        queue: asyncio.Queue[_Result | BaseException | None],
    ) -> None:
        async def run_item(item: _Item) -> None:
            try:
                result = await func(item)
                await queue.put(result)
            finally:
                semaphore.release()

        async for item in source:
            await semaphore.acquire()
            try:
                tg.create_task(run_item(item))
            except BaseException:
                semaphore.release()
                raise

    async for result in stream_taskgroup(build, buffer=buffer):
        yield result


async def count_stream(
    stream: AsyncIterable[_StreamItem],
    predicate: Callable[[_StreamItem], bool] | None = None,
) -> int:
    count = 0
    if predicate is None:
        async for _ in stream:
            count += 1
        return count
    async for item in stream:
        if predicate(item):
            count += 1
    return count


async def stream_taskgroup(
    builder: Callable[
        [asyncio.TaskGroup, asyncio.Queue[_StreamItem | BaseException | None]],
        Awaitable[None],
    ],
    buffer: int = _DEFAULT_BUFFER,
) -> AsyncIterator[_StreamItem]:
    queue: asyncio.Queue[_StreamItem | BaseException | None] = asyncio.Queue(
        maxsize=buffer
    )

    async def producer() -> None:
        try:
            async with asyncio.TaskGroup() as tg:
                await builder(tg, queue)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await queue.put(exc)
        else:
            await queue.put(None)

    producer_task = asyncio.create_task(producer())
    try:
        while True:
            item = await queue.get()
            match item:
                case None:
                    break
                case BaseException() as exc:
                    raise exc
                case value:
                    yield value
    finally:
        if not producer_task.done():
            producer_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await producer_task
