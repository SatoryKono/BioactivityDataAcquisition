"""Application workflows for operator-facing observability diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from bioetl.application.observability.span_helpers import traced_async_operation
from bioetl.application.services.audit_inspection_service import (
    AuditInspectionResult,
    AuditInspectionService,
)
from bioetl.application.services.checkpoint_service import (
    CheckpointInfo,
    CheckpointService,
)
from bioetl.application.services.control_plane.run_manifest_inspection_service import (
    RunManifestInspectionResult,
    RunManifestInspectionService,
)

if TYPE_CHECKING:
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
        LineageRunExplanationResult,
    )
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.domain.ports import TracingPort

__all__ = [
    "AuditRunWorkflowResult",
    "CheckpointAuditWorkflowResult",
    "ObservabilityWorkflowService",
    "RunForensicDossierResult",
]

_TRACE_ATTR_AUDIT_ENTRIES_COUNT = "bioetl.audit_entries_count"
_TRACE_ATTR_COMPONENT = "bioetl.component"
_TRACE_ATTR_HAS_RUN_MANIFEST_SERVICE = "bioetl.has_run_manifest_service"
_TRACE_ATTR_OPERATION = "bioetl.operation"
_TRACE_ATTR_SUCCESS = "bioetl.success"
_TRACE_DRILLDOWN_PATH = "/a/grafana-exploretraces-app/"
_TRACE_DRILLDOWN_DEFAULT_FROM = "now-24h"
_TRACE_DRILLDOWN_DEFAULT_TO = "now"
_TRACE_WINDOW_PADDING = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class AuditRunWorkflowResult:
    """Aggregate operator view for one run's audit context."""

    run_id: str
    audit: AuditInspectionResult
    run_manifest: RunManifestInspectionResult | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation for CLI or API responses."""
        return {
            "run_id": self.run_id,
            "audit": self.audit.to_dict(),
            "run_manifest": (
                self.run_manifest.to_dict() if self.run_manifest is not None else None
            ),
        }


@dataclass(frozen=True, slots=True)
class CheckpointAuditWorkflowResult:
    """Aggregate operator view for one checkpoint and related audit context."""

    pipeline_name: str
    checkpoint: CheckpointInfo | None
    audit: AuditInspectionResult
    run_manifest: RunManifestInspectionResult | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation for CLI or API responses."""
        return {
            "pipeline_name": self.pipeline_name,
            "checkpoint": (
                {
                    "pipeline_name": self.checkpoint.pipeline_name,
                    "run_id": self.checkpoint.run_id,
                    "metadata": self.checkpoint.metadata,
                }
                if self.checkpoint is not None
                else None
            ),
            "audit": self.audit.to_dict(),
            "run_manifest": (
                self.run_manifest.to_dict() if self.run_manifest is not None else None
            ),
        }


@dataclass(frozen=True, slots=True)
class RunForensicDossierResult:
    """Bounded one-run dossier across observability and control-plane surfaces."""

    run_id: str
    pipeline_name: str | None
    audit: AuditInspectionResult
    run_manifest: RunManifestInspectionResult | None = None
    checkpoint: CheckpointInfo | None = None
    lineage: LineageRunExplanationResult | None = None
    quarantine_summary: dict[str, object] | None = None
    traceability: dict[str, object] | None = None
    status: dict[str, object] | None = None
    missing_evidence: tuple[str, ...] = ()
    degraded_evidence: tuple[str, ...] = ()
    next_steps: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe dossier payload for CLI or API responses."""
        return {
            "run_id": self.run_id,
            "pipeline_name": self.pipeline_name,
            "audit": self.audit.to_dict(),
            "run_manifest": (
                self.run_manifest.to_dict() if self.run_manifest is not None else None
            ),
            "checkpoint": (
                {
                    "pipeline_name": self.checkpoint.pipeline_name,
                    "run_id": self.checkpoint.run_id,
                    "metadata": self.checkpoint.metadata,
                }
                if self.checkpoint is not None
                else None
            ),
            "lineage": self.lineage.to_dict() if self.lineage is not None else None,
            "quarantine_summary": self.quarantine_summary,
            "traceability": self.traceability,
            "status": self.status,
            "missing_evidence": list(self.missing_evidence),
            "degraded_evidence": list(self.degraded_evidence),
            "next_steps": list(self.next_steps),
        }


@dataclass(slots=True)
class ObservabilityWorkflowService:
    """Compose audit, checkpoint, and run-manifest diagnostics workflows."""

    audit_service: AuditInspectionService
    checkpoint_service: CheckpointService
    run_manifest_service: RunManifestInspectionService | None = None
    lineage_service: LineageInspectionService | None = None
    quarantine_service: QuarantineService | None = None
    tracer: TracingPort | None = None
    TRACER_NAME = "bioetl.diagnostics"

    async def inspect_audit_run(
        self,
        run_id: str,
        *,
        limit: int = 100,
    ) -> AuditRunWorkflowResult:
        """Return audit entries and best-effort manifest context for one run."""
        if self.tracer is None:
            return await self._inspect_audit_run_impl(run_id=run_id, limit=limit)
        async with traced_async_operation(
            self.tracer,
            "diagnostics.inspect_audit_run",
            {
                _TRACE_ATTR_COMPONENT: "observability_workflow_service",
                _TRACE_ATTR_OPERATION: "inspect_audit_run",
                "bioetl.limit": limit,
                _TRACE_ATTR_HAS_RUN_MANIFEST_SERVICE: self.run_manifest_service
                is not None,
            },
            tracer_name=self.TRACER_NAME,
        ) as span:
            result = await self._inspect_audit_run_impl(run_id=run_id, limit=limit)
            span.set_attribute(_TRACE_ATTR_SUCCESS, True)
            span.set_attribute(
                _TRACE_ATTR_AUDIT_ENTRIES_COUNT, len(result.audit.entries)
            )
            span.set_attribute(
                "bioetl.has_run_manifest", result.run_manifest is not None
            )
            return result

    async def _inspect_audit_run_impl(
        self,
        *,
        run_id: str,
        limit: int,
    ) -> AuditRunWorkflowResult:
        """Implement audit-run diagnostics without tracing concerns."""
        audit = await self.audit_service.inspect_run(run_id, limit=limit)
        run_manifest = self._resolve_run_manifest(run_id)
        return AuditRunWorkflowResult(
            run_id=run_id,
            audit=audit,
            run_manifest=run_manifest,
        )

    async def inspect_run_dossier(
        self,
        run_id: str,
        *,
        audit_limit: int = 100,
    ) -> RunForensicDossierResult:
        """Return a one-run dossier across audit, control-plane, and triage seams."""
        if self.tracer is None:
            return await self._inspect_run_dossier_impl(
                run_id=run_id,
                audit_limit=audit_limit,
            )
        async with traced_async_operation(
            self.tracer,
            "diagnostics.inspect_run_dossier",
            {
                _TRACE_ATTR_COMPONENT: "observability_workflow_service",
                _TRACE_ATTR_OPERATION: "inspect_run_dossier",
                "bioetl.audit_limit": audit_limit,
                _TRACE_ATTR_HAS_RUN_MANIFEST_SERVICE: self.run_manifest_service
                is not None,
                "bioetl.has_lineage_service": self.lineage_service is not None,
                "bioetl.has_quarantine_service": self.quarantine_service is not None,
            },
            tracer_name=self.TRACER_NAME,
        ) as span:
            result = await self._inspect_run_dossier_impl(
                run_id=run_id,
                audit_limit=audit_limit,
            )
            span.set_attribute(_TRACE_ATTR_SUCCESS, True)
            span.set_attribute(
                _TRACE_ATTR_AUDIT_ENTRIES_COUNT, len(result.audit.entries)
            )
            span.set_attribute(
                "bioetl.missing_evidence_count", len(result.missing_evidence)
            )
            span.set_attribute(
                "bioetl.degraded_evidence_count", len(result.degraded_evidence)
            )
            return result

    async def _inspect_run_dossier_impl(
        self,
        *,
        run_id: str,
        audit_limit: int,
    ) -> RunForensicDossierResult:
        """Implement dossier aggregation without tracing concerns."""
        audit = await self.audit_service.inspect_run(run_id, limit=audit_limit)
        run_manifest = self._resolve_run_manifest(run_id)
        pipeline_name = self._resolve_pipeline_name(run_manifest)
        checkpoint = await self._resolve_checkpoint_for_run(
            run_id=run_id,
            pipeline_name=pipeline_name,
        )
        lineage = self._resolve_lineage_for_run(run_id)
        quarantine_summary = await self._resolve_quarantine_summary_for_run(
            run_id=run_id,
            pipeline_name=pipeline_name,
            run_manifest=run_manifest,
        )
        traceability = self._build_traceability_section(
            run_id=run_id,
            run_manifest=run_manifest,
            lineage=lineage,
            audit=audit,
            trace_links_enabled=self._trace_links_enabled(),
        )
        missing_evidence, degraded_evidence = self._classify_evidence_status(
            run_manifest=run_manifest,
            checkpoint=checkpoint,
            lineage=lineage,
            quarantine_summary=quarantine_summary,
            traceability=traceability,
        )
        next_steps = self._build_next_steps(
            run_manifest=run_manifest,
            missing_evidence=missing_evidence,
            degraded_evidence=degraded_evidence,
        )
        status = self._build_status_section(
            run_manifest=run_manifest,
            checkpoint=checkpoint,
            lineage=lineage,
            quarantine_summary=quarantine_summary,
            missing_evidence=missing_evidence,
            degraded_evidence=degraded_evidence,
        )
        return RunForensicDossierResult(
            run_id=run_id,
            pipeline_name=pipeline_name,
            audit=audit,
            run_manifest=run_manifest,
            checkpoint=checkpoint,
            lineage=lineage,
            quarantine_summary=quarantine_summary,
            traceability=traceability,
            status=status,
            missing_evidence=missing_evidence,
            degraded_evidence=degraded_evidence,
            next_steps=next_steps,
        )

    async def inspect_checkpoint_workflow(
        self,
        pipeline_name: str,
        *,
        run_id: str | None = None,
        audit_limit: int = 100,
    ) -> CheckpointAuditWorkflowResult:
        """Return checkpoint state and any related audit/run-manifest context."""
        if self.tracer is None:
            return await self._inspect_checkpoint_workflow_impl(
                pipeline_name=pipeline_name,
                run_id=run_id,
                audit_limit=audit_limit,
            )
        async with traced_async_operation(
            self.tracer,
            "diagnostics.inspect_checkpoint_workflow",
            {
                _TRACE_ATTR_COMPONENT: "observability_workflow_service",
                _TRACE_ATTR_OPERATION: "inspect_checkpoint_workflow",
                "bioetl.pipeline": pipeline_name,
                "bioetl.audit_limit": audit_limit,
                "bioetl.has_explicit_run_id": run_id is not None,
                _TRACE_ATTR_HAS_RUN_MANIFEST_SERVICE: self.run_manifest_service
                is not None,
            },
            tracer_name=self.TRACER_NAME,
        ) as span:
            result = await self._inspect_checkpoint_workflow_impl(
                pipeline_name=pipeline_name,
                run_id=run_id,
                audit_limit=audit_limit,
            )
            span.set_attribute(_TRACE_ATTR_SUCCESS, True)
            span.set_attribute(
                _TRACE_ATTR_AUDIT_ENTRIES_COUNT, len(result.audit.entries)
            )
            span.set_attribute("bioetl.has_checkpoint", result.checkpoint is not None)
            span.set_attribute(
                "bioetl.has_run_manifest", result.run_manifest is not None
            )
            return result

    async def _inspect_checkpoint_workflow_impl(
        self,
        *,
        pipeline_name: str,
        run_id: str | None,
        audit_limit: int,
    ) -> CheckpointAuditWorkflowResult:
        """Implement checkpoint diagnostics workflow without tracing concerns."""
        checkpoint = await self.checkpoint_service.get_checkpoint(pipeline_name)
        resolved_run_id = run_id or (
            checkpoint.run_id if checkpoint is not None else None
        )

        if resolved_run_id is None:
            audit = AuditInspectionResult(
                query={
                    "run_id": None,
                    "pipeline_name": pipeline_name,
                    "limit": audit_limit,
                },
                entries=(),
            )
            return CheckpointAuditWorkflowResult(
                pipeline_name=pipeline_name,
                checkpoint=checkpoint,
                audit=audit,
                run_manifest=None,
            )

        audit = await self.audit_service.inspect_run(
            resolved_run_id,
            limit=audit_limit,
        )
        run_manifest = self._resolve_run_manifest(resolved_run_id)
        return CheckpointAuditWorkflowResult(
            pipeline_name=pipeline_name,
            checkpoint=checkpoint,
            audit=audit,
            run_manifest=run_manifest,
        )

    async def _resolve_checkpoint_for_run(
        self,
        *,
        run_id: str,
        pipeline_name: str | None,
    ) -> CheckpointInfo | None:
        """Resolve checkpoint state best-effort for one run."""
        if pipeline_name is None:
            return None
        checkpoint = await self.checkpoint_service.get_checkpoint(pipeline_name)
        if checkpoint is None:
            return None
        if checkpoint.run_id in {None, run_id}:
            return checkpoint
        return CheckpointInfo(
            pipeline_name=checkpoint.pipeline_name,
            run_id=checkpoint.run_id,
            metadata={**checkpoint.metadata, "status": "mismatched_run_context"},
        )

    async def _resolve_quarantine_summary_for_run(
        self,
        *,
        run_id: str,
        pipeline_name: str | None,
        run_manifest: RunManifestInspectionResult | None,
    ) -> dict[str, object] | None:
        """Resolve bounded quarantine summary for one run when available."""
        if self.quarantine_service is None or pipeline_name is None:
            return None
        try:
            stats = await self.quarantine_service.get_filtered_stats(
                pipeline=pipeline_name,
                run_id=run_id,
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            return None
        return self._enrich_quarantine_summary(
            stats=stats,
            run_id=run_id,
            run_manifest=run_manifest,
        )

    def _resolve_lineage_for_run(
        self,
        run_id: str,
    ) -> LineageRunExplanationResult | None:
        """Resolve lineage explanation best-effort for one run."""
        if self.lineage_service is None:
            return None
        try:
            return self.lineage_service.explain_run(run_id)
        except ValueError:
            return None

    @staticmethod
    def _resolve_pipeline_name(
        run_manifest: RunManifestInspectionResult | None,
    ) -> str | None:
        """Resolve pipeline name from manifest context when available."""
        if run_manifest is None:
            return None
        return run_manifest.manifest.pipeline_name

    @staticmethod
    def _enrich_quarantine_summary(
        *,
        stats: dict[str, object],
        run_id: str,
        run_manifest: RunManifestInspectionResult | None,
    ) -> dict[str, object]:
        """Attach run-scoped metadata and Bronze denominator when available."""
        summary = dict(stats)
        summary["run_scope"] = {"run_id": run_id}
        silver_stats = summary.get("silver_filter_rejects")
        if (
            run_manifest is not None
            and isinstance(silver_stats, dict)
            and isinstance(silver_stats.get("total_count"), int)
        ):
            bronze_records = ObservabilityWorkflowService._resolve_bronze_record_count(
                run_manifest
            )
            if bronze_records is not None:
                silver_total = silver_stats["total_count"]
                silver_stats["bronze_records"] = bronze_records
                silver_stats["bronze_ratio"] = silver_total / bronze_records
                silver_stats["bronze_ratio_pct"] = (silver_total / bronze_records) * 100
        return summary

    @staticmethod
    def _resolve_bronze_record_count(
        run_manifest: RunManifestInspectionResult,
    ) -> int | None:
        """Return the strongest Bronze record denominator from manifest ledger data."""
        bronze_records: int | None = None
        for entry in run_manifest.ledger_entries:
            metrics_snapshot = getattr(entry, "metrics_snapshot", None)
            if not isinstance(metrics_snapshot, dict):
                continue
            value = metrics_snapshot.get("records_bronze")
            if not isinstance(value, int) or value <= 0:
                continue
            bronze_records = (
                value if bronze_records is None else max(bronze_records, value)
            )
        return bronze_records

    @staticmethod
    def _build_traceability_section(
        *,
        run_id: str,
        run_manifest: RunManifestInspectionResult | None,
        lineage: LineageRunExplanationResult | None,
        audit: AuditInspectionResult,
        trace_links_enabled: bool,
    ) -> dict[str, object]:
        """Build a stable traceability summary for one run dossier."""
        diagnostics = run_manifest.diagnostics if run_manifest is not None else {}
        identity_graph = run_manifest.identity_graph if run_manifest is not None else {}
        provider = ObservabilityWorkflowService._resolve_manifest_provider(run_manifest)
        run_type = ObservabilityWorkflowService._resolve_manifest_run_type(run_manifest)
        trace_urls = (
            ObservabilityWorkflowService._build_trace_urls(
                run_id=run_id,
                pipeline_name=ObservabilityWorkflowService._resolve_pipeline_name(
                    run_manifest
                ),
                provider=provider,
                run_type=run_type,
                run_manifest=run_manifest,
                audit=audit,
            )
            if trace_links_enabled
            else []
        )
        trace_ids = ObservabilityWorkflowService._build_trace_ids(
            run_id=run_id,
            diagnostics=diagnostics,
            trace_links_available=bool(trace_urls),
        )
        return {
            "audit_entries_count": len(audit.entries),
            "identity_graph_complete": diagnostics.get("identity_graph_complete"),
            "correlation_anchor_gaps": diagnostics.get("correlation_anchor_gaps"),
            "lineage_fragment_ids": diagnostics.get("lineage_fragment_ids")
            or (list(lineage.fragment_ids) if lineage is not None else []),
            "artifact_refs": diagnostics.get("artifact_refs", []),
            "trace_ids": trace_ids,
            "trace_urls": trace_urls,
            "trace_links_available": bool(trace_urls),
            "persistence_profile": diagnostics.get("persistence_profile"),
            "replay_capability": identity_graph.get("replay_capability")
            or diagnostics.get("replay_capability"),
        }

    def _trace_links_enabled(self) -> bool:
        """Return whether operator-facing trace drilldowns should be exposed."""
        if self.tracer is None:
            return False
        return getattr(self.tracer, "is_noop", False) is not True

    @staticmethod
    def _build_trace_ids(
        *,
        run_id: str,
        diagnostics: dict[str, object],
        trace_links_available: bool,
    ) -> list[str]:
        """Return bounded operator-facing trace correlation identifiers."""
        explicit_trace_ids = diagnostics.get("trace_ids")
        if isinstance(explicit_trace_ids, list):
            normalized = [
                value.strip()
                for value in explicit_trace_ids
                if isinstance(value, str) and value.strip()
            ]
            if normalized:
                return list(dict.fromkeys(normalized))
        if trace_links_available and run_id:
            return [run_id]
        return []

    @staticmethod
    def _resolve_manifest_provider(
        run_manifest: RunManifestInspectionResult | None,
    ) -> str | None:
        """Resolve provider from manifest context when available."""
        if run_manifest is None:
            return None
        provider = getattr(run_manifest.manifest, "provider", None)
        return str(provider) if provider not in {None, ""} else None

    @staticmethod
    def _resolve_manifest_run_type(
        run_manifest: RunManifestInspectionResult | None,
    ) -> str | None:
        """Resolve run type from manifest context when available."""
        if run_manifest is None:
            return None
        run_type = getattr(run_manifest.manifest, "run_type", None)
        if hasattr(run_type, "value"):
            run_type = run_type.value
        return str(run_type) if run_type not in {None, ""} else None

    @staticmethod
    def _build_trace_urls(
        *,
        run_id: str,
        pipeline_name: str | None,
        provider: str | None,
        run_type: str | None,
        run_manifest: RunManifestInspectionResult | None,
        audit: AuditInspectionResult,
    ) -> list[str]:
        """Build best-effort operator trace drilldown links for one run."""
        query = ObservabilityWorkflowService._build_traceql_query(
            run_id=run_id,
            pipeline_name=pipeline_name,
            provider=provider,
            run_type=run_type,
        )
        if query is None:
            return []
        from_value, to_value = ObservabilityWorkflowService._build_trace_time_window(
            run_manifest=run_manifest,
            audit=audit,
        )
        params = urlencode(
            {
                "from": from_value,
                "to": to_value,
                "datasource": "tempo",
                "queryType": "traceqlSearch",
                "query": query,
            }
        )
        return [f"{_TRACE_DRILLDOWN_PATH}?{params}"]

    @staticmethod
    def _build_traceql_query(
        *,
        run_id: str,
        pipeline_name: str | None,
        provider: str | None,
        run_type: str | None,
    ) -> str | None:
        """Build a low-cardinality TraceQL filter for dossier drilldown."""
        if not run_id:
            return None
        filters = [f'span."bioetl.run_id" = "{run_id}"']
        if pipeline_name:
            filters.append(f'span."bioetl.pipeline" = "{pipeline_name}"')
        if run_type:
            filters.append(f'span."bioetl.run_type" = "{run_type}"')
        if provider:
            filters.append(f'span."bioetl.provider" = "{provider}"')
        return "{ " + " && ".join(filters) + " }"

    @staticmethod
    def _build_trace_time_window(
        *,
        run_manifest: RunManifestInspectionResult | None,
        audit: AuditInspectionResult,
    ) -> tuple[str, str]:
        """Build a best-effort Grafana time window around the run evidence."""
        timestamps: list[datetime] = []
        manifest_created_at = (
            getattr(run_manifest.manifest, "created_at", None)
            if run_manifest is not None
            else None
        )
        normalized_manifest_time = ObservabilityWorkflowService._normalize_datetime(
            manifest_created_at
        )
        if normalized_manifest_time is not None:
            timestamps.append(normalized_manifest_time)
        for entry in audit.entries:
            normalized_entry_time = ObservabilityWorkflowService._normalize_datetime(
                entry.timestamp
            )
            if normalized_entry_time is not None:
                timestamps.append(normalized_entry_time)
        if not timestamps:
            return (_TRACE_DRILLDOWN_DEFAULT_FROM, _TRACE_DRILLDOWN_DEFAULT_TO)
        start = min(timestamps) - _TRACE_WINDOW_PADDING
        end = max(timestamps) + _TRACE_WINDOW_PADDING
        return (
            str(int(start.timestamp() * 1000)),
            str(int(end.timestamp() * 1000)),
        )

    @staticmethod
    def _normalize_datetime(value: object) -> datetime | None:
        """Normalize datetimes used for operator drilldown windows."""
        if not isinstance(value, datetime):
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _classify_evidence_status(
        self,
        *,
        run_manifest: RunManifestInspectionResult | None,
        checkpoint: CheckpointInfo | None,
        lineage: LineageRunExplanationResult | None,
        quarantine_summary: dict[str, object] | None,
        traceability: dict[str, object],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Classify missing vs degraded evidence for one dossier."""
        missing = ["run_manifest"] if run_manifest is None else []
        degraded = self._classify_checkpoint_status(checkpoint)
        if lineage is None:
            degraded.append("lineage")
        if quarantine_summary is None:
            degraded.append("quarantine_summary")
        degraded.extend(self._collect_traceability_degradation(traceability))
        return tuple(missing), tuple(degraded)

    @staticmethod
    def _classify_checkpoint_status(checkpoint: CheckpointInfo | None) -> list[str]:
        """Return checkpoint-specific degraded evidence markers."""
        if checkpoint is None:
            return ["checkpoint"]
        if checkpoint.metadata.get("status") == "mismatched_run_context":
            return ["checkpoint_mismatched_run"]
        return []

    @staticmethod
    def _collect_traceability_degradation(
        traceability: dict[str, object],
    ) -> list[str]:
        """Return degraded evidence markers derived from the traceability section."""
        degraded: list[str] = []
        persistence_profile = traceability.get("persistence_profile")
        if isinstance(persistence_profile, dict):
            degraded.extend(
                ObservabilityWorkflowService._collect_persistence_profile_degradation(
                    persistence_profile
                )
            )
        if ObservabilityWorkflowService._has_correlation_anchor_gaps(traceability):
            degraded.append("correlation_anchor_gaps")
        if not traceability.get("trace_links_available", False):
            degraded.append("trace_links_unavailable")
        return degraded

    @staticmethod
    def _collect_persistence_profile_degradation(
        persistence_profile: dict[str, object],
    ) -> list[str]:
        """Return degraded evidence markers derived from persistence profile gaps."""
        degraded: list[str] = []
        attained = persistence_profile.get("attained_profile")
        if attained not in {None, "forensic_grade"}:
            degraded.append(f"persistence_profile:{attained}")
        for key in (
            "replay_ready_missing_requirements",
            "forensic_grade_missing_requirements",
        ):
            value = persistence_profile.get(key)
            if isinstance(value, list) and value:
                degraded.append(key)
        return degraded

    @staticmethod
    def _has_correlation_anchor_gaps(traceability: dict[str, object]) -> bool:
        """Return whether the dossier reports correlation-anchor coverage gaps."""
        correlation_gaps = traceability.get("correlation_anchor_gaps")
        return isinstance(correlation_gaps, dict) and any(
            isinstance(value, int) and value > 0 for value in correlation_gaps.values()
        )

    @staticmethod
    def _build_next_steps(
        *,
        run_manifest: RunManifestInspectionResult | None,
        missing_evidence: tuple[str, ...],
        degraded_evidence: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Build operator-facing next steps for dossier follow-up."""
        steps: list[str] = []
        if run_manifest is not None:
            diagnostics_steps = run_manifest.diagnostics.get("next_steps")
            if isinstance(diagnostics_steps, list):
                steps.extend(str(step) for step in diagnostics_steps)
        if "run_manifest" in missing_evidence:
            steps.append(
                "Persist and inspect run-manifest/ledger artifacts for this run."
            )
        if any(item.startswith("persistence_profile:") for item in degraded_evidence):
            steps.append(
                "Review required persistence profile before treating this run as forensic-grade."
            )
        if "trace_links_unavailable" in degraded_evidence:
            steps.append(
                "Use audit, manifest, and lineage sections as the current traceability fallback."
            )
        seen: dict[str, None] = {}
        return tuple(
            step for step in steps if not (step in seen or seen.setdefault(step, None))
        )

    @staticmethod
    def _build_status_section(
        *,
        run_manifest: RunManifestInspectionResult | None,
        checkpoint: CheckpointInfo | None,
        lineage: LineageRunExplanationResult | None,
        quarantine_summary: dict[str, object] | None,
        missing_evidence: tuple[str, ...],
        degraded_evidence: tuple[str, ...],
    ) -> dict[str, object]:
        """Build a concise high-level dossier status section."""
        diagnostics = run_manifest.diagnostics if run_manifest is not None else {}
        persistence_profile = diagnostics.get("persistence_profile")
        attained_profile = (
            persistence_profile.get("attained_profile")
            if isinstance(persistence_profile, dict)
            else None
        )
        return {
            "forensic_profile": attained_profile,
            "latest_status": diagnostics.get("latest_status"),
            "latest_event_type": diagnostics.get("latest_event_type"),
            "checkpoint_status": (
                "missing"
                if checkpoint is None
                else checkpoint.metadata.get("status", "present")
            ),
            "lineage_status": "present" if lineage is not None else "missing",
            "quarantine_status": (
                "present" if quarantine_summary is not None else "missing"
            ),
            "missing_evidence_count": len(missing_evidence),
            "degraded_evidence_count": len(degraded_evidence),
        }

    def _resolve_run_manifest(
        self,
        identifier: str,
    ) -> RunManifestInspectionResult | None:
        """Resolve manifest context best-effort without failing the workflow."""
        if self.run_manifest_service is None:
            return None
        try:
            return self.run_manifest_service.show(identifier)
        except ValueError:
            return None
