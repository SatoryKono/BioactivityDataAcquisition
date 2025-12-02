from bioetl.output.contracts import MetadataWriterABC, WriterABC
from bioetl.output.impl.csv_writer import CsvWriterImpl
from bioetl.output.impl.metadata_writer import MetadataWriterImpl


def default_writer() -> WriterABC:
    return CsvWriterImpl()


def default_metadata_writer() -> MetadataWriterABC:
    return MetadataWriterImpl()

