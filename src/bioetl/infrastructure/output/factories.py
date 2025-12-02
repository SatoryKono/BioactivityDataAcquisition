from bioetl.infrastructure.output.contracts import MetadataWriterABC, WriterABC
from bioetl.infrastructure.output.impl.csv_writer import CsvWriterImpl
from bioetl.infrastructure.output.impl.metadata_writer import MetadataWriterImpl


def default_writer() -> WriterABC:
    return CsvWriterImpl()


def default_metadata_writer() -> MetadataWriterABC:
    return MetadataWriterImpl()

