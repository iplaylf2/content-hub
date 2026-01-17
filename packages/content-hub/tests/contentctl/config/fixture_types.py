"""Type definitions for config module fixtures."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

type LoadYamlFixture = Callable[[Path], dict[str, Any]]
