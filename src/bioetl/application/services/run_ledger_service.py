"""Application service for append-only run-ledger events."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.control_plane.run_ledger import (
    canonicalize_run_ledger_stage_name,
    infer_ledger_event_family,
)
from bioetl.domain.events import PipelineEvent
from bioetl.domain.ports import RunLedgerPort
from bioetl.domain.types import RunID
from bioetl.domain.types.dq_contracts import DQDisposition

__all__ = ["RunLedgerService"]

_LEDGER_DETAILS_CONTRACT_VERSION = "v1"


def _coalesce_missing(current: str | None, default: str | None) -> str | None:
    """Return default only when current value is missing."""
    if current is None:
        return default
    return current


def _apply_optional_diagnostic_anchor(
    diagnostic: dict[str, object],
    field_name: str,
    value: str | None,
) -> None:
    """Attach one non-empty correlation anchor to diagnostic payload."""
    if value is None:
        return
    if not value.strip():
        return
    diagnostic[field_name] = value


def _sync_manifest_runtime_defaults(
    service: RunLedgerService,
    manifest: RunManifest,
) -> None:
    """Hydrate runtime correlation defaults from the immutable manifest."""
    code_provenance = manifest.code_provenance
    service.pipeline_name = _coalesce_missing(
        service.pipeline_name, manifest.pipeline_name
    )
    service.provider = _coalesce_missing(service.provider, manifest.provider)
    service.entity = _coalesce_missing(service.entity, manifest.entity)
    service.run_type = _coalesce_missing(service.run_type, manifest.run_type.value)
    service.effective_config_hash = _coalesce_missing(
        service.effective_config_hash,
        code_provenance.config_hash,
    )


def _sync_manifest_contract_defaults(
    service: RunLedgerService,
    manifest: RunManifest,
) -> None:
    """Hydrate contract/DQ correlation defaults from the immutable manifest."""
    code_provenance = manifest.code_provenance
    service.contract_ref = _coalesce_missing(
        service.contract_ref,
        code_provenance.contract_ref,
    )
    service.contract_version = _coalesce_missing(
        service.contract_version,
        code_provenance.contract_version,
    )
    service.dq_policy_ref = _coalesce_missing(
        service.dq_policy_ref,
        code_provenance.dq_policy_ref,
    )
    service.rule_bundle_version = _coalesce_missing(
        service.rule_bundle_version,
        code_provenance.rule_bundle_version,
    )
    service.dq_contract_compatibility_hash = _coalesce_missing(
        service.dq_contract_compatibility_hash,
        code_provenance.dq_contract_compatibility_hash,
    )
    service.effective_config_artifact_id = _coalesce_missing(
        service.effective_config_artifact_id,
        code_provenance.effective_config_artifact_id,
    )


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

    def record_manifest_created(self, manifest: RunManifest) -> RunLedgerEntry:
        """Record manifest creation as the first control-plane event."""
        # Keep the first event diagnostics stable around runtime anchors.
        _sync_manifest_runtime_defaults(self, manifest)
        entry = self._append(
            event_type="manifest_created",
            status="created",
            details={
                "execution_fingerprint": manifest.execution_fingerprint,
                "pipeline_name": manifest.pipeline_name,
                "provider": manifest.provider,
                "entity": manifest.entity,
            },
        )
        # Contract/DQ anchors are still needed for subsequent lifecycle events.
        _sync_manifest_contract_defaults(self, manifest)
        return entry

    def record_run_started(self) -> RunLedgerEntry:
        """Record the transition into active execution."""
        return self._append(event_type="run_started", status="running")

    def record_stage_started(
        self,
        *,
        stage: str,
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry:
        """Record transition into one canonical execution stage."""
        return self._append(
            event_type="stage_started",
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
            event_type="stage_completed",
            status="completed",
            stage=canonicalize_run_ledger_stage_name(stage),
            metrics_snapshot=metrics_snapshot,
            details=details,
        )

    def record_run_finished(
        self,
        *,
        metrics_snapshot: dict[str, int],
    ) -> RunLedgerEntry:
        """Record successful run completion."""
        return self._append(
            event_type="run_finished",
            status="success",
            metrics_snapshot=metrics_snapshot,
        )

    def record_run_failed(
        self,
        *,
        message: str,
        error_type: str | None,
        metrics_snapshot: dict[str, int],
    ) -> RunLedgerEntry:
        """Record failed run completion."""
        return self._append(
            event_type="run_failed",
            status="failed",
            message=message,
            error_type=error_type,
            metrics_snapshot=metrics_snapshot,
        )

    def record_run_shutdown(
        self,
        *,
        metrics_snapshot: dict[str, int],
    ) -> RunLedgerEntry:
        """Record graceful shutdown completion."""
        return self._append(
            event_type="run_shutdown",
            status="shutdown",
            metrics_snapshot=metrics_snapshot,
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
        payload: dict[str, object] = {"artifact_path": artifact_path}
        if details:
            payload.update(details)
        return self._append(
            event_type=PipelineEvent.ARTIFACT_PUBLISHED,
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
            event_type="dq_policy_applied",
            status=status,
            stage=stage,
            details=payload,
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
        event_family = infer_ledger_event_family(event_type)
        entry = RunLedgerEntry(
            entry_id=self._entry_id_factory(),
            manifest_id=self.manifest_id,
            run_id=self.run_id,
            event_type=event_type,
            event_family=event_family,
            occurred_at=datetime.now(UTC),
            status=status,
            stage=stage,
            message=message,
            error_type=error_type,
            dataset_ref=dataset_ref,
            lineage_fragment_id=lineage_fragment_id,
            metrics_snapshot=metrics_snapshot,
            details=self._build_diagnostic_details(
                event_type=event_type,
                event_family=event_family,
                status=status,
                stage=stage,
                error_type=error_type,
                dataset_ref=dataset_ref,
                lineage_fragment_id=lineage_fragment_id,
                details=details,
            ),
        )
        self.ledger_port.append(entry)
        return entry

    def _build_diagnostic_details(
        self,
        *,
        event_type: str,
        event_family: str,
        status: str | None,
        stage: str | None,
        error_type: str | None,
        dataset_ref: str | None,
        lineage_fragment_id: str | None,
        details: dict[str, object] | None,
    ) -> dict[str, object]:
        """Attach stable diagnostic metadata contract for ledger tooling."""
        normalized_details: dict[str, object] = {}
        if details:
            normalized_details.update(details)

        diagnostic: dict[str, object] = {
            "contract_version": _LEDGER_DETAILS_CONTRACT_VERSION,
            "event_type": event_type,
            "event_family": event_family,
            "manifest_id": self.manifest_id,
            "run_id": str(self.run_id),
        }
        _apply_optional_diagnostic_anchor(
            diagnostic,
            "pipeline",
            self.pipeline_name,
        )
        _apply_optional_diagnostic_anchor(diagnostic, "provider", self.provider)
        _apply_optional_diagnostic_anchor(diagnostic, "entity", self.entity)
        _apply_optional_diagnostic_anchor(diagnostic, "run_type", self.run_type)
        _apply_optional_diagnostic_anchor(
            diagnostic,
            "effective_config_hash",
            self.effective_config_hash,
        )
        _apply_optional_diagnostic_anchor(
            diagnostic,
            "contract_ref",
            self.contract_ref,
        )
        _apply_optional_diagnostic_anchor(
            diagnostic,
            "data_contract_version",
            self.contract_version,
        )
        _apply_optional_diagnostic_anchor(
            diagnostic,
            "dq_policy_ref",
            self.dq_policy_ref,
        )
        _apply_optional_diagnostic_anchor(
            diagnostic,
            "rule_bundle_version",
            self.rule_bundle_version,
        )
        _apply_optional_diagnostic_anchor(
            diagnostic,
            "dq_contract_compatibility_hash",
            self.dq_contract_compatibility_hash,
        )
        _apply_optional_diagnostic_anchor(
            diagnostic,
            "effective_config_artifact_id",
            self.effective_config_artifact_id,
        )
        _apply_optional_diagnostic_anchor(
            diagnostic,
            "composite_run_id",
            self.composite_run_id,
        )
        if status is not None:
            diagnostic["status"] = status
        if stage is not None:
            diagnostic["stage"] = stage
        if error_type is not None:
            diagnostic["error_type"] = error_type
        if dataset_ref is not None:
            diagnostic["dataset_ref"] = dataset_ref
        if lineage_fragment_id is not None:
            diagnostic["lineage_fragment_id"] = lineage_fragment_id

        normalized_details["_diagnostic"] = diagnostic
        return normalized_details
