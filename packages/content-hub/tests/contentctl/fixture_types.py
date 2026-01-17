"""Type definitions for contentctl module fixtures."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

type MakeWorkspace = Callable[[str, str | Path], Any]
type MakeSyncOp = Callable[[str, Any], Any]
