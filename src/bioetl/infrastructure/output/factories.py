from bioetl.clients.base.output.contracts import (
    MetadataWriterABC,
    QualityReportABC,
    WriterABC,
)
from bioetl.infrastructure.output.impl.csv_writer import CsvWriterImpl
from bioetl.infrastructure.output.impl.metadata_writer import MetadataWriterImpl
from bioetl.infrastructure.output.impl.quality_report import QualityReportImpl


def default_writer() -> WriterABC:
    return CsvWriterImpl()


def default_metadata_writer() -> MetadataWriterABC:
    return MetadataWriterImpl()


def default_quality_reporter() -> QualityReportABC:
    return QualityReportImpl()
