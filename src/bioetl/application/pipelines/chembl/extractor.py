"""
ChEMBL data extractor implementation.
"""

from typing import Any, Iterable

import pandas as pd
from pydantic import BaseModel

from bioetl.domain.configs import PipelineConfig
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.pipelines.contracts import ExtractorABC
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.record_source import RecordSourceABC
from bioetl.domain.transform.contracts import NormalizationServiceABC


class ChemblExtractorImpl(ExtractorABC):
    """
    Extracts data from ChEMBL source (API or File) and applies normalization.

    Record source is injected via constructor and created by RecordSourceFactory.
    """

    def __init__(
        self,
        config: PipelineConfig,
        extraction_service: ExtractionServiceABC,
        normalization_service: NormalizationServiceABC,
        logger: LoggingPortABC,
        record_source: RecordSourceABC,
    ) -> None:
        self.config = config
        self.extraction_service = extraction_service
        self.normalization_service = normalization_service
        self.logger = logger
        self.record_source = record_source

    def extract(self, **kwargs: Any) -> Iterable[pd.DataFrame]:
        """
        Yields chunks of normalized data.
        """
        limit = kwargs.pop("limit", None)
        remaining = limit

        for raw_chunk in self.record_source.iter_records():
            if remaining is not None and remaining <= 0:
                break

            chunk_records = raw_chunk
            if remaining is not None:
                chunk_records = raw_chunk[:remaining]

            normalized_input = [
                record.model_dump() if isinstance(record, BaseModel) else record
                for record in chunk_records
            ]

            working_chunk = pd.DataFrame(normalized_input)

            normalized_chunk = self.normalization_service.normalize(working_chunk)

            if not normalized_chunk.empty:
                yield normalized_chunk

            if remaining is not None:
                remaining -= len(chunk_records)
                if remaining <= 0:
                    break
