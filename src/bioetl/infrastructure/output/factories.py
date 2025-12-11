"""Factories composing loaders for pipeline artifacts.

Naming convention:
- create_*() - creates a new instance each time
- get_*() - returns singleton/cached instance
- build_*() - uses builder pattern
"""

from typing import Any

from bioetl.domain.clients.base.output.contracts import (
    OutputFrameConverterABC,
    QualityReportABC,
)
from bioetl.domain.configs import DeterminismConfig, QualityControlConfig
from bioetl.domain.observability import MetricsPortABC
from bioetl.infrastructure.output.impl.csv_writer import CsvWriter
from bioetl.infrastructure.output.impl.metadata_writer import MetadataWriter
from bioetl.infrastructure.output.impl.quality_report import QualityReportImpl
from bioetl.infrastructure.output.unified_loader_impl import (
    UnifiedLoaderImpl,
)


def create_writer() -> CsvWriter:
    """Create a new CSV writer instance."""

    return CsvWriter()


def create_metadata_writer() -> MetadataWriter:
    """Create a new metadata writer instance."""

    return MetadataWriter()


def create_quality_reporter() -> QualityReportABC:
    """Create a new quality report writer instance."""

    return QualityReportImpl()


def create_loader(
    *,
    config: DeterminismConfig,
    qc_config: QualityControlConfig | None = None,
    writer: Any | None = None,
    metadata_writer: Any | None = None,
    quality_reporter: QualityReportABC | None = None,
    metrics_port: MetricsPortABC | None = None,
    converter: OutputFrameConverterABC | None = None,
) -> UnifiedLoaderImpl:
    """Create a new unified loader with optional overrides."""

    return UnifiedLoaderImpl(
        data_writer=writer or create_writer(),
        metadata_writer=metadata_writer or create_metadata_writer(),
        qc_report_generator=quality_reporter or create_quality_reporter(),
        config=config,
        qc_config=qc_config,
        metrics=metrics_port,
        converter=converter,
    )


__all__ = [
    "create_loader",
    "create_metadata_writer",
    "create_quality_reporter",
    "create_writer",
]
