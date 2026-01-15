"""Type definitions for contentctl module fixtures."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeAlias

MakeWorkspace: TypeAlias = Callable[[str, str | Path], Any]
