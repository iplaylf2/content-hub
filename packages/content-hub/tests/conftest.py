from pathlib import Path
import sys
from collections.abc import Callable

import pytest


@pytest.fixture
def fixture_path() -> Callable[..., Path]:
    """Return a function to get fixture file paths."""

    def _fixture_path(*parts: str) -> Path:
        return FIXTURES_ROOT.joinpath(*parts)

    return _fixture_path


TESTS_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = TESTS_ROOT.parent
SRC_ROOT = PACKAGE_ROOT / "src"
FIXTURES_ROOT = TESTS_ROOT / "_fixtures"


def _prepend_sys_path(path: Path) -> None:
    """Ensure test and source roots are importable in pytest importlib mode."""
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


_prepend_sys_path(PACKAGE_ROOT)
_prepend_sys_path(SRC_ROOT)
_prepend_sys_path(TESTS_ROOT)
