"""Output writer contracts re-export."""

from bioetl.domain.clients.base.output.contracts import (
    MetadataWriterABC,
    QualityReportABC,
    WriterABC,
    WriteResult,
)

__all__ = [
    "WriteResult",
    "WriterABC",
    "MetadataWriterABC",
    "QualityReportABC",
]
