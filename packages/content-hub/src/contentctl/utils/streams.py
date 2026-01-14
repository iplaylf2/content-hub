from collections.abc import AsyncIterable, Callable
from typing import TypeVar

_StreamItem = TypeVar("_StreamItem")


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
