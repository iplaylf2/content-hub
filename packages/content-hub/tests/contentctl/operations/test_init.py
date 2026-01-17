from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import create_autospec

import pytest
from contentctl.gateway.defaults import DEFAULT_CONFIG_FILENAME
from contentctl.operations.init import run_init

if TYPE_CHECKING:
    from tests.fixture_types import FixturePath


@pytest.mark.parametrize(
    ("init_dir_name", "config_filename"),
    [("virtual-init", DEFAULT_CONFIG_FILENAME)],
)
def test_init_dry_run_skips_write(
    fixture_path: FixturePath,
    monkeypatch: pytest.MonkeyPatch,
    init_dir_name: str,
    config_filename: str,
) -> None:
    observed_writes: list[str] = []
    init_dir = fixture_path(init_dir_name)

    def observe_write_text(_self: Path, content: str, **_kwargs: object) -> None:
        observed_writes.append(content)

    write_text_mock = create_autospec(Path.write_text, side_effect=observe_write_text)
    monkeypatch.setattr(Path, "write_text", write_text_mock)

    output = StringIO()
    run_init(
        path=init_dir,
        config_filename=config_filename,
        dry_run=True,
        verbose=False,
        output=output,
    )

    write_text_mock.assert_not_called()
    assert observed_writes == []


@pytest.mark.parametrize(
    ("init_dir_name", "config_filename"),
    [("virtual-init", DEFAULT_CONFIG_FILENAME)],
)
def test_init_fails_when_file_exists(
    fixture_path: FixturePath,
    monkeypatch: pytest.MonkeyPatch,
    init_dir_name: str,
    config_filename: str,
) -> None:
    init_dir = fixture_path(init_dir_name)
    exists_mock = create_autospec(Path.exists, return_value=True)
    monkeypatch.setattr(Path, "exists", exists_mock)

    output = StringIO()
    with pytest.raises(FileExistsError):
        run_init(
            path=init_dir,
            config_filename=config_filename,
            dry_run=False,
            verbose=False,
            output=output,
        )


@pytest.mark.parametrize(
    ("init_dir_name", "config_filename"),
    [("virtual-init", DEFAULT_CONFIG_FILENAME)],
)
def test_init_writes_config_and_creates_directories(
    fixture_path: FixturePath,
    monkeypatch: pytest.MonkeyPatch,
    init_dir_name: str,
    config_filename: str,
) -> None:
    observed_writes: list[str] = []
    init_dir = fixture_path(init_dir_name)

    def observe_write_text(_self: Path, content: str, **_kwargs: object) -> None:
        observed_writes.append(content)

    mkdir_mock = create_autospec(Path.mkdir)
    write_text_mock = create_autospec(Path.write_text, side_effect=observe_write_text)

    monkeypatch.setattr(Path, "mkdir", mkdir_mock)
    monkeypatch.setattr(Path, "write_text", write_text_mock)

    output = StringIO()
    run_init(
        path=init_dir,
        config_filename=config_filename,
        dry_run=False,
        verbose=False,
        output=output,
    )

    mkdir_mock.assert_called_once()
    call_kwargs = mkdir_mock.call_args.kwargs
    assert call_kwargs["parents"] is True
    assert call_kwargs["exist_ok"] is True
    write_text_mock.assert_called_once()
    assert len(observed_writes) == 1
    assert observed_writes[0]
