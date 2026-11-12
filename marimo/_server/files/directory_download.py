# Copyright 2026 Marimo. All rights reserved.
from __future__ import annotations

import os
import stat
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

MAX_DIRECTORY_DOWNLOAD_BYTES = 1024 * 1024 * 1024
MAX_DIRECTORY_DOWNLOAD_ENTRIES = 10_000


class DirectoryDownloadTooLargeError(ValueError):
    pass


def write_directory_archive(directory: Path, destination: Path) -> None:
    """Archive regular files and directories, without following symbolic links."""
    directory = directory.resolve()
    destination = destination.resolve()
    size = 0
    entries = 0

    def on_error(error: OSError) -> None:
        raise error

    with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
        for root, dirs, files in os.walk(directory, onerror=on_error):
            root_path = Path(root)
            dirs[:] = [
                name
                for name in dirs
                if not (root_path / name).is_symlink()
                and root_path / name != destination.parent
            ]
            entries += 1
            if entries > MAX_DIRECTORY_DOWNLOAD_ENTRIES:
                raise DirectoryDownloadTooLargeError(
                    "Folder exceeds the 10,000-entry download limit"
                )
            relative = root_path.relative_to(directory)
            archive_name = Path(directory.name or "download") / relative
            archive.writestr(f"{archive_name.as_posix()}/", b"")
            for name in files:
                path = root_path / name
                if path == destination or not stat.S_ISREG(
                    path.lstat().st_mode
                ):
                    continue
                entries += 1
                if entries > MAX_DIRECTORY_DOWNLOAD_ENTRIES:
                    raise DirectoryDownloadTooLargeError(
                        "Folder exceeds the 10,000-entry download limit"
                    )
                with (
                    path.open("rb") as source,
                    archive.open(
                        (archive_name / name).as_posix(),
                        "w",
                        force_zip64=True,
                    ) as target,
                ):
                    while chunk := source.read(1024 * 1024):
                        size += len(chunk)
                        if size > MAX_DIRECTORY_DOWNLOAD_BYTES:
                            raise DirectoryDownloadTooLargeError(
                                "Folder exceeds the 1 GiB download limit"
                            )
                        target.write(chunk)
