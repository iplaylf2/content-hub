from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, Callable


async def count_stream[StreamItem](
    stream: AsyncIterable[StreamItem],
    predicate: Callable[[StreamItem], bool] | None = None,
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
