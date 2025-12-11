"""Extract stage with optional record mapping support."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast

import pandas as pd

from bioetl.application.mappers.contracts import RecordMapperABC
from bioetl.domain.data import TabularData
from bioetl.domain.pipelines.contracts import ExtractorABC
from bioetl.domain.ports.extraction import ExtractionServiceABC


class ExtractStage(ExtractorABC):
    """Extract stage with optional record mapping.

    This stage wraps an ExtractionServiceABC and optionally validates
    records through a RecordMapperABC before converting to DataFrames.

    When a mapper is provided, records are validated against domain models
    before conversion, ensuring data quality. When no mapper is provided,
    raw dicts are converted directly to DataFrame without validation.

    Supports pre-configured entity for pipeline integration where the
    entity is determined by configuration rather than at extraction time.

    Example:
        >>> from bioetl.application.mappers.chembl import ChemblRecordMapper
        >>> stage = ExtractStage(extraction_service, ChemblRecordMapper())
        >>> for df in stage.extract("activity", target_chembl_id="CHEMBL25"):
        ...     process(df)

        # Pre-configured entity for pipeline use:
        >>> stage = ExtractStage(extraction_service, ChemblRecordMapper(), entity="activity")
        >>> for df in stage.extract():  # Uses pre-configured entity
        ...     process(df)
    """

    def __init__(
        self,
        extraction_service: ExtractionServiceABC,
        record_mapper: RecordMapperABC | None = None,
        entity: str | None = None,
    ) -> None:
        """Initialize extract stage.

        Args:
            extraction_service: Service for fetching raw records.
            record_mapper: Optional mapper for domain model validation.
            entity: Optional pre-configured entity type. When provided,
                extract() can be called without entity argument.
        """
        self._extraction_service = extraction_service
        self._mapper = record_mapper
        self._entity = entity

    @property
    def extraction_service(self) -> ExtractionServiceABC:
        """Get the underlying extraction service."""
        return self._extraction_service

    @property
    def record_mapper(self) -> RecordMapperABC | None:
        """Get the record mapper if configured."""
        return self._mapper

    @property
    def entity(self) -> str | None:
        """Get the pre-configured entity if set."""
        return self._entity

    def extract(
        self,
        entity: str | None = None,
        *,
        chunk_size: int | None = None,
        **filters: Any,
    ) -> Iterable[TabularData]:
        """Extract and optionally map records to DataFrames.

        If mapper is provided, records are validated against domain models
        before conversion. Otherwise, raw dicts are converted directly.

        Args:
            entity: Entity type to extract (e.g., 'activity', 'molecule').
                If not provided, uses the pre-configured entity from constructor.
            chunk_size: Optional batch size for pagination.
            **filters: Additional filters to apply during extraction.
                Supports 'limit' to restrict total record count.

        Yields:
            DataFrames containing extracted records.

        Raises:
            ValueError: If entity type is unknown to mapper or not configured.
            ValidationError: If record validation fails (when mapper is used).
        """
        resolved_entity = entity or self._entity
        if resolved_entity is None:
            raise ValueError(
                "Entity must be provided either to extract() or in constructor."
            )

        # Extract limit from filters for manual limiting
        limit = filters.pop("limit", None)
        remaining = limit

        for batch in self._extraction_service.iter_extract(
            resolved_entity, chunk_size=chunk_size, **filters
        ):
            if remaining is not None and remaining <= 0:
                break

            # Check if batch is empty (works for both list and DataFrame)
            if isinstance(batch, pd.DataFrame):
                if batch.empty:
                    continue
            elif not batch:
                continue

            # Apply limit to batch if needed
            batch_records = batch
            if remaining is not None:
                batch_records = batch[:remaining]

            if self._mapper:
                # Map to domain models first (validates structure)
                typed_records = self._mapper.map_records(batch_records, resolved_entity)
                df = pd.DataFrame([r.model_dump() for r in typed_records])
            else:
                # Direct conversion (no validation)
                df = pd.DataFrame(batch_records)

            if not df.empty:
                yield cast(TabularData, df)

            if remaining is not None:
                remaining -= len(batch_records)
                if remaining <= 0:
                    break

    def extract_all(
        self,
        entity: str | None = None,
        **filters: Any,
    ) -> pd.DataFrame:
        """Extract all records as a single DataFrame.

        Convenience method that collects all batches into one DataFrame.

        Args:
            entity: Entity type to extract.
                If not provided, uses the pre-configured entity from constructor.
            **filters: Additional filters to apply.

        Returns:
            DataFrame containing all extracted records.

        Raises:
            ValueError: If entity is not provided and not pre-configured.
        """
        resolved_entity = entity or self._entity
        if resolved_entity is None:
            raise ValueError(
                "Entity must be provided either to extract_all() or in constructor."
            )

        all_records = self._extraction_service.extract_all(resolved_entity, **filters)

        if not all_records:
            return pd.DataFrame()

        if self._mapper:
            typed_records = self._mapper.map_records(all_records, resolved_entity)
            return pd.DataFrame([r.model_dump() for r in typed_records])

        return pd.DataFrame(all_records)


__all__ = ["ExtractStage"]
