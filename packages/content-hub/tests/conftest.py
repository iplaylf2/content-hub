from pathlib import Path
import sys

from tests.paths import PACKAGE_ROOT, SRC_ROOT, TESTS_ROOT


def _prepend_sys_path(path: Path) -> None:
    """Ensure test and source roots are importable in pytest importlib mode."""
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


_prepend_sys_path(PACKAGE_ROOT)
_prepend_sys_path(SRC_ROOT)
_prepend_sys_path(TESTS_ROOT)
