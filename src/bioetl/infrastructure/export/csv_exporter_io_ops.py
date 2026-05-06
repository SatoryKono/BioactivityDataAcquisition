"""Low-level filesystem operations for CSV exporter."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.csv as pv

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


def _locked_csv_backup_path(path: Path) -> Path:
    """Return an occurrence-only backup path for a locked CSV target."""
    timestamp = int(time.time())
    return path.with_suffix(f".{timestamp}.csv")


def atomic_csv_write(
    data: pa.Table,
    target_path: Path,
    write_options: pv.WriteOptions,
    logger: LoggerPort,
) -> None:
    """Write CSV atomically to avoid file lock issues on Windows."""
    target_dir = target_path.parent
    fd, temp_path_str = tempfile.mkstemp(
        suffix=".csv.tmp",
        prefix=target_path.stem + "_",
        dir=target_dir,
    )
    temp_path = Path(temp_path_str)
    try:
        os.close(fd)
        pv.write_csv(data, temp_path, write_options=write_options)
        try:
            temp_path.replace(target_path)
        except PermissionError:
            backup_path = _locked_csv_backup_path(target_path)
            temp_path.replace(backup_path)
            logger.warning(
                "Target CSV locked, wrote to backup", backup_path=str(backup_path)
            )
            return
    except (OSError, pa.ArrowException, ValueError, TypeError, RuntimeError):
        if temp_path.exists():
            temp_path.unlink()
        raise


def append_to_csv(
    data: pa.Table,
    csv_path: Path,
    delimiter: str,
    logger: LoggerPort,
) -> None:
    """Append records to an existing CSV without reading it."""
    fd, temp_path_str = tempfile.mkstemp(
        suffix=".csv.tmp",
        prefix=csv_path.stem + "_append_",
        dir=csv_path.parent,
    )
    temp_path = Path(temp_path_str)
    try:
        os.close(fd)
        write_options = pv.WriteOptions(include_header=False, delimiter=delimiter)
        pv.write_csv(data, temp_path, write_options=write_options)
        try:
            with open(csv_path, "ab") as target, open(temp_path, "rb") as source:
                target.write(source.read())
        except PermissionError:
            backup_path = _locked_csv_backup_path(csv_path)
            logger.warning(
                "Target CSV locked during append, wrote batch to backup",
                backup_path=str(backup_path),
            )
            temp_path.replace(backup_path)
            return
    except (OSError, pa.ArrowException, ValueError, TypeError, RuntimeError):
        if temp_path.exists():
            temp_path.unlink()
        raise
    else:
        if temp_path.exists():
            temp_path.unlink()
