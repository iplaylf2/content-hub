from io import StringIO
from pathlib import Path
from unittest.mock import create_autospec

import pytest

from contentctl.operations.init import run_init


@pytest.mark.parametrize("dry_run", [True, False])
def test_init_writes_config_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, dry_run: bool
) -> None:
    observed_writes: list[str] = []

    def observe_write_text(self: Path, content: str, **kwargs: object) -> None:
        observed_writes.append(content)

    write_text_mock = create_autospec(Path.write_text, side_effect=observe_write_text)
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
        assert observed_writes == []
    else:
        write_text_mock.assert_called_once()
        assert len(observed_writes) == 1
        content = observed_writes[0]
        assert isinstance(content, str) and len(content) > 0


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
    mkdir_mock = create_autospec(Path.mkdir)
    write_text_mock = create_autospec(Path.write_text)

    monkeypatch.setattr(Path, "mkdir", mkdir_mock)
    monkeypatch.setattr(Path, "write_text", write_text_mock)

    output = StringIO()
    run_init(
        path=tmp_path,
        dry_run=False,
        verbose=False,
        output=output,
    )

    mkdir_mock.assert_called_once()
    call_kwargs = mkdir_mock.call_args.kwargs
    assert call_kwargs["parents"] is True
    assert call_kwargs["exist_ok"] is True
