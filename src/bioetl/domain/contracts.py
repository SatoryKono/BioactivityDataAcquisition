"""
Domain contracts (ABCs) for extraction services.

These interfaces define the contract that extraction services must implement,
allowing application layer to depend on abstractions rather than concrete
implementations.
"""
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

import pandas as pd


class ExtractionServiceABC(ABC):
    """
    Abstract base class for data extraction services.

    Defines the contract for services that extract data from external sources
    and return it as DataFrames.
    """

    @abstractmethod
    def get_release_version(self) -> str:
        """
        Get the version/release identifier of the data source.

        Returns:
            String identifier (e.g., 'chembl_34', 'v2.1.0')
        """

    @abstractmethod
    def extract_all(self, entity: str, **filters: Any) -> pd.DataFrame:
        """
        Extract all records for an entity with optional filters.

        Args:
            entity: Entity name to extract (e.g., 'activity', 'assay')
            **filters: Provider-specific filters (e.g., limit, offset)

        Returns:
            DataFrame containing extracted records
        """

    @abstractmethod
    def iter_extract(
        self, entity: str, *, chunk_size: int | None = None, **filters: Any
    ) -> Iterable[pd.DataFrame]:
        """
        Stream records for an entity in DataFrame chunks.

        Args:
            entity: Entity name to extract (e.g., 'activity', 'assay')
            chunk_size: Preferred chunk size for each page/batch
            **filters: Provider-specific filters (e.g., limit, offset)

        Returns:
            Iterable of DataFrames with extracted records
        """

    @abstractmethod
    def request_batch(
        self,
        entity: str,
        batch_ids: list[str],
        filter_key: str,
    ) -> dict[str, Any]:
        """
        Request a batch of records by IDs.

        Args:
            entity: Entity name
            batch_ids: List of IDs to fetch
            filter_key: API filter key (e.g., 'activity_id__in')

        Returns:
            Raw API response dict
        """

    @abstractmethod
    def parse_response(
        self, raw_response: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Parse raw API response into list of records.

        Args:
            raw_response: Raw response from API

        Returns:
            List of record dictionaries
        """

    @abstractmethod
    def serialize_records(
        self, entity: str, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Serialize records (flattening, type conversion) before DataFrame creation.

        Args:
            entity: Entity name
            records: List of raw records

        Returns:
            List of serialized records
        """