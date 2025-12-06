"""
ChEMBL data extractor implementation.
"""

from typing import Any, Iterable

import pandas as pd

from bioetl.application.pipelines.contracts import ExtractorABC
from bioetl.domain.clients.base.logging.contracts import LoggerAdapterABC
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.record_source import ApiRecordSource, RecordSource
from bioetl.domain.transform.contracts import NormalizationServiceABC


class ChemblExtractorImpl(ExtractorABC):
    """
    Extracts data from ChEMBL source (API or File) and applies normalization.
    """

    def __init__(
        self,
        config: PipelineConfig,
        extraction_service: ExtractionServiceABC,
        normalization_service: NormalizationServiceABC,
        logger: LoggerAdapterABC,
        record_source: RecordSource | None = None,
    ) -> None:
        self.config = config
        self.extraction_service = extraction_service
        self.normalization_service = normalization_service
        self.logger = logger
        self.record_source = record_source or ApiRecordSource(
            extraction_service=extraction_service,
            entity=config.entity_name,
            filters=config.pipeline,
        )

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

            working_chunk = pd.DataFrame(chunk_records)

            normalized_chunk = self.normalization_service.normalize_batch(working_chunk)

            if not normalized_chunk.empty:
                yield normalized_chunk

            if remaining is not None:
                remaining -= len(chunk_records)
                if remaining <= 0:
                    break
