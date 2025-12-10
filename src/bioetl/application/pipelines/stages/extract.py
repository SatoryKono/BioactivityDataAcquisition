"""Extract stage with optional record mapping support."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from bioetl.application.mappers.contracts import RecordMapperABC
from bioetl.domain.ports.extraction import ExtractionServiceABC


class ExtractStage:
    """Extract stage with optional record mapping.

    This stage wraps an ExtractionServiceABC and optionally validates
    records through a RecordMapperABC before converting to DataFrames.

    When a mapper is provided, records are validated against domain models
    before conversion, ensuring data quality. When no mapper is provided,
    raw dicts are converted directly to DataFrame without validation.

    Example:
        >>> from bioetl.application.mappers.chembl import ChemblRecordMapper
        >>> stage = ExtractStage(extraction_service, ChemblRecordMapper())
        >>> for df in stage.extract("activity", target_chembl_id="CHEMBL25"):
        ...     process(df)
    """

    def __init__(
        self,
        extraction_service: ExtractionServiceABC,
        record_mapper: RecordMapperABC | None = None,
    ) -> None:
        """Initialize extract stage.

        Args:
            extraction_service: Service for fetching raw records.
            record_mapper: Optional mapper for domain model validation.
        """
        self._extraction_service = extraction_service
        self._mapper = record_mapper

    @property
    def extraction_service(self) -> ExtractionServiceABC:
        """Get the underlying extraction service."""
        return self._extraction_service

    @property
    def record_mapper(self) -> RecordMapperABC | None:
        """Get the record mapper if configured."""
        return self._mapper

    def extract(
        self,
        entity: str,
        *,
        chunk_size: int | None = None,
        **filters: object,
    ) -> Iterable[pd.DataFrame]:
        """Extract and optionally map records to DataFrames.

        If mapper is provided, records are validated against domain models
        before conversion. Otherwise, raw dicts are converted directly.

        Args:
            entity: Entity type to extract (e.g., 'activity', 'molecule').
            chunk_size: Optional batch size for pagination.
            **filters: Additional filters to apply during extraction.

        Yields:
            DataFrames containing extracted records.

        Raises:
            ValueError: If entity type is unknown to mapper.
            ValidationError: If record validation fails (when mapper is used).
        """
        for batch in self._extraction_service.iter_extract(
            entity, chunk_size=chunk_size, **filters
        ):
            if not batch:
                continue

            if self._mapper:
                # Map to domain models first (validates structure)
                typed_records = self._mapper.map_records(batch, entity)
                df = pd.DataFrame([r.model_dump() for r in typed_records])
            else:
                # Direct conversion (no validation)
                df = pd.DataFrame(batch)

            yield df

    def extract_all(
        self,
        entity: str,
        **filters: object,
    ) -> pd.DataFrame:
        """Extract all records as a single DataFrame.

        Convenience method that collects all batches into one DataFrame.

        Args:
            entity: Entity type to extract.
            **filters: Additional filters to apply.

        Returns:
            DataFrame containing all extracted records.
        """
        all_records = self._extraction_service.extract_all(entity, **filters)

        if not all_records:
            return pd.DataFrame()

        if self._mapper:
            typed_records = self._mapper.map_records(all_records, entity)
            return pd.DataFrame([r.model_dump() for r in typed_records])

        return pd.DataFrame(all_records)


__all__ = ["ExtractStage"]
