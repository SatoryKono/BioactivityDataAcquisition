# mypy: disable-error-code=no-any-return
"""Feature and sequence fetch methods for UniProtAdapter."""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING, Any

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.uniprot.fasta_parser import FastaParser

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


_UNIPROT_FEATURE_SEQUENCE_ERRORS = (Exception,)


class UniProtFeatureSequenceAdapterMixin:
    """Feature/sequence endpoint helpers."""

    async def _get_features_json(self: Any, query: str) -> list[BronzeRecord]:
        """Retrieve feature payload from UniProt JSON endpoint."""
        try:
            start_time = time.perf_counter()
            with self._adapter_metrics.measure_request("/uniprotkb/features"):
                response = await self.http_client.get(
                    f"{self.base_url}/uniprotkb/{query}.json"
                )
            duration_ms = (time.perf_counter() - start_time) * 1000
            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)
            if response.status_code == 200:
                features: list[BronzeRecord] = response.json().get("features", [])
                return features
            return []
        except _UNIPROT_FEATURE_SEQUENCE_ERRORS as error:
            self._handle_fetch_error("feature", query, error=error)
            return []

    async def _fetch_features(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch protein features."""
        if not query:
            raise ValueError("Query is required for feature search")

        features = await self._get_features_json(query)
        for index, feature in enumerate(features):
            if limit and index >= limit:
                break
            yield self._format_feature(query, feature)

    def _format_feature(self: Any, query: str, feature: BronzeRecord) -> BronzeRecord:
        """Normalize feature payload to record contract."""
        return {
            "accession": query,
            "type": feature.get("type"),
            "location": feature.get("location"),
            "description": feature.get("description"),
        }

    async def _get_sequence_fasta(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        query: str,  # Any: mixin self type is provided structurally by composed adapter class
    ) -> (
        str | None
    ):  # Any: mixin self type is provided structurally by composed adapter class
        """Retrieve FASTA sequence text."""
        try:
            start_time = time.perf_counter()
            with self._adapter_metrics.measure_request("/uniprotkb/stream"):
                response = await self.http_client.get(
                    f"{self.base_url}/uniprotkb/stream",
                    params={"query": query, "format": "fasta"},
                )
            duration_ms = (time.perf_counter() - start_time) * 1000
            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)
            if response.status_code == 200:
                return response.text
            return None
        except _UNIPROT_FEATURE_SEQUENCE_ERRORS as error:
            self._handle_fetch_error("sequence", query, error=error)
            return None

    async def _get_parsed_sequences(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        query: str,  # Any: mixin self type is provided structurally by composed adapter class
    ) -> AsyncIterator[BronzeRecord]:
        """Parse FASTA into sequence records."""
        fasta_text = await self._get_sequence_fasta(query)
        if fasta_text:
            loop = asyncio.get_running_loop()
            records = await loop.run_in_executor(None, FastaParser.parse, fasta_text)
            for record in records:
                yield record

    async def _fetch_sequences(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        query: str | None,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch sequence records."""
        if not query:
            raise ValueError("Query is required for sequence fetch")

        fetched = 0
        async for seq_record in self._get_parsed_sequences(query):
            if limit and fetched >= limit:
                break
            yield seq_record
            fetched += 1
