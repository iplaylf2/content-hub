"""Type definitions for config module fixtures."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeAlias

LoadYamlFixture: TypeAlias = Callable[[Path], dict[str, Any]]
