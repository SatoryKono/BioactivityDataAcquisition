"""CSV exporter with atomic writes, path confinement, and complex-type flattening."""

from __future__ import annotations

__all__ = ["CsvExporter"]

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.csv as pv

from bioetl.infrastructure.export.csv_exporter_io_ops import (
    append_to_csv as _append_to_csv,
)
from bioetl.infrastructure.export.csv_exporter_io_ops import (
    atomic_csv_write as _atomic_csv_write,
)
from bioetl.infrastructure.export.csv_exporter_io_ops import (
    raw_sidecar_is_typed as _raw_sidecar_is_typed,
)
from bioetl.infrastructure.export.csv_exporter_io_ops import (
    read_raw_table as _read_raw_table,
)
from bioetl.infrastructure.export.csv_exporter_pair_ops import (
    list_all_clear_pairs as _list_all_clear_pairs,
)
from bioetl.infrastructure.export.csv_exporter_pair_ops import (
    list_named_clear_pair as _list_named_clear_pair,
)
from bioetl.infrastructure.export.csv_exporter_pair_ops import (
    raw_csv_path as _raw_csv_path,
)
from bioetl.infrastructure.export.csv_exporter_pair_ops import (
    unlink_clear_pairs as _unlink_clear_pairs,
)
from bioetl.infrastructure.export.csv_exporter_pair_ops import (
    write_raw_and_published_pair as _write_raw_and_published_pair,
)
from bioetl.infrastructure.export.csv_exporter_table_ops import (
    deduplicate_full_rows as _deduplicate_full_rows_impl,
)
from bioetl.infrastructure.export.csv_exporter_table_ops import (
    deduplicate_table as _deduplicate_table,
)
from bioetl.infrastructure.export.csv_exporter_table_ops import (
    flatten_table_for_csv as _flatten_table_for_csv,
)
from bioetl.infrastructure.export.csv_exporter_table_ops import (
    is_complex_type as _is_complex_type,
)
from bioetl.infrastructure.export.csv_exporter_table_ops import (
    serialize_column_to_json as _serialize_column_to_json,
)
from bioetl.infrastructure.export.csv_exporter_table_ops import (
    sort_table as _sort_table,
)
from bioetl.infrastructure.export.csv_exporter_table_ops import (
    validate_spreadsheet_safe_column_names as _validate_spreadsheet_safe_column_names,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


def _export_root(base_path: Path) -> Path:
    return base_path.expanduser().resolve(strict=False)


def _resolve_table_csv_path(base_path: Path, table_name: str) -> Path:
    """Resolve ``{table_name}.csv`` under the export root; reject traversal."""
    name = table_name.strip() if isinstance(table_name, str) else ""
    if not name:
        raise ValueError("CSV export table name must be a non-empty string")
    candidate = Path(name)
    # Reject separators explicitly: on POSIX a backslash is a legal name
    # character and would otherwise pass Path.parts checks.
    if (
        candidate.is_absolute()
        or len(candidate.parts) != 1
        or candidate.name != name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
        or "\0" in name
    ):
        raise ValueError(f"invalid CSV export table name: {table_name!r}")
    root = _export_root(base_path)
    csv_path = (root / f"{name}.csv").resolve(strict=False)
    if not csv_path.is_relative_to(root):
        raise ValueError(f"CSV export path escapes export directory: {table_name!r}")
    return csv_path


def _resolve_table_export_paths(base_path: Path, table_name: str) -> tuple[Path, Path]:
    root = _export_root(base_path)
    csv_path = _resolve_table_csv_path(base_path, table_name)
    raw_path = _raw_csv_path(csv_path).resolve(strict=False)
    if not raw_path.is_relative_to(root):
        raise ValueError(
            f"CSV raw sidecar path escapes export directory: {table_name!r}"
        )
    return csv_path, raw_path


def _seed_raw_sidecar_if_missing(
    *,
    base_path: Path,
    table_name: str,
    logger: LoggerPort,
    delimiter: str = ",",
) -> None:
    """Seed ``.csv.raw`` from published CSV using confined export-root paths only."""
    csv_full_path, raw_path = _resolve_table_export_paths(base_path, table_name)
    if raw_path.exists() and _raw_sidecar_is_typed(raw_path):
        return
    source = raw_path if raw_path.exists() else csv_full_path
    table = (
        _read_raw_table(source, delimiter=delimiter)
        if raw_path.exists()
        else pv.read_csv(source, parse_options=pv.ParseOptions(delimiter=delimiter))
    )
    _write_raw_and_published_pair(
        write_raw=lambda: _atomic_csv_write(
            table, raw_path, pv.WriteOptions(), logger, spreadsheet_safe=False
        ),
        write_published=lambda: True,
        raw_path=raw_path,
        csv_path=csv_full_path,
        mode="seed",
    )


class CsvExporter:
    """CSV exporter with atomic writes and spreadsheet-safe publish path."""

    _is_complex_type = staticmethod(_is_complex_type)
    _serialize_column_to_json = staticmethod(_serialize_column_to_json)
    _flatten_for_csv = staticmethod(_flatten_table_for_csv)
    _raw_csv_path = staticmethod(_raw_csv_path)

    def __init__(
        self,
        base_path: str,
        logger: LoggerPort,
        delimiter: str = ",",
        header: bool = True,
        encoding: str = "utf-8",
        sort_by: list[str] | None = None,
        sort_ascending: bool = True,
    ) -> None:
        self.base_path = Path(base_path)
        self._logger = logger
        self.delimiter = delimiter
        self.header = header
        self.encoding = encoding
        self.sort_by = sort_by or []
        self.sort_ascending = sort_ascending

    def _export_root(self) -> Path:
        return _export_root(self.base_path)

    def _resolve_table_csv_path(self, table_name: str) -> Path:
        return _resolve_table_csv_path(self.base_path, table_name)

    def _resolve_table_export_paths(self, table_name: str) -> tuple[Path, Path]:
        return _resolve_table_export_paths(self.base_path, table_name)

    def export_table(self, table: pa.Table, output_path: str) -> Path:
        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        csv_data = self._flatten_for_csv(table)
        csv_data = self._deduplicate_full_rows(csv_data)
        if self.sort_by:
            csv_data = self._sort_table(csv_data, self.sort_by)
        _validate_spreadsheet_safe_column_names(csv_data)
        return self._overwrite_export(
            csv_data=csv_data,
            csv_full_path=target_path,
            raw_path=self._raw_csv_path(target_path),
            sort_by=self.sort_by,
        )

    def clear(self, table_name: str | None = None) -> list[Path]:
        root = self._export_root()
        if not root.exists():
            return []
        if table_name:
            csv_path = self._resolve_table_csv_path(table_name)
            pairs = [
                _list_named_clear_pair(
                    csv_path=csv_path,
                    raw_path=self._raw_csv_path(csv_path),
                    root=root,
                )
            ]
        else:
            pairs = _list_all_clear_pairs(base_path=root, root=root)
        return _unlink_clear_pairs(pairs, self._logger)

    def _sort_table(self, table: pa.Table, sort_columns: list[str]) -> pa.Table:
        return _sort_table(table, sort_columns, sort_ascending=self.sort_ascending)

    def _deduplicate(self, table: pa.Table, primary_keys: list[str]) -> pa.Table:
        return _deduplicate_table(table, primary_keys, logger=self._logger)

    def _atomic_csv_write(
        self,
        data: pa.Table,
        target_path: Path,
        write_options: pv.WriteOptions,
        *,
        spreadsheet_safe: bool = True,
    ) -> bool:
        return _atomic_csv_write(
            data,
            target_path,
            write_options,
            self._logger,
            spreadsheet_safe=spreadsheet_safe,
        )

    async def export(
        self,
        table_name: str,
        data: pa.Table,
        append: bool = True,
        sort_by: list[str] | None = None,
        primary_keys: list[str] | None = None,
    ) -> Path:
        return await asyncio.to_thread(
            self._export_sync, table_name, data, append, sort_by, primary_keys
        )

    def _export_sync(
        self,
        table_name: str,
        data: pa.Table,
        append: bool,
        sort_by: list[str] | None,
        primary_keys: list[str] | None,
    ) -> Path:
        _ = primary_keys
        root = self._export_root()
        csv_full_path, raw_path = self._resolve_table_export_paths(table_name)
        root.mkdir(parents=True, exist_ok=True)
        csv_data = self._flatten_for_csv(data)
        _validate_spreadsheet_safe_column_names(csv_data)
        if append and csv_full_path.exists():
            return self._append_existing_export(
                table_name=table_name,
                csv_data=csv_data,
                csv_full_path=csv_full_path,
                raw_path=raw_path,
            )
        return self._overwrite_export(
            csv_data=csv_data,
            csv_full_path=csv_full_path,
            raw_path=raw_path,
            sort_by=sort_by,
        )

    def _append_existing_export(
        self,
        *,
        table_name: str,
        csv_data: pa.Table,
        csv_full_path: Path,
        raw_path: Path,
    ) -> Path:
        _seed_raw_sidecar_if_missing(
            base_path=self.base_path,
            table_name=table_name,
            logger=self._logger,
            delimiter=self.delimiter,
        )
        _write_raw_and_published_pair(
            write_raw=lambda: self._append_to_csv(
                csv_data, raw_path, spreadsheet_safe=False
            ),
            write_published=lambda: self._append_to_csv(
                csv_data, csv_full_path, spreadsheet_safe=True
            ),
            raw_path=raw_path,
            csv_path=csv_full_path,
            mode="append",
        )
        return csv_full_path

    def _overwrite_export(
        self,
        *,
        csv_data: pa.Table,
        csv_full_path: Path,
        raw_path: Path,
        sort_by: list[str] | None,
    ) -> Path:
        sort_columns = sort_by if sort_by is not None else self.sort_by
        if sort_columns:
            csv_data = self._sort_table(csv_data, sort_columns)
        write_options = self._build_write_options()
        _write_raw_and_published_pair(
            write_raw=lambda: self._atomic_csv_write(
                csv_data, raw_path, write_options, spreadsheet_safe=False
            ),
            write_published=lambda: self._atomic_csv_write(
                csv_data, csv_full_path, write_options, spreadsheet_safe=True
            ),
            raw_path=raw_path,
            csv_path=csv_full_path,
            mode="write",
        )
        return csv_full_path

    async def finalize_csv(
        self,
        table_name: str,
        sort_by: list[str] | None = None,
        primary_keys: list[str] | None = None,
    ) -> Path | None:
        return await asyncio.to_thread(
            self._finalize_csv_sync, table_name, sort_by, primary_keys
        )

    def _finalize_csv_sync(
        self,
        table_name: str,
        sort_by: list[str] | None,
        primary_keys: list[str] | None,
    ) -> Path | None:
        csv_full_path, raw_path = self._resolve_table_export_paths(table_name)
        if not csv_full_path.exists() and not raw_path.exists():
            return None
        parse_options = pv.ParseOptions(delimiter=self.delimiter)
        source_path = raw_path if raw_path.exists() else csv_full_path
        table = (
            _read_raw_table(raw_path, delimiter=self.delimiter)
            if raw_path.exists()
            else pv.read_csv(source_path, parse_options=parse_options)
        )
        if primary_keys:
            table = self._deduplicate(table, primary_keys)
        sort_columns = sort_by if sort_by is not None else self.sort_by
        if sort_columns:
            table = self._sort_table(table, sort_columns)
        write_options = self._build_write_options()
        _validate_spreadsheet_safe_column_names(table)
        _write_raw_and_published_pair(
            write_raw=lambda: self._atomic_csv_write(
                table, raw_path, write_options, spreadsheet_safe=False
            ),
            write_published=lambda: self._atomic_csv_write(
                table, csv_full_path, write_options, spreadsheet_safe=True
            ),
            raw_path=raw_path,
            csv_path=csv_full_path,
            mode="write",
        )
        self._logger.info(
            "csv_export_finalized",
            table_name=table_name,
            rows=table.num_rows,
            deduplicated=bool(primary_keys),
            sorted=bool(sort_columns),
        )
        return csv_full_path

    def _append_to_csv(
        self,
        data: pa.Table,
        csv_path: Path,
        *,
        spreadsheet_safe: bool = True,
    ) -> bool:
        return _append_to_csv(
            data,
            csv_path,
            self.delimiter,
            self._logger,
            spreadsheet_safe=spreadsheet_safe,
        )

    def _deduplicate_full_rows(self, table: pa.Table) -> pa.Table:
        deduplicated = _deduplicate_full_rows_impl(table)
        removed = table.num_rows - deduplicated.num_rows
        if removed:
            self._logger.debug(
                "csv_export_table_deduplicated",
                removed_rows=removed,
            )
        return deduplicated

    def _build_write_options(self) -> pv.WriteOptions:
        return pv.WriteOptions(
            include_header=self.header,
            delimiter=self.delimiter,
        )
