from bioetl.infrastructure.config.models import DeterminismConfig
from bioetl.infrastructure.output.adapters import UnifiedOutputServiceAdapter
from bioetl.infrastructure.output.contracts import (
    MetadataWriterABC,
    OutputServiceABC,
    WriterABC,
)
from bioetl.infrastructure.output.impl.csv_writer import CsvWriterImpl
from bioetl.infrastructure.output.impl.metadata_writer import MetadataWriterImpl
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


def default_writer() -> WriterABC:
    return CsvWriterImpl()


def default_metadata_writer() -> MetadataWriterABC:
    return MetadataWriterImpl()


def default_output_service(config: DeterminismConfig) -> OutputServiceABC:
    """Фабрика фасада записи результатов."""
    unified_writer = UnifiedOutputWriter(
        writer=default_writer(),
        metadata_writer=default_metadata_writer(),
        config=config,
    )
    return UnifiedOutputServiceAdapter(unified_writer)

