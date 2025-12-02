import pytest
from bioetl.infrastructure.output.factories import default_writer, default_metadata_writer
from bioetl.infrastructure.output.impl.csv_writer import CsvWriterImpl
from bioetl.infrastructure.output.impl.metadata_writer import MetadataWriterImpl

def test_default_writer():
    writer = default_writer()
    assert isinstance(writer, CsvWriterImpl)

def test_default_metadata_writer():
    writer = default_metadata_writer()
    assert isinstance(writer, MetadataWriterImpl)
