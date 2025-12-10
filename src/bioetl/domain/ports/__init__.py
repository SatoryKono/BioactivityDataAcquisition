"""Domain ports (hexagonal architecture boundaries)."""

from bioetl.domain.ports.parsing import (
    PaginationInfo,
    RawPayload,
    RawRecordDict,
    RawRecordList,
    ResponseParserPortABC,
)

__all__: list[str] = [
    "PaginationInfo",
    "RawPayload",
    "RawRecordDict",
    "RawRecordList",
    "ResponseParserPortABC",
]
