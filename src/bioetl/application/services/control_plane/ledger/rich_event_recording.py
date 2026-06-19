"""Rich ledger event recording mixin kept separate from core lifecycle service."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import bioetl.application.services.control_plane.ledger.rich_events as _rich_events
from bioetl.domain.control_plane import RunLedgerEntry


class _RunLedgerRichEventAppender(Protocol):
    def _append(
        self,
        *,
        event_type: str,
        status: str | None,
        stage: str | None = None,
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry: ...


class RunLedgerRichEventRecordingMixin:
    """Bounded rich-event wrappers kept out of the core lifecycle hotspot."""

    def record_composite_dependency_completed(
        self: _RunLedgerRichEventAppender,
        *,
        dependency_name: str,
        result: Mapping[str, object],
    ) -> RunLedgerEntry:
        """Record bounded dependency result evidence for rich composite replay."""
        return _rich_events.record_composite_dependency_completed(
            self,
            dependency_name=dependency_name,
            result=result,
        )

    def record_composite_enricher_completed(
        self: _RunLedgerRichEventAppender,
        *,
        enricher_name: str,
        result: Mapping[str, object],
    ) -> RunLedgerEntry:
        """Record bounded enricher result evidence for rich composite replay."""
        return _rich_events.record_composite_enricher_completed(
            self,
            enricher_name=enricher_name,
            result=result,
        )

    def record_composite_merge_completed(
        self: _RunLedgerRichEventAppender,
        *,
        result: Mapping[str, object],
    ) -> RunLedgerEntry:
        """Record bounded merge result evidence for rich composite replay."""
        return _rich_events.record_composite_merge_completed(
            self,
            result=result,
        )

    def record_input_snapshot_published(
        self: _RunLedgerRichEventAppender,
        *,
        provider: str,
        entity: str,
        pipeline_name: str,
        snapshot_id: str,
        content_hash: str,
        immutable_uri: str,
        bronze_batch_ref: str,
        query_fingerprint: str | None = None,
        details: Mapping[str, object] | None = None,
    ) -> RunLedgerEntry:
        """Record immutable input snapshot evidence published after Bronze write."""
        return _rich_events.record_input_snapshot_published(
            self,
            provider=provider,
            entity=entity,
            pipeline_name=pipeline_name,
            snapshot_id=snapshot_id,
            content_hash=content_hash,
            immutable_uri=immutable_uri,
            bronze_batch_ref=bronze_batch_ref,
            query_fingerprint=query_fingerprint,
            details=details,
        )
