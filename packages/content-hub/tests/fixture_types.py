"""Type definitions for shared pytest fixtures.

This module provides type definitions for fixtures that are used
across multiple test modules.
"""

from collections.abc import Callable
from pathlib import Path
from typing import TypeAlias

FixturePath: TypeAlias = Callable[..., Path]
