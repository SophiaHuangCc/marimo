# Copyright 2026 Marimo. All rights reserved.
from __future__ import annotations

import os
from typing import TYPE_CHECKING
from zipfile import ZipFile

import pytest

from marimo._server.files import directory_download
from marimo._server.files.directory_download import (
    DirectoryDownloadTooLargeError,
    write_directory_archive,
)
from marimo._utils.platform import is_windows

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.skipif(is_windows(), reason="Requires symlinks and FIFOs")
def test_skips_links_and_special_files(tmp_path: Path) -> None:
    folder = tmp_path / "results"
    folder.mkdir()
    (tmp_path / "secret.txt").write_text("outside")
    (folder / "data.txt").write_text("inside")
    (folder / "link.txt").symlink_to(tmp_path / "secret.txt")
    (folder / "cycle").symlink_to(folder, target_is_directory=True)
    (folder / "broken").symlink_to(tmp_path / "missing")
    os.mkfifo(folder / "pipe")
    destination = tmp_path / "results.zip"

    write_directory_archive(folder, destination)

    with ZipFile(destination) as archive:
        assert {name: archive.read(name) for name in archive.namelist()} == {
            "results/": b"",
            "results/data.txt": b"inside",
        }


@pytest.mark.parametrize(
    ("limit", "value"),
    [
        ("MAX_DIRECTORY_DOWNLOAD_BYTES", 3),
        ("MAX_DIRECTORY_DOWNLOAD_ENTRIES", 1),
    ],
)
def test_archive_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, limit: str, value: int
) -> None:
    folder = tmp_path / "results"
    folder.mkdir()
    (folder / "data.txt").write_text("too large")
    monkeypatch.setattr(directory_download, limit, value)

    with pytest.raises(DirectoryDownloadTooLargeError):
        write_directory_archive(folder, tmp_path / "results.zip")


def test_does_not_archive_its_own_temporary_directory(tmp_path: Path) -> None:
    (tmp_path / "data.txt").write_text("data")
    temporary = tmp_path / "marimo-download-example"
    temporary.mkdir()
    destination = temporary / "download.zip"

    write_directory_archive(tmp_path, destination)

    with ZipFile(destination) as archive:
        assert archive.namelist() == [
            f"{tmp_path.name}/",
            f"{tmp_path.name}/data.txt",
        ]
