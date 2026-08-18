"""Generate Trust validation panel fixtures for empty/error/populated close-ups.

Outputs contract-shaped JSON under tests/fixtures/grafana/control_plane_validation/
for panels 9413–9418 (#8576 / #8578 / #8976). Does not invent Prometheus metrics.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from bioetl.application.observability.control_plane_evidence import (
    FAILURE_REASON_CATEGORIES,
    ControlPlaneEvidenceService,
    EvidenceScopeContext,
)
from bioetl.application.observability.control_plane_evidence.checks import (
    EvidenceCheckResult,
)
from bioetl.application.observability.control_plane_evidence.failure_reasons import (
    build_failure_reason_rows,
)
from bioetl.application.observability.control_plane_evidence.models import (
    evidence_payload,
)
from bioetl.application.observability.control_plane_evidence.service_support import (
    source_error_payload,
)
from bioetl.domain.control_plane import RunCodeProvenance, RunLedgerEntry, RunManifest
from bioetl.domain.types import RunID, RunType
from scripts.ops.observability.trust_validation_fixture_materialization import (
    materialize_trust_validation_fixture_matrix,
)

NOW = datetime(2026, 8, 11, tzinfo=UTC)
RUN_ID = RunID(UUID("00000000-0000-0000-0000-000000008576"))
DEFAULT_OUT = Path("tests/fixtures/grafana/control_plane_validation")

PANEL_MAP = {
    9413: "checkpoint-validation",
    9414: "manifest-validation",
    9415: "lineage-validation",
    9416: "retention-compliance",
    9417: "failure-reasons",
    9418: "manifest-validation",
}


def _manifest() -> RunManifest:
    return RunManifest(
        manifest_id="manifest-8576-fixture",
        execution_fingerprint="fp-8576-fixture",
        schema_version="1.0",
        created_at=NOW - timedelta(days=1),
        run_id=RUN_ID,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"required_persistence_profile": "replay_ready"},
        code_provenance=RunCodeProvenance(
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            contract_schema_hash="schema-hash",
            dq_policy_ref="chembl.activity.dq",
            rule_bundle_version="1",
            effective_config_artifact_id="effective-config-8576",
        ),
    )


def _scope(manifest: RunManifest | None) -> EvidenceScopeContext:
    return EvidenceScopeContext(
        requested_pipeline="chembl_activity",
        selected_run_id=str(RUN_ID),
        selected_run_types=("incremental",),
        resolved_via=(
            "selected_run_id" if manifest is not None else "selected_run_id_not_found"
        ),
        manifest=manifest,
    )


def _envelope(
    endpoint: str,
    checks: tuple[EvidenceCheckResult, ...],
    *,
    manifest: RunManifest,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    return evidence_payload(
        endpoint=endpoint,
        checks=checks,
        requested_pipeline="chembl_activity",
        selected_run_id=str(RUN_ID),
        selected_run_types=("incremental",),
        resolved_via="selected_run_id",
        manifest=manifest,
        additional_fields=extra,
    )


def _http_503(endpoint: str) -> dict[str, object]:
    return {
        "contract": "control_plane_validation_evidence_v1",
        "endpoint": endpoint,
        "status": "ERROR",
        "pipeline": "chembl_activity",
        "run_type": "incremental",
        "run_id": str(RUN_ID),
        "manifest_id": None,
        "resolved_via": "service_unavailable",
        "summary": {
            "check_count": 1,
            "ok_count": 0,
            "warning_count": 0,
            "error_count": 1,
            "unknown_count": 0,
        },
        "rows": [
            {
                "check": "service",
                "status": "ERROR",
                "reason": "control_plane_evidence_service_unavailable",
                "detail": (
                    "Control-plane evidence service is not configured on this host."
                ),
            }
        ],
        "http_status": 503,
    }


def _empty_rows(endpoint: str, manifest: RunManifest) -> dict[str, object]:
    payload = _envelope(endpoint, (), manifest=manifest)
    payload["rows"] = []
    payload["status"] = "UNKNOWN"
    payload["summary"] = {
        "check_count": 0,
        "ok_count": 0,
        "warning_count": 0,
        "error_count": 0,
        "unknown_count": 0,
    }
    payload["note"] = (
        "Synthetic rows=[] for Infinity noValue visual path; not a live service response."
    )
    return payload


def build_matrix() -> dict[str, dict[str, dict[str, object]]]:
    svc = ControlPlaneEvidenceService()
    manifest = _manifest()
    scope = _scope(manifest)
    unresolved = _scope(None)

    checkpoint_pop = svc.checkpoint_validation(
        scope=scope,
        checkpoint=(
            RUN_ID,
            {
                "manifest_id": manifest.manifest_id,
                "pipeline_name": manifest.pipeline_name,
                "run_type": manifest.run_type.value,
                "execution_fingerprint": manifest.execution_fingerprint,
                "records_processed": 42,
                "checkpoint_checksum_valid": True,
                "checkpoint_saved_at_epoch_seconds": NOW.timestamp(),
            },
        ),
        evidence_source="immutable_manifest_history",
        aggregate_scope_unknown=False,
    )
    checkpoint_empty = svc.checkpoint_validation(
        scope=scope,
        checkpoint=None,
        evidence_source="immutable_manifest_history",
        aggregate_scope_unknown=False,
    )

    manifest_pop = _envelope(
        "manifest-validation",
        (
            EvidenceCheckResult(
                "parse",
                "OK",
                "manifest_parse_ok",
                "The raw manifest envelope was parsed.",
            ),
            EvidenceCheckResult(
                "schema", "OK", "manifest_schema_valid", "Manifest schema is supported."
            ),
            EvidenceCheckResult(
                "schema_version",
                "OK",
                "manifest_schema_version_supported",
                "schema_version 1.0 is supported.",
            ),
            EvidenceCheckResult(
                "contract",
                "OK",
                "manifest_contract_compatible",
                "Contract ref/version match the run provenance.",
            ),
            EvidenceCheckResult(
                "identity",
                "OK",
                "manifest_identity_consistent",
                "Run/pipeline identity fields are consistent.",
            ),
        ),
        manifest=manifest,
    )
    lineage_pop = _envelope(
        "lineage-validation",
        (
            EvidenceCheckResult(
                "closure",
                "OK",
                "lineage_closure_ok",
                "All lineage references resolve within the fragment set.",
            ),
            EvidenceCheckResult(
                "identity",
                "OK",
                "lineage_identity_consistent",
                "Node identities match the selected run anchors.",
            ),
            EvidenceCheckResult(
                "cycles", "OK", "lineage_acyclic", "No cycles were detected."
            ),
            EvidenceCheckResult(
                "persistence",
                "OK",
                "lineage_persistence_profile_met",
                "Required persistence profile is satisfied.",
            ),
        ),
        manifest=manifest,
        extra={"fragment_count": 2, "edge_count": 3, "node_count": 4},
    )
    retention_pop = _envelope(
        "retention-compliance",
        (
            EvidenceCheckResult(
                "retention_policy",
                "OK",
                "retention_policy_ok",
                "Default retention policy is configured.",
            ),
            EvidenceCheckResult(
                "evidence_floor",
                "OK",
                "reproducibility_evidence_floor_met",
                "Required reproducibility evidence is present.",
            ),
            EvidenceCheckResult(
                "archive",
                "OK",
                "archive_support_available",
                "Archive support is available for the selected run.",
            ),
        ),
        manifest=manifest,
        extra={
            "retention_days": 90,
            "cutoff": (NOW - timedelta(days=90)).isoformat(),
            "artifacts": [],
        },
    )

    failed_entries = (
        RunLedgerEntry(
            entry_id="e1",
            manifest_id=manifest.manifest_id,
            run_id=manifest.run_id,
            event_type="run_failed",
            status="failed",
            error_type="HTTPError",
            event_family="provider",
            stage="bronze",
            occurred_at=NOW,
        ),
        RunLedgerEntry(
            entry_id="e2",
            manifest_id=manifest.manifest_id,
            run_id=manifest.run_id,
            event_type="run_failed",
            status="failed",
            error_type="DataQualityError",
            event_family="dq",
            stage="silver",
            occurred_at=NOW,
        ),
    )
    fail_rows, fail_total = build_failure_reason_rows(failed_entries)
    fr_pop = _envelope(
        "failure-reasons",
        (
            EvidenceCheckResult(
                "classification",
                "OK",
                "failure_reasons_bounded",
                "Failed ledger events were projected to the fixed category set.",
            ),
        ),
        manifest=manifest,
        extra={
            "categories": list(FAILURE_REASON_CATEGORIES),
            "total_failure_count": fail_total,
        },
    )
    fr_pop["rows"] = fail_rows

    zero_rows, zero_total = build_failure_reason_rows(())
    fr_zero = _envelope(
        "failure-reasons",
        (
            EvidenceCheckResult(
                "classification",
                "OK",
                "failure_reasons_bounded",
                "Failed ledger events were projected to the fixed category set.",
            ),
        ),
        manifest=manifest,
        extra={
            "categories": list(FAILURE_REASON_CATEGORIES),
            "total_failure_count": zero_total,
        },
    )
    fr_zero["rows"] = zero_rows

    return {
        "checkpoint-validation": {
            "populated": checkpoint_pop,
            "valid_empty_or_unknown": checkpoint_empty,
            "backend_error": source_error_payload(
                endpoint="checkpoint-validation",
                scope=scope,
                reason="checkpoint_parse_error",
                check="parse",
            ),
            "service_unavailable": _http_503("checkpoint-validation"),
            "empty_rows": _empty_rows("checkpoint-validation", manifest),
            "aggregate_scope_unknown": svc.checkpoint_validation(
                scope=scope,
                checkpoint=None,
                evidence_source="none",
                aggregate_scope_unknown=True,
            ),
        },
        "manifest-validation": {
            "populated": manifest_pop,
            "valid_empty_or_unknown": svc.manifest_validation(scope=unresolved),
            "incomplete_reasons": _envelope(
                "manifest-validation",
                tuple(
                    EvidenceCheckResult(
                        f"trust_reason_{index}",
                        "UNKNOWN",
                        reason,
                        "Missing or contradictory exact-run evidence.",
                    )
                    for index, reason in enumerate(
                        (
                            "manifest_contract_compatibility_not_verified",
                            "checkpoint_artifact_not_observed",
                            "lineage_closure_not_verified",
                            "retention_plan_not_observed",
                        )
                    )
                ),
                manifest=manifest,
            ),
            "backend_error": source_error_payload(
                endpoint="manifest-validation",
                scope=scope,
                reason="manifest_parse_error",
                check="parse",
            ),
            "service_unavailable": _http_503("manifest-validation"),
            "empty_rows": _empty_rows("manifest-validation", manifest),
        },
        "lineage-validation": {
            "populated": lineage_pop,
            "valid_empty_or_unknown": svc.lineage_validation(scope=unresolved),
            "backend_error": source_error_payload(
                endpoint="lineage-validation",
                scope=scope,
                reason="lineage_source_read_error",
                check="closure",
            ),
            "service_unavailable": _http_503("lineage-validation"),
            "empty_rows": _empty_rows("lineage-validation", manifest),
        },
        "retention-compliance": {
            "populated": retention_pop,
            "valid_empty_or_unknown": svc.retention_compliance(
                scope=unresolved, now=NOW
            ),
            "backend_error": source_error_payload(
                endpoint="retention-compliance",
                scope=scope,
                reason="retention_plan_read_error",
                check="retention_policy",
            ),
            "service_unavailable": _http_503("retention-compliance"),
            "empty_rows": _empty_rows("retention-compliance", manifest),
        },
        "failure-reasons": {
            "populated": fr_pop,
            "valid_empty_or_unknown": svc.failure_reasons(scope=unresolved),
            "zero_failures": fr_zero,
            "backend_error": source_error_payload(
                endpoint="failure-reasons",
                scope=scope,
                reason="run_ledger_parse_error",
                check="classification",
            ),
            "service_unavailable": _http_503("failure-reasons"),
            "empty_rows": _empty_rows("failure-reasons", manifest),
        },
    }


def write_matrix(out: Path) -> dict[str, object]:
    return materialize_trust_validation_fixture_matrix(
        out=out,
        matrix=build_matrix(),
        panel_map=PANEL_MAP,
        fixture_run_id=RUN_ID,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUT,
        help="Fixture root (default: tests/fixtures/grafana/control_plane_validation)",
    )
    args = parser.parse_args()
    write_matrix(args.output_dir)
    print(f"INDEX -> {args.output_dir / 'INDEX.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
