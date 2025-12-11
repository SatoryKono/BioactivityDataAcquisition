from bioetl.infrastructure.output.factories import (
    create_writer,
    default_metadata_writer,
)
from bioetl.infrastructure.output.impl.csv_writer import CsvWriter
from bioetl.infrastructure.output.impl.metadata_writer import MetadataWriter


def test_default_writer():
    writer = create_writer()
    assert isinstance(writer, CsvWriter)


def test_default_metadata_writer():
    writer = default_metadata_writer()
    assert isinstance(writer, MetadataWriter)
