import asyncio
import contextlib
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable

_DEFAULT_BUFFER = 256
_DEFAULT_CONCURRENCY = min(32, (os.cpu_count() or 1) + 4)


def default_concurrency() -> int:
    return _DEFAULT_CONCURRENCY


async def map_concurrent[Item, Result](
    source: AsyncIterable[Item],
    func: Callable[[Item], Awaitable[Result]],
    semaphore: asyncio.Semaphore,
) -> AsyncIterator[Result]:
    async def worker(item: Item) -> AsyncIterator[Emit[Result] | Spawn[Result]]:
        yield Emit(await func(item))

    async def main() -> AsyncIterator[Emit[Result] | Spawn[Result]]:
        async for item in source:
            yield Spawn(worker(item), semaphore)

    async for result in stream_concurrently(main()):
        yield result


async def stream_concurrently[Result](
    entry_point: AsyncIterator[Emit[Result] | Spawn[Result]],
    buffer: int = _DEFAULT_BUFFER,
) -> AsyncIterator[Result]:
    queue: asyncio.Queue[Result | _Done | _Error] = asyncio.Queue(maxsize=buffer)

    async def drive(
        iterator: AsyncIterator[Emit[Result] | Spawn[Result]],
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
                        iterator: AsyncIterator[Emit[Result] | Spawn[Result]],
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
            await queue.put(_Error(_normalize_exception(exc)))

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


def _normalize_exception(exc: BaseException) -> BaseException:
    if not isinstance(exc, ExceptionGroup):
        return exc

    group = cast("ExceptionGroup[Exception]", exc)
    exceptions = group.exceptions
    if len(exceptions) != 1:
        return cast("BaseException", exc)

    return _normalize_exception(exceptions[0])
