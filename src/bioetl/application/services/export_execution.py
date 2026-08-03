"""Execution helpers for governed table exports."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

from bioetl.application.services.export_manifests import write_export_sidecar_manifests
from bioetl.application.services.export_models import ExportOptions, ExportResult

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        DeltaReaderPort,
        ExportWriterPort,
        LoggerPort,
    )

_PRIVILEGED_EXPORT_ROLES = frozenset({"admin", "exporter", "investigator"})
_SENSITIVE_COLUMN_TOKENS = frozenset(
    {
        "payload",
        "raw",
        "secret",
        "token",
        "password",
        "credential",
    }
)


class _SchemaField(Protocol):
    """Named field surface exposed by export table schemas."""

    @property
    def name(self) -> str: ...


class _ExportSchema(Protocol):
    """Iterable schema surface used by export governance."""

    def __iter__(self) -> Iterator[_SchemaField]: ...


@runtime_checkable
class _SelectableTable(Protocol):
    """Minimal table surface needed by export redaction helpers."""

    @property
    def schema(self) -> _ExportSchema: ...

    @property
    def num_rows(self) -> int: ...

    def select(self, columns: list[str]) -> _SelectableTable: ...


async def export_existing_table(
    *,
    reader: DeltaReaderPort,
    writer: ExportWriterPort,
    logger: LoggerPort,
    export_path: Path,
    table_name: str,
    layer: str,
    options: ExportOptions,
    table_path: Path | str,
) -> ExportResult:
    """Export an existing table and build success result."""
    logger.info(
        "Reading table for export",
        table=table_name,
        layer=layer,
        format=options.format,
        limit=options.limit,
    )
    table_path_str = (
        table_path if isinstance(table_path, str) else table_path.as_posix()
    )
    table_payload = await reader.read_table(
        table_path_str, columns=options.columns, limit=options.limit
    )
    if not isinstance(table_payload, _SelectableTable):
        raise TypeError("Delta reader returned a table without export capabilities")
    export_table, redacted_columns = apply_redaction_policy(
        table=table_payload,
        options=options,
    )
    row_count = export_table.num_rows
    audit_ref = build_audit_ref(
        table_name=table_name,
        layer=layer,
        options=options,
        row_count=row_count,
        output_columns=tuple(field.name for field in export_table.schema),
        redacted_columns=redacted_columns,
    )
    output_path = Path(
        writer.write_export(
            table=cast(
                Any, export_table
            ),  # Any: export port accepts Arrow/table duck-type
            table_name=table_name,
            layer=layer,
            fmt=options.format,
            output_dir=str(options.output_path or export_path),
        )
    )
    manifest_paths = write_export_manifests_if_enabled(
        writer=writer,
        table=cast(Any, export_table),  # Any: export port accepts Arrow/table duck-type
        table_name=table_name,
        layer=layer,
        options=options,
        output_path=output_path,
        row_count=row_count,
        audit_ref=audit_ref,
        redacted_columns=redacted_columns,
    )
    logger.info(
        "Export completed",
        table=table_name,
        rows=row_count,
        output=str(output_path),
        audit_ref=audit_ref,
        role=options.role,
        redaction_profile=options.redaction_profile,
        redacted_columns=list(redacted_columns),
        manifests=[str(path) for path in manifest_paths],
    )
    return create_success_result(
        table_name=table_name,
        layer=layer,
        options=options,
        output_path=output_path,
        row_count=row_count,
        manifest_paths=manifest_paths,
        audit_ref=audit_ref,
        redacted_columns=redacted_columns,
    )


def write_export_manifests_if_enabled(
    *,
    writer: ExportWriterPort,
    table: _SelectableTable,
    table_name: str,
    layer: str,
    options: ExportOptions,
    output_path: Path,
    row_count: int,
    audit_ref: str,
    redacted_columns: tuple[str, ...],
) -> tuple[Path, ...]:
    if not options.include_manifests:
        return ()
    return write_export_sidecar_manifests(
        writer=writer,
        table=cast(Any, table),  # Any: export port accepts Arrow/table duck-type
        table_name=table_name,
        layer=layer,
        export_format=options.format,
        output_path=output_path,
        row_count=row_count,
        timestamp_opts=(
            options.manifest_generated_at,
            options.allow_nondeterministic_manifest_timestamp,
            None,
        ),
        run_ids=options.run_ids,
        code_revision=options.code_revision,
        access=(
            options.requester,
            options.role,
            options.filters_hash,
            options.expires_at,
            options.redaction_profile,
            audit_ref,
        ),
        redacted_columns=redacted_columns,
        strict=options.manifest_strict,
    )


def create_missing_table_result(
    *,
    table_name: str,
    layer: str,
    options: ExportOptions,
    table_path: Path | str,
) -> ExportResult:
    """Build result payload for missing table case."""
    return ExportResult(
        table_name=table_name,
        layer=layer,
        format=options.format,
        output_path=None,
        row_count=0,
        error=f"Table not found: {table_path}",
        audit_ref=build_audit_ref(
            table_name=table_name,
            layer=layer,
            options=options,
            row_count=0,
            output_columns=(),
            redacted_columns=(),
        ),
        expires_at=options.expires_at,
        redaction_profile=options.redaction_profile,
    )


def create_success_result(
    *,
    table_name: str,
    layer: str,
    options: ExportOptions,
    output_path: Path,
    row_count: int,
    manifest_paths: tuple[Path, ...] = (),
    audit_ref: str | None = None,
    redacted_columns: tuple[str, ...] = (),
) -> ExportResult:
    """Build result payload for successful export case."""
    return ExportResult(
        table_name=table_name,
        layer=layer,
        format=options.format,
        output_path=output_path,
        row_count=row_count,
        manifest_paths=manifest_paths,
        audit_ref=audit_ref,
        checksum_manifest_path=manifest_paths[-1] if manifest_paths else None,
        expires_at=options.expires_at,
        redaction_profile=options.redaction_profile,
        redacted_columns=redacted_columns,
    )


def create_failed_result(
    *,
    table_name: str,
    layer: str,
    options: ExportOptions,
    error: str,
) -> ExportResult:
    """Build result payload for failed export case."""
    return ExportResult(
        table_name=table_name,
        layer=layer,
        format=options.format,
        output_path=None,
        row_count=0,
        error=error,
        audit_ref=build_audit_ref(
            table_name=table_name,
            layer=layer,
            options=options,
            row_count=0,
            output_columns=(),
            redacted_columns=(),
        ),
        expires_at=options.expires_at,
        redaction_profile=options.redaction_profile,
    )


def get_layer_base_path(*, layer: str, silver_path: Path, gold_path: Path) -> Path:
    """Resolve the root path for one export layer."""
    if layer == "silver":
        return silver_path
    if layer == "gold":
        return gold_path
    raise ValueError(f"Invalid layer: {layer}")


def apply_redaction_policy(
    *,
    table: _SelectableTable,
    options: ExportOptions,
) -> tuple[_SelectableTable, tuple[str, ...]]:
    """Apply deterministic role-sensitive column redaction."""
    column_names = tuple(field.name for field in table.schema)
    sensitive_columns = _sensitive_export_columns(column_names)
    if not _should_redact_columns(sensitive_columns, options=options):
        return table, ()
    retained_columns = _retained_export_columns(
        column_names=column_names,
        sensitive_columns=sensitive_columns,
        role=options.role,
    )
    return table.select(retained_columns), sensitive_columns


def _sensitive_export_columns(column_names: tuple[str, ...]) -> tuple[str, ...]:
    """Return governed sensitive columns from an export schema."""
    return tuple(name for name in column_names if _is_sensitive_export_column(name))


def _should_redact_columns(
    sensitive_columns: tuple[str, ...],
    *,
    options: ExportOptions,
) -> bool:
    """Return whether sensitive columns must be removed for this requester."""
    if not sensitive_columns:
        return False
    if options.role in _PRIVILEGED_EXPORT_ROLES:
        return False
    if options.redaction_profile == "none":
        raise PermissionError(
            f"Role '{options.role}' cannot export raw sensitive fields"
        )
    return True


def _retained_export_columns(
    *,
    column_names: tuple[str, ...],
    sensitive_columns: tuple[str, ...],
    role: str,
) -> list[str]:
    """Return non-sensitive columns, or fail when nothing can be exported."""
    sensitive_names = set(sensitive_columns)
    retained_columns = [name for name in column_names if name not in sensitive_names]
    if not retained_columns:
        raise PermissionError(
            f"Role '{role}' cannot export a table containing only sensitive fields"
        )
    return retained_columns


def build_audit_ref(
    *,
    table_name: str,
    layer: str,
    options: ExportOptions,
    row_count: int,
    output_columns: tuple[str, ...],
    redacted_columns: tuple[str, ...],
) -> str:
    """Return a stable audit reference without writing from application code."""
    payload = build_audit_ref_payload(
        table_name=table_name,
        layer=layer,
        options=options,
        row_count=row_count,
        output_columns=output_columns,
        redacted_columns=redacted_columns,
    )
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return f"export-audit:{digest[:24]}"


def build_audit_ref_payload(
    *,
    table_name: str,
    layer: str,
    options: ExportOptions,
    row_count: int,
    output_columns: tuple[str, ...],
    redacted_columns: tuple[str, ...],
) -> dict[str, object]:
    """Build canonical audit identity material for one export."""
    return {
        "table_name": table_name,
        "layer": layer,
        "format": options.format,
        "row_count": row_count,
        "columns": output_columns,
        "redacted_columns": redacted_columns,
        "requester": options.requester,
        "role": options.role,
        "filters_hash": options.filters_hash,
        "expires_at": options.expires_at,
        "redaction_profile": options.redaction_profile,
        "run_ids": options.run_ids,
        "code_revision": options.code_revision,
    }


def _is_sensitive_export_column(column_name: str) -> bool:
    """Return whether a column name is governed as sensitive export material."""
    normalized = column_name.lower()
    return any(token in normalized for token in _SENSITIVE_COLUMN_TOKENS)


__all__ = [
    "apply_redaction_policy",
    "build_audit_ref",
    "build_audit_ref_payload",
    "create_failed_result",
    "create_missing_table_result",
    "create_success_result",
    "export_existing_table",
    "get_layer_base_path",
    "write_export_manifests_if_enabled",
]
