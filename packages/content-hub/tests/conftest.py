import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def fixture_path() -> Callable[..., Path]:
    """Return a function to get fixture file paths."""

    def _fixture_path(*parts: str) -> Path:
        return FIXTURE_ROOT.joinpath(*parts)

    return _fixture_path


@pytest.fixture
def fixture_dir() -> Path:
    """Return the path to the _fixture directory."""
    return FIXTURE_ROOT


TESTS_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = TESTS_ROOT.parent
SRC_ROOT = PACKAGE_ROOT / "src"
FIXTURE_ROOT = TESTS_ROOT / "_fixture"


def _prepend_sys_path(path: Path) -> None:
    """Ensure test and source roots are importable in pytest importlib mode."""
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


_prepend_sys_path(PACKAGE_ROOT)
_prepend_sys_path(SRC_ROOT)
_prepend_sys_path(TESTS_ROOT)
