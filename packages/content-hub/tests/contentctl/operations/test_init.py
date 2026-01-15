from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import pytest

from contentctl.operations.init import run_init


@pytest.mark.parametrize("dry_run", [True, False])
def test_init_writes_config_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, dry_run: bool
) -> None:
    write_text_mock = Mock(spec=Path.write_text)
    monkeypatch.setattr(Path, "write_text", write_text_mock)

    output = StringIO()
    run_init(
        path=tmp_path,
        dry_run=dry_run,
        verbose=False,
        output=output,
    )

    if dry_run:
        write_text_mock.assert_not_called()
    else:
        write_text_mock.assert_called_once()
        call_args = write_text_mock.call_args[0]
        content = call_args[0]
        assert isinstance(content, str)
        assert len(content) > 0


def test_init_fails_when_file_exists(tmp_path: Path) -> None:
    config_file = tmp_path / "content-hub.yaml"
    config_file.touch()

    output = StringIO()
    with pytest.raises(FileExistsError):
        run_init(
            path=tmp_path,
            dry_run=False,
            verbose=False,
            output=output,
        )


def test_init_creates_parent_directories(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    observed_mkdirs: list[tuple[Path, bool, bool]] = []

    def observe_mkdir(parents: bool = False, exist_ok: bool = False) -> None:
        # When called as path.mkdir(), the path is bound to the mock instance
        observed_mkdirs.append((tmp_path, parents, exist_ok))

    mkdir_mock = Mock(spec=Path.mkdir, side_effect=observe_mkdir)
    write_text_mock = Mock(spec=Path.write_text)

    monkeypatch.setattr(Path, "mkdir", mkdir_mock)
    monkeypatch.setattr(Path, "write_text", write_text_mock)

    output = StringIO()
    run_init(
        path=tmp_path,
        dry_run=False,
        verbose=False,
        output=output,
    )

    assert observed_mkdirs == [(tmp_path, True, True)]
