"""Export adapters for various formats.

Implements RULES.md §2.1 - Data export functionality.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

__all__ = [
    "CsvExporter",
    "DQReportWriter",
    "ExportCatalogAdapter",
    "ExportWriterAdapter",
]

_EXPORT_ATTRIBUTE_MODULES = {
    "CsvExporter": "bioetl.infrastructure.export.csv_exporter",
    "DQReportWriter": "bioetl.infrastructure.export.dq_report_writer",
    "ExportCatalogAdapter": "bioetl.infrastructure.export.export_catalog_adapter",
    "ExportWriterAdapter": "bioetl.infrastructure.export.export_writer_adapter",
}


def __getattr__(
    name: str,
) -> Any:  # Any: Dynamically returns attributes from lazily imported modules.
    """Lazily import export adapters to avoid importing optional stacks eagerly."""
    if TYPE_CHECKING:
        raise AttributeError
    module_name = _EXPORT_ATTRIBUTE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(module_name), name)
