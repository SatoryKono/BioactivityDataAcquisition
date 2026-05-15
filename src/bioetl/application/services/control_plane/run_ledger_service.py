"""Application service for append-only run-ledger events."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from bioetl.application.services.control_plane._run_ledger_entry_support import (
    RunLedgerEntryRequest,
    append_run_ledger_entry,
    append_run_outcome,
)
from bioetl.application.services.control_plane import _run_ledger_rich_events
from bioetl.application.services.control_plane._run_ledger_diagnostic_support import (
    sync_manifest_contract_defaults,
    sync_manifest_runtime_defaults,
)
from bioetl.domain.context import current_utc_time
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.control_plane.run_ledger import (
    ARTIFACT_PUBLISHED_EVENT,
    DQ_POLICY_APPLIED_EVENT,
    MANIFEST_CREATED_EVENT,
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_SHUTDOWN_EVENT,
    RUN_STARTED_EVENT,
    STAGE_COMPLETED_EVENT,
    STAGE_STARTED_EVENT,
    canonicalize_run_ledger_stage_name,
)
from bioetl.domain.ports import RunLedgerPort
from bioetl.domain.types import RunID
from bioetl.domain.types.dq_contracts import DQDisposition

__all__ = ["RunLedgerService"]


@dataclass(slots=True)
class RunLedgerService:
    """Append immutable control-plane lifecycle entries for one manifest."""

    ledger_port: RunLedgerPort
    manifest_id: str
    run_id: RunID
    pipeline_name: str | None = None
    provider: str | None = None
    entity: str | None = None
    run_type: str | None = None
    resolved_config_hash: str | None = None
    effective_config_hash: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    dq_policy_ref: str | None = None
    rule_bundle_version: str | None = None
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None
    composite_run_id: str | None = None
    _entry_id_factory: Callable[[], str] = field(
        default_factory=lambda: lambda: str(uuid4())
    )
    _occurred_at_factory: Callable[[], datetime] = current_utc_time

    def record_manifest_created(self, manifest: RunManifest) -> RunLedgerEntry:
        """Record manifest creation as the first control-plane event."""
        if self.manifest_id != manifest.manifest_id:
            raise ValueError(
                "RunLedgerService manifest_id must match the persisted manifest before recording ledger events"
            )
        if self.run_id != manifest.run_id:
            raise ValueError(
                "RunLedgerService run_id must match the persisted manifest before recording ledger events"
            )
        # Keep the first event diagnostics stable around runtime anchors.
        sync_manifest_runtime_defaults(self, manifest)
        entry = self._append(
            event_type=MANIFEST_CREATED_EVENT,
            status="created",
            details={
                "execution_fingerprint": manifest.execution_fingerprint,
                "pipeline_name": manifest.pipeline_name,
                "provider": manifest.provider,
                "entity": manifest.entity,
            },
        )
        # Contract/DQ anchors are still needed for subsequent lifecycle events.
        sync_manifest_contract_defaults(self, manifest)
        return entry

    def record_run_started(self) -> RunLedgerEntry:
        """Record the transition into active execution."""
        return self._append(event_type=RUN_STARTED_EVENT, status="running")

    def record_stage_started(
        self,
        *,
        stage: str,
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry:
        """Record transition into one canonical execution stage."""
        return self._append(
            event_type=STAGE_STARTED_EVENT,
            status="running",
            stage=canonicalize_run_ledger_stage_name(stage),
            details=details,
        )

    def record_stage_completed(
        self,
        *,
        stage: str,
        metrics_snapshot: dict[str, int],
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry:
        """Record successful completion of one execution stage."""
        return self._append(
            event_type=STAGE_COMPLETED_EVENT,
            status="completed",
            stage=canonicalize_run_ledger_stage_name(stage),
            metrics_snapshot=metrics_snapshot,
            details=details,
        )

    def record_run_finished(
        self,
        *,
        metrics_snapshot: dict[str, int],
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry:
        """Record successful run completion."""
        return append_run_outcome(
            self,
            event_type=RUN_FINISHED_EVENT,
            status="success",
            metrics_snapshot=metrics_snapshot,
            details=details,
        )

    def record_run_failed(
        self,
        *,
        message: str,
        error_type: str | None,
        metrics_snapshot: dict[str, int],
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry:
        """Record failed run completion."""
        return append_run_outcome(
            self,
            event_type=RUN_FAILED_EVENT,
            status="failed",
            metrics_snapshot=metrics_snapshot,
            message=message,
            error_type=error_type,
            details=details,
        )

    def record_run_exception(
        self,
        *,
        error: Exception,
        metrics_snapshot: dict[str, int],
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry:
        """Record failed run completion directly from an exception instance."""
        return self.record_run_failed(
            message=str(error),
            error_type=type(error).__name__,
            metrics_snapshot=metrics_snapshot,
            details=details,
        )

    def record_run_shutdown(
        self,
        *,
        metrics_snapshot: dict[str, int],
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry:
        """Record graceful shutdown completion."""
        return append_run_outcome(
            self,
            event_type=RUN_SHUTDOWN_EVENT,
            status="shutdown",
            metrics_snapshot=metrics_snapshot,
            details=details,
        )

    def record_artifact_published(
        self,
        *,
        layer: str,
        artifact_path: str,
        dataset_ref: str | None = None,
        lineage_fragment_id: str | None = None,
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry:
        """Record a published layer artifact tied to this manifest."""
        if dataset_ref is None and lineage_fragment_id is None:
            raise ValueError(
                "Artifact publication requires dataset_ref or lineage_fragment_id"
            )
        payload: dict[str, object] = {"artifact_path": artifact_path}
        if details:
            payload.update(details)
        return self._append(
            event_type=ARTIFACT_PUBLISHED_EVENT,
            status="published",
            stage=layer,
            dataset_ref=dataset_ref,
            lineage_fragment_id=lineage_fragment_id,
            details=payload,
        )

    def record_dq_policy_applied(
        self,
        *,
        stage: str,
        status: str = "failed",
        rule_id: str | None = None,
        disposition: DQDisposition | str | None = None,
        dq_report_path: str | None = None,
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry:
        """Record a DQ policy outcome with stable trace anchors."""
        payload: dict[str, object] = {}
        if rule_id is not None:
            payload["rule_id"] = rule_id
        if disposition is not None:
            payload["disposition"] = str(disposition)
        if dq_report_path is not None:
            payload["dq_report_path"] = dq_report_path
        if details:
            payload.update(details)
        return self._append(
            event_type=DQ_POLICY_APPLIED_EVENT,
            status=status,
            stage=stage,
            details=payload,
        )

    def record_composite_dependency_completed(
        self,
        *,
        dependency_name: str,
        result: Mapping[str, object],
    ) -> RunLedgerEntry:
        """Record bounded dependency result evidence for rich composite replay."""
        return _run_ledger_rich_events.record_composite_dependency_completed(
            self,
            dependency_name=dependency_name,
            result=result,
        )

    def record_composite_enricher_completed(
        self,
        *,
        enricher_name: str,
        result: Mapping[str, object],
    ) -> RunLedgerEntry:
        """Record bounded enricher result evidence for rich composite replay."""
        return _run_ledger_rich_events.record_composite_enricher_completed(
            self,
            enricher_name=enricher_name,
            result=result,
        )

    def record_composite_merge_completed(
        self,
        *,
        result: Mapping[str, object],
    ) -> RunLedgerEntry:
        """Record bounded merge result evidence for rich composite replay."""
        return _run_ledger_rich_events.record_composite_merge_completed(
            self,
            result=result,
        )

    def record_input_snapshot_published(
        self,
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
        return _run_ledger_rich_events.record_input_snapshot_published(
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

    def _append(
        self,
        *,
        event_type: str,
        status: str | None,
        stage: str | None = None,
        message: str | None = None,
        error_type: str | None = None,
        dataset_ref: str | None = None,
        lineage_fragment_id: str | None = None,
        metrics_snapshot: dict[str, int] | None = None,
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry:
        """Create and append one ledger entry."""
        return append_run_ledger_entry(
            self,
            RunLedgerEntryRequest(
                event_type=event_type,
                status=status,
                stage=stage,
                message=message,
                error_type=error_type,
                dataset_ref=dataset_ref,
                lineage_fragment_id=lineage_fragment_id,
                metrics_snapshot=metrics_snapshot,
                details=details,
            ),
        )
