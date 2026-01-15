"""Type definitions for shared pytest fixtures.

This module provides type definitions for fixtures that are used
across multiple test modules.
"""

from collections.abc import Callable
from pathlib import Path

type FixturePath = Callable[..., Path]
