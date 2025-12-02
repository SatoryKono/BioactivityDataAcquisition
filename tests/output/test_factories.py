import pytest
from bioetl.output.factories import default_writer, default_metadata_writer
from bioetl.output.impl.csv_writer import CsvWriterImpl
from bioetl.output.impl.metadata_writer import MetadataWriterImpl

def test_default_writer():
    writer = default_writer()
    assert isinstance(writer, CsvWriterImpl)

def test_default_metadata_writer():
    writer = default_metadata_writer()
    assert isinstance(writer, MetadataWriterImpl)
