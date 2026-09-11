# mypy: disable-error-code=attr-defined
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Feature/sequence fetch and metadata helpers for UniProtAdapter."""

from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.mixin_host import as_mixin_host
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.common.source_metadata_capability import (
    clear_source_metadata_collector,
    consume_source_metadata,
    get_request_count,
)
from bioetl.infrastructure.adapters.uniprot.fasta_parser import FastaParser

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.models.metadata import SourceMetadata

_UNIPROT_FEATURE_SEQUENCE_ERRORS = (Exception,)


class UniProtFeatureSequenceAdapterMixin:
    """Feature/sequence endpoint helpers."""

    async def _get_features_json(self, query: str) -> list[BronzeRecord]:
        """Retrieve feature payload from UniProt JSON endpoint.

        Returns:
            List of feature record dicts from the UniProt entry, empty list on error.
        """
        try:
            start_time = time.perf_counter()
            with as_mixin_host(self)._adapter_metrics.measure_request(
                "/uniprotkb/features"
            ):  # Any: mixin host
                response = await as_mixin_host(
                    self
                )._http_client.get(  # Any: mixin host
                    f"{as_mixin_host(self).base_url}/uniprotkb/{query}.json"  # Any: mixin host
                )
            typed_response = cast("object", response)
            duration_ms = (time.perf_counter() - start_time) * 1000
            with contextlib.suppress(Exception):
                as_mixin_host(
                    self
                )._request_collector.record_from_response(  # Any: mixin host
                    typed_response, duration_ms
                )
            if getattr(typed_response, "status_code", None) == 200:
                json_fn = getattr(typed_response, "json", None)
                payload = json_fn() if callable(json_fn) else {}
                if isinstance(payload, dict):
                    raw_features = payload.get("features")
                    if isinstance(raw_features, list):
                        return [item for item in raw_features if isinstance(item, dict)]
            return []
        except _UNIPROT_FEATURE_SEQUENCE_ERRORS as error:
            as_mixin_host(self)._handle_fetch_error(
                "feature", query, error=error
            )  # Any: mixin host
            return []

    async def _fetch_features(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch protein features."""
        if not query:
            raise ValueError("Query is required for feature search")

        features = await as_mixin_host(self)._get_features_json(
            query
        )  # Any: mixin host
        for index, feature in enumerate(features):
            if limit and index >= limit:
                break
            yield as_mixin_host(self)._format_feature(query, feature)  # Any: mixin host

    def _format_feature(self, query: str, feature: BronzeRecord) -> BronzeRecord:
        """Normalize feature payload to record contract.

        Returns:
            Dictionary with accession, type, location, and description keys.
        """
        return {
            "accession": query,
            "type": feature.get("type"),
            "location": feature.get("location"),
            "description": feature.get("description"),
        }

    async def _get_sequence_fasta(
        self,
        query: str,
    ) -> str | None:
        """Retrieve FASTA sequence text.

        Returns:
            FASTA format text string if request succeeds, None on error or non-200 response.
        """
        try:
            start_time = time.perf_counter()
            with as_mixin_host(self)._adapter_metrics.measure_request(
                "/uniprotkb/stream"
            ):  # Any: mixin host
                response = await as_mixin_host(
                    self
                )._http_client.get(  # Any: mixin host
                    f"{as_mixin_host(self).base_url}/uniprotkb/stream",  # Any: mixin host
                    params={"query": query, "format": "fasta"},
                )
            typed_response = cast("object", response)
            duration_ms = (time.perf_counter() - start_time) * 1000
            with contextlib.suppress(Exception):
                as_mixin_host(
                    self
                )._request_collector.record_from_response(  # Any: mixin host
                    typed_response, duration_ms
                )
            if getattr(typed_response, "status_code", None) == 200:
                text = getattr(typed_response, "text", None)
                return text if isinstance(text, str) else None
            return None
        except _UNIPROT_FEATURE_SEQUENCE_ERRORS as error:
            as_mixin_host(self)._handle_fetch_error(
                "sequence", query, error=error
            )  # Any: mixin host
            return None

    async def _get_parsed_sequences(
        self,
        query: str,
    ) -> AsyncIterator[BronzeRecord]:
        """Parse FASTA into sequence records."""
        fasta_text = await as_mixin_host(self)._get_sequence_fasta(
            query
        )  # Any: mixin host
        if fasta_text:
            records = FastaParser.parse(fasta_text)
            for record in records:
                yield record

    async def _fetch_sequences(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch sequence records."""
        if not query:
            raise ValueError("Query is required for sequence fetch")

        fetched = 0
        async for seq_record in as_mixin_host(self)._get_parsed_sequences(
            query
        ):  # Any: mixin host
            if limit and fetched >= limit:
                break
            yield seq_record
            fetched += 1


class UniProtAdapterMetadataMixin:
    """Adds request-metadata and repr helpers to UniProt adapter."""

    # Host-class attributes (provided by UniProtAdapter.__init__)
    api_key: str | None = cast(Any, None)  # Any: host attr default (PD6)
    base_url: str = cast(Any, None)  # Any: host attr default (PD6)
    _request_collector: APIRequestCollector = cast(
        Any, None
    )  # Any: host attr default (PD6)

    def _get_health_endpoint(self) -> str:
        """Return health check endpoint.

        Returns:
            Endpoint path string used for UniProt health probe requests.
        """
        return "/uniprotkb/search"

    def __repr__(self) -> str:
        key_info = "with API key" if self.api_key else "without API key"
        return f"UniProtAdapter(base_url='{self.base_url}', {key_info})"

    def get_source_metadata(
        self,
        api_version: str | None = None,
    ) -> SourceMetadata:
        """Get API request metadata and clear collector.

        Returns:
            SourceMetadata aggregated from all recorded API requests since last clear.
        """
        return consume_source_metadata(
            collector=self._request_collector,
            url=self.base_url,
            api_version=api_version,
        )

    def clear_request_collector(self) -> None:
        """Clear the request collector without returning metadata."""
        clear_source_metadata_collector(collector=self._request_collector)

    @property
    def request_count(self) -> int:
        """Number of recorded API requests since last clear."""
        return get_request_count(collector=self._request_collector)


__all__ = ["UniProtAdapterMetadataMixin", "UniProtFeatureSequenceAdapterMixin"]
