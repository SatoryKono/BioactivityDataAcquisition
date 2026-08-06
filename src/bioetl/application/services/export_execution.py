"""Compatibility re-export — implementation lives in `bioetl.application.services.export_lineage.export_execution`.

ARCH-REF-03 / #7704: root path kept for stable imports.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.export_lineage import export_execution as _impl
from bioetl.application.services.export_lineage.export_execution import *  # noqa: F403
from bioetl.application.services.export_lineage.export_execution import (
    __all__ as __all__,
)
from bioetl.application.services.export_lineage.export_execution import (
    _SelectableTable,
)
from bioetl.application.services.export_lineage.export_execution import (
    write_export_sidecar_manifests as write_export_sidecar_manifests,
)
from bioetl.application.services.export_lineage.export_models import (
    ExportOptions,
    ExportResult,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import DeltaReaderPort, ExportWriterPort, LoggerPort


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
    """Delegate while preserving the legacy monkeypatch seam."""
    return await _impl.export_existing_table(
        reader=reader,
        writer=writer,
        logger=logger,
        export_path=export_path,
        table_name=table_name,
        layer=layer,
        options=options,
        table_path=table_path,
        _manifest_writer=write_export_sidecar_manifests,
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
    """Delegate while preserving the legacy monkeypatch seam."""
    return _impl.write_export_manifests_if_enabled(
        writer=writer,
        table=table,
        table_name=table_name,
        layer=layer,
        options=options,
        output_path=output_path,
        row_count=row_count,
        audit_ref=audit_ref,
        redacted_columns=redacted_columns,
        _manifest_writer=write_export_sidecar_manifests,
    )
