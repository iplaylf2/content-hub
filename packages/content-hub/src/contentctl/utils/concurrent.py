import asyncio
import contextlib
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable

_Item = TypeVar("_Item")
_Result = TypeVar("_Result")

_DEFAULT_BUFFER = 256
_DEFAULT_CONCURRENCY = min(32, (os.cpu_count() or 1) + 4)


def default_concurrency() -> int:
    return _DEFAULT_CONCURRENCY


async def map_concurrent(
    source: AsyncIterable[_Item],
    func: Callable[[_Item], Awaitable[_Result]],
    semaphore: asyncio.Semaphore,
) -> AsyncIterator[_Result]:
    async def worker(item: _Item) -> AsyncIterator[Emit[_Result] | Spawn[_Result]]:
        yield Emit(await func(item))

    async def main() -> AsyncIterator[Emit[_Result] | Spawn[_Result]]:
        async for item in source:
            yield Spawn(worker(item), semaphore)

    async for result in stream_concurrently(main()):
        yield result


async def stream_concurrently(
    entry_point: AsyncIterator[Emit[_Result] | Spawn[_Result]],
    buffer: int = _DEFAULT_BUFFER,
) -> AsyncIterator[_Result]:
    queue: asyncio.Queue[_Result | _Done | _Error] = asyncio.Queue(maxsize=buffer)

    async def drive(
        iterator: AsyncIterator[Emit[_Result] | Spawn[_Result]],
        tg: asyncio.TaskGroup,
    ) -> None:
        async for op in iterator:
            match op:
                case Emit(value):
                    await queue.put(value)
                case Spawn(sub_iterator, semaphore):
                    if semaphore is None:
                        tg.create_task(drive(sub_iterator, tg))
                        continue

                    await semaphore.acquire()

                    async def drive_sem(
                        iterator: AsyncIterator[Emit[_Result] | Spawn[_Result]],
                        semaphore: asyncio.Semaphore,
                    ) -> None:
                        try:
                            await drive(iterator, tg)
                        finally:
                            semaphore.release()

                    try:
                        tg.create_task(drive_sem(sub_iterator, semaphore))
                    except:
                        semaphore.release()
                        raise

    async def producer() -> None:
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(drive(entry_point, tg))

            await queue.put(_Done())
        except asyncio.CancelledError:
            raise
        except BaseException as exc:
            await queue.put(_Error(exc))

    task = asyncio.create_task(producer())

    try:
        while True:
            item = await queue.get()

            match item:
                case _Done():
                    break
                case _Error(exc):
                    raise exc
                case _:
                    yield item

    finally:
        if not task.done():
            task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await task


@dataclass(slots=True)
class Emit[T]:
    value: T


@dataclass(slots=True)
class Spawn[T]:
    iterator: AsyncIterator[Emit[T] | Spawn[T]]
    semaphore: asyncio.Semaphore | None = None


@dataclass(slots=True)
class _Done:
    pass


@dataclass(slots=True)
class _Error:
    exc: BaseException
