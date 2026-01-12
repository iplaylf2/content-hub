from __future__ import annotations

from pathlib import Path


TESTS_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = TESTS_ROOT.parent
SRC_ROOT = PACKAGE_ROOT / "src"
FIXTURES_ROOT = TESTS_ROOT / "_fixtures"
