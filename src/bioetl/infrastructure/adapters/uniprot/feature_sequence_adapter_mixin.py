# mypy: disable-error-code=attr-defined
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Feature and sequence fetch methods for UniProtAdapter."""

from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING, cast, Any, Protocol

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.uniprot.fasta_parser import FastaParser
from bioetl.domain.mixin_host import as_mixin_host

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

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
            with as_mixin_host(self)._adapter_metrics.measure_request("/uniprotkb/features"):  # Any: mixin host surface (self attrs/methods)
                response = await as_mixin_host(self)._http_client.get(  # Any: mixin host surface (self attrs/methods)
                    f"{as_mixin_host(self).base_url}/uniprotkb/{query}.json"  # Any: mixin host surface (self attrs/methods)
                )
            typed_response = cast("object", response)
            duration_ms = (time.perf_counter() - start_time) * 1000
            with contextlib.suppress(Exception):
                as_mixin_host(self)._request_collector.record_from_response(  # Any: mixin host surface (self attrs/methods)
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
            as_mixin_host(self)._handle_fetch_error("feature", query, error=error)  # Any: mixin host surface (self attrs/methods)
            return []

    async def _fetch_features(
        self,
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch protein features."""
        if not query:
            raise ValueError("Query is required for feature search")

        features = await as_mixin_host(self)._get_features_json(query)  # Any: mixin host surface (self attrs/methods)
        for index, feature in enumerate(features):
            if limit and index >= limit:
                break
            yield as_mixin_host(self)._format_feature(query, feature)  # Any: mixin host surface (self attrs/methods)

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
            with as_mixin_host(self)._adapter_metrics.measure_request("/uniprotkb/stream"):  # Any: mixin host surface (self attrs/methods)
                response = await as_mixin_host(self)._http_client.get(  # Any: mixin host surface (self attrs/methods)
                    f"{as_mixin_host(self).base_url}/uniprotkb/stream",  # Any: mixin host surface (self attrs/methods)
                    params={"query": query, "format": "fasta"},
                )
            typed_response = cast("object", response)
            duration_ms = (time.perf_counter() - start_time) * 1000
            with contextlib.suppress(Exception):
                as_mixin_host(self)._request_collector.record_from_response(  # Any: mixin host surface (self attrs/methods)
                    typed_response, duration_ms
                )
            if getattr(typed_response, "status_code", None) == 200:
                text = getattr(typed_response, "text", None)
                return text if isinstance(text, str) else None
            return None
        except _UNIPROT_FEATURE_SEQUENCE_ERRORS as error:
            as_mixin_host(self)._handle_fetch_error("sequence", query, error=error)  # Any: mixin host surface (self attrs/methods)
            return None

    async def _get_parsed_sequences(
        self,
        query: str,
    ) -> AsyncIterator[BronzeRecord]:
        """Parse FASTA into sequence records."""
        fasta_text = await as_mixin_host(self)._get_sequence_fasta(query)  # Any: mixin host surface (self attrs/methods)
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
        async for seq_record in as_mixin_host(self)._get_parsed_sequences(query):  # Any: mixin host surface (self attrs/methods)
            if limit and fetched >= limit:
                break
            yield seq_record
            fetched += 1
