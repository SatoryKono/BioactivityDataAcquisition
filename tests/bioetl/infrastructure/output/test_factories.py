from bioetl.infrastructure.output.factories import (
    create_metadata_writer,
    create_writer,
)
from bioetl.infrastructure.output.impl.csv_writer import CsvWriter
from bioetl.infrastructure.output.impl.metadata_writer import MetadataWriter


def test_create_writer():
    writer = create_writer()
    assert isinstance(writer, CsvWriter)


def test_create_metadata_writer():
    writer = create_metadata_writer()
    assert isinstance(writer, MetadataWriter)
