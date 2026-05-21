"""Low-level filesystem operations for CSV exporter."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.csv as pv

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


def _csv_payload_digest(path: Path) -> str:
    """Return a stable digest for one temporary CSV payload."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _locked_csv_backup_path(path: Path, *, payload_path: Path, mode: str) -> Path:
    """Return a deterministic backup path for a locked CSV target."""
    suffix = _csv_payload_digest(payload_path)
    return path.with_suffix(f".{mode}-locked.{suffix}.csv")


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
            backup_path = _locked_csv_backup_path(
                target_path,
                payload_path=temp_path,
                mode="write",
            )
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
            backup_path = _locked_csv_backup_path(
                csv_path,
                payload_path=temp_path,
                mode="append",
            )
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
