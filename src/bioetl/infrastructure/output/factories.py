from bioetl.domain.clients.base.output.contracts import (
    MetadataWriterABC,
    OutputWriterABC,
    QualityReportABC,
    WriterABC,
)
from bioetl.domain.configs import DeterminismConfig, QcConfig
from bioetl.infrastructure.output.impl.csv_writer import CsvWriterImpl
from bioetl.infrastructure.output.impl.metadata_writer import MetadataWriterImpl
from bioetl.infrastructure.output.impl.quality_report import QualityReportImpl
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


def default_writer() -> WriterABC:
    return CsvWriterImpl()


def default_metadata_writer() -> MetadataWriterABC:
    return MetadataWriterImpl()


def default_quality_reporter() -> QualityReportABC:
    return QualityReportImpl()


def default_output_writer(
    *,
    config: DeterminismConfig,
    qc_config: QcConfig | None = None,
    writer: WriterABC | None = None,
    metadata_writer: MetadataWriterABC | None = None,
    quality_reporter: QualityReportABC | None = None,
) -> OutputWriterABC:
    return UnifiedOutputWriter(
        writer=writer or default_writer(),
        metadata_writer=metadata_writer or default_metadata_writer(),
        quality_reporter=quality_reporter or default_quality_reporter(),
        config=config,
        qc_config=qc_config,
    )
