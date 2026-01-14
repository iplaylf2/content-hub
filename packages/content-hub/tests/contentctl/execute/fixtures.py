from collections.abc import AsyncIterator
from pathlib import Path

from contentctl.plan.sync import SyncAction, SyncOperation

SOURCE_ROOT = Path("/virtual/source")
DESTINATION_ROOT = Path("/virtual/destination")


def make_sync_op(filename: str, action: SyncAction) -> SyncOperation:
    return SyncOperation(
        relative=Path(filename),
        action=action,
    )


def make_stream(*operations: SyncOperation) -> AsyncIterator[SyncOperation]:
    return _iter_operations(operations)


async def _iter_operations(
    operations: tuple[SyncOperation, ...],
) -> AsyncIterator[SyncOperation]:
    for operation in operations:
        yield operation
