from pathlib import Path

from tests.paths import FIXTURES_ROOT
from contentctl.config import Workspace


DEFAULT_CONFIG_NAME = "content-hub.yaml"
DEFAULT_PATH = "."


def fixture_path(*parts: str) -> Path:
    return FIXTURES_ROOT.joinpath(*parts)


def make_workspace(name: str, root: str | Path) -> Workspace:
    return Workspace(name=name, path=Path(root), include=(), exclude=())
