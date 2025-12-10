"""Domain ports (hexagonal architecture boundaries)."""

from bioetl.domain.ports.extraction import (
    BatchAdapterABC,
    ExtractionServiceABC,
    RawRecordBatch,
    RawRecordDict,
    RecordFetcherABC,
    VersionProviderABC,
    from_raw_records,
    to_raw_records,
)
from bioetl.domain.ports.parsing import (
    PaginationInfo,
    RawPayload,
    RawRecordList,
    ResponseParserPortABC,
)

__all__: list[str] = [
    # Extraction ports
    "BatchAdapterABC",
    "ExtractionServiceABC",
    "RawRecordBatch",
    "RawRecordDict",
    "RecordFetcherABC",
    "VersionProviderABC",
    # Backward compatibility helpers
    "from_raw_records",
    "to_raw_records",
    # Parsing ports
    "PaginationInfo",
    "RawPayload",
    "RawRecordList",
    "ResponseParserPortABC",
]
