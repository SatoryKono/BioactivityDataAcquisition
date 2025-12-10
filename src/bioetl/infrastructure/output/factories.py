"""Factories composing loaders for pipeline artifacts."""

from typing import Any

from bioetl.domain.clients.base.output.contracts import (
    OutputFrameConverterABC,
    QualityReportABC,
)
from bioetl.domain.configs import DeterminismConfig, QcConfig
from bioetl.domain.observability import MetricsPortABC
from bioetl.infrastructure.output.impl.csv_writer import CsvWriter
from bioetl.infrastructure.output.impl.metadata_writer import MetadataWriter
from bioetl.infrastructure.output.impl.quality_report import QualityReportImpl
from bioetl.infrastructure.output.unified_loader_impl import (
    UnifiedLoaderImpl,
)


def default_writer() -> CsvWriter:
    """Create the default CSV writer implementation."""

    return CsvWriter()


def default_metadata_writer() -> MetadataWriter:
    """Create the metadata writer that stores sidecar files."""

    return MetadataWriter()


def default_quality_reporter() -> QualityReportABC:
    """Provide the default quality report writer implementation."""

    return QualityReportImpl()


def default_loader(
    *,
    config: DeterminismConfig,
    qc_config: QcConfig | None = None,
    writer: Any | None = None,
    metadata_writer: Any | None = None,
    quality_reporter: QualityReportABC | None = None,
    metrics_port: MetricsPortABC | None = None,
    converter: OutputFrameConverterABC | None = None,
) -> UnifiedLoaderImpl:
    """Compose the unified loader with optional overrides."""

    return UnifiedLoaderImpl(
        writer=writer or default_writer(),
        metadata_writer=metadata_writer or default_metadata_writer(),
        quality_reporter=quality_reporter or default_quality_reporter(),
        config=config,
        qc_config=qc_config,
        metrics=metrics_port,
        converter=converter,
    )
