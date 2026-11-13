"""Low-level filesystem operations for CSV exporter."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.csv as pv

from bioetl.infrastructure.export.csv_exporter_table_ops import spreadsheet_safe_table

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


def _csv_payload_digest(path: Path) -> str:
    """Return a stable digest for one temporary CSV payload."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _locked_csv_backup_path(path: Path, *, payload_path: Path, mode: str) -> Path:
    """Return a deterministic backup path for a locked CSV target."""
    suffix = _csv_payload_digest(payload_path)
    return path.with_suffix(f".{mode}-locked.{suffix}.csv")


def _copy_csv_payload(source_path: Path, target_path: Path) -> None:
    """Publish one CSV payload without filesystem rename semantics."""
    with source_path.open("rb") as source, target_path.open("wb") as target:
        while chunk := source.read(1024 * 1024):
            target.write(chunk)
    source_path.unlink()


def _move_csv_payload(source_path: Path, target_path: Path) -> None:
    """Publish one CSV payload without relying on pathlib's concrete Path class."""
    shutil.move(os.fspath(source_path), os.fspath(target_path))


def _publish_csv_payload(source_path: Path, target_path: Path) -> None:
    """Publish one CSV payload using the safest available local filesystem path."""
    if os.name == "nt":
        # Windows cloud-backed filesystems can hang indefinitely in os.replace().
        _copy_csv_payload(source_path, target_path)
        return
    source_path.replace(target_path)


def _publish_locked_csv_backup(
    source_path: Path,
    backup_path: Path,
) -> None:
    """Publish a locked-target backup without reusing the failed target path."""
    if os.name == "nt":
        _copy_csv_payload(source_path, backup_path)
        return
    _move_csv_payload(source_path, backup_path)


def _csv_temp_directory(target_dir: Path) -> Path | None:
    """Choose a staging directory that cannot hang on Windows cloud drives."""
    if os.name == "nt":
        return None
    return target_dir


def raw_sidecar_is_typed(path: Path) -> bool:
    """Recognize the IPC stream marker without loading the complete sidecar."""
    with path.open("rb") as source:
        return source.read(4) == b"\xff\xff\xff\xff"


def _write_raw_table(table: pa.Table, path: Path) -> None:
    """Store original Arrow types; each appended batch is a separate IPC stream."""
    with path.open("wb") as sink, pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)


def _logical_raw_table(table: pa.Table) -> pa.Table:
    """Decode dictionary storage while keeping each field's logical value type."""
    for index, field in enumerate(table.schema):
        if pa.types.is_dictionary(field.type):
            logical_type = field.type.value_type
            table = table.set_column(
                index,
                field.with_type(logical_type),
                table.column(index).cast(logical_type),
            )
    return table


def read_raw_table(path: Path, *, delimiter: str = ",") -> pa.Table:
    """Read typed streams, retaining a compatibility path for old CSV sidecars."""
    if not raw_sidecar_is_typed(path):
        return pv.read_csv(path, parse_options=pv.ParseOptions(delimiter=delimiter))
    tables: list[pa.Table] = []
    with path.open("rb") as source:
        size = path.stat().st_size
        while source.tell() < size:
            with pa.ipc.open_stream(source) as reader:
                tables.append(_logical_raw_table(reader.read_all()))
    return pa.concat_tables(tables, promote_options="permissive")


def atomic_csv_write(
    data: pa.Table,
    target_path: Path,
    write_options: pv.WriteOptions,
    logger: LoggerPort,
    *,
    spreadsheet_safe: bool = True,
) -> bool:
    """Write CSV atomically to avoid file lock issues on Windows.

    When ``spreadsheet_safe`` is false, write the working raw representation
    used for append/dedupe as typed Arrow IPC streams; neutralize only the published CSV artifact.

    Returns ``True`` when the primary ``target_path`` was updated. Returns
    ``False`` when the primary target stayed locked. Raw sidecars never publish
    a spreadsheet-visible backup; safe CSV output retains its fallback.
    """
    target_dir = target_path.parent
    fd, temp_path_str = tempfile.mkstemp(
        suffix=".csv.tmp",
        prefix=target_path.stem + "_",
        dir=_csv_temp_directory(target_dir),
    )
    temp_path = Path(temp_path_str)
    try:
        os.close(fd)
        payload = spreadsheet_safe_table(data) if spreadsheet_safe else data
        if spreadsheet_safe:
            pv.write_csv(payload, temp_path, write_options=write_options)
        else:
            _write_raw_table(data, temp_path)
        try:
            _publish_csv_payload(temp_path, target_path)
        except PermissionError:
            if not spreadsheet_safe:
                temp_path.unlink()
                return False
            backup_path = _locked_csv_backup_path(
                target_path,
                payload_path=temp_path,
                mode="write",
            )
            _publish_locked_csv_backup(temp_path, backup_path)
            logger.warning(
                "Target CSV locked, wrote to backup", backup_path=str(backup_path)
            )
            return False
    except (OSError, pa.ArrowException, ValueError, TypeError, RuntimeError):
        if temp_path.exists():
            temp_path.unlink()
        raise
    return True


def append_to_csv(
    data: pa.Table,
    csv_path: Path,
    delimiter: str,
    logger: LoggerPort,
    *,
    spreadsheet_safe: bool = True,
) -> bool:
    """Append records to an existing CSV without reading it.

    When ``spreadsheet_safe`` is false, append to the working raw representation
    used for append/dedupe as typed Arrow IPC streams; neutralize only the published CSV artifact.

    Returns ``True`` when the primary ``csv_path`` was updated. Returns
    ``False`` when the primary target stayed locked. Raw sidecars never publish
    a spreadsheet-visible backup; safe CSV output retains its fallback.
    """
    fd, temp_path_str = tempfile.mkstemp(
        suffix=".csv.tmp",
        prefix=csv_path.stem + "_append_",
        dir=_csv_temp_directory(csv_path.parent),
    )
    temp_path = Path(temp_path_str)
    try:
        os.close(fd)
        write_options = pv.WriteOptions(include_header=False, delimiter=delimiter)
        payload = spreadsheet_safe_table(data) if spreadsheet_safe else data
        if spreadsheet_safe:
            pv.write_csv(payload, temp_path, write_options=write_options)
        else:
            _write_raw_table(data, temp_path)
        try:
            with open(csv_path, "ab") as target, open(temp_path, "rb") as source:
                target.write(source.read())
        except PermissionError:
            if not spreadsheet_safe:
                temp_path.unlink()
                return False
            backup_path = _locked_csv_backup_path(
                csv_path,
                payload_path=temp_path,
                mode="append",
            )
            logger.warning(
                "Target CSV locked during append, wrote batch to backup",
                backup_path=str(backup_path),
            )
            _publish_locked_csv_backup(temp_path, backup_path)
            return False
    except (OSError, pa.ArrowException, ValueError, TypeError, RuntimeError):
        if temp_path.exists():
            temp_path.unlink()
        raise
    else:
        if temp_path.exists():
            temp_path.unlink()
    return True
