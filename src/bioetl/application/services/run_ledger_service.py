"""Application service for append-only run-ledger events."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.ports import RunLedgerPort
from bioetl.domain.types import RunID

__all__ = ["RunLedgerService"]


@dataclass(slots=True)
class RunLedgerService:
    """Append immutable control-plane lifecycle entries for one manifest."""

    ledger_port: RunLedgerPort
    manifest_id: str
    run_id: RunID
    _entry_id_factory: Callable[[], str] = field(
        default_factory=lambda: lambda: str(uuid4())
    )

    def record_manifest_created(self, manifest: RunManifest) -> RunLedgerEntry:
        """Record manifest creation as the first control-plane event."""
        return self._append(
            event_type="manifest_created",
            status="created",
            details={
                "execution_fingerprint": manifest.execution_fingerprint,
                "pipeline_name": manifest.pipeline_name,
                "provider": manifest.provider,
                "entity": manifest.entity,
            },
        )

    def record_run_started(self) -> RunLedgerEntry:
        """Record the transition into active execution."""
        return self._append(event_type="run_started", status="running")

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
            stage=stage,
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
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry:
        """Record a published layer artifact tied to this manifest."""
        payload: dict[str, object] = {"artifact_path": artifact_path}
        if details:
            payload.update(details)
        return self._append(
            event_type="artifact_published",
            status="published",
            stage=layer,
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
        metrics_snapshot: dict[str, int] | None = None,
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry:
        """Create and append one ledger entry."""
        entry = RunLedgerEntry(
            entry_id=self._entry_id_factory(),
            manifest_id=self.manifest_id,
            run_id=self.run_id,
            event_type=event_type,
            occurred_at=datetime.now(UTC),
            status=status,
            stage=stage,
            message=message,
            error_type=error_type,
            metrics_snapshot=metrics_snapshot,
            details=details,
        )
        self.ledger_port.append(entry)
        return entry
