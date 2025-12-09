"""Factories composing output writers for pipeline artifacts."""

from bioetl.domain.clients.base.output.contracts import (
    MetadataWriterABC,
    OutputWriterABC,
    OutputFrameConverterABC,
    QualityReportABC,
    WriterABC,
)
from bioetl.domain.configs import DeterminismConfig, QcConfig
from bioetl.domain.observability import MetricsPortABC
from bioetl.infrastructure.output.impl.csv_writer import CsvWriterImpl
from bioetl.infrastructure.output.impl.metadata_writer import MetadataWriterImpl
from bioetl.infrastructure.output.impl.quality_report import QualityReportImpl
from bioetl.infrastructure.output.unified_output_writer_impl import (
    UnifiedOutputWriterImpl,
)


def default_writer() -> WriterABC:
    """Create the default CSV writer implementation."""

    return CsvWriterImpl()


def default_metadata_writer() -> MetadataWriterABC:
    """Create the metadata writer that stores sidecar files."""

    return MetadataWriterImpl()


def default_quality_reporter() -> QualityReportABC:
    """Provide the default quality report writer implementation."""

    return QualityReportImpl()


def default_output_writer(
    *,
    config: DeterminismConfig,
    qc_config: QcConfig | None = None,
    writer: WriterABC | None = None,
    metadata_writer: MetadataWriterABC | None = None,
    quality_reporter: QualityReportABC | None = None,
    metrics_port: MetricsPortABC | None = None,
    converter: OutputFrameConverterABC | None = None,
) -> OutputWriterABC:
    """Compose the unified output writer with optional overrides."""

    return UnifiedOutputWriterImpl(
        writer=writer or default_writer(),
        metadata_writer=metadata_writer or default_metadata_writer(),
        quality_reporter=quality_reporter or default_quality_reporter(),
        config=config,
        qc_config=qc_config,
        metrics=metrics_port,
        converter=converter,
    )
