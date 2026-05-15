"""Control-plane identity evidence payload helpers for Grafana HTTP panels."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from bioetl.domain.control_plane import (
    RunArtifactRef,
    RunInputSnapshotRef,
    RunLedgerEntry,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.control_plane.run_ledger import (
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
    COMPOSITE_ENRICHER_COMPLETED_EVENT,
    COMPOSITE_MERGE_COMPLETED_EVENT,
)
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint

IDENTITY_EVIDENCE_CONTRACT = "control_plane_identity_evidence_v1"

_COMPOSITE_EVENTS = frozenset(
    {
        COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
        COMPOSITE_ENRICHER_COMPLETED_EVENT,
        COMPOSITE_MERGE_COMPLETED_EVENT,
    }
)
_TERMINAL_STATUSES = frozenset({"success", "failed", "shutdown"})
_CHECKPOINT_ANCHORS = (
    "manifest_id",
    "execution_fingerprint",
    "effective_config_hash",
    "effective_config_artifact_id",
    "input_snapshot_fingerprint",
    "composite_run_identity",
)


class _LedgerEntryProvider(Protocol):
    def list_entries(self, manifest_id: str) -> list[RunLedgerEntry]: ...


@dataclass(frozen=True, slots=True)
class _AnchorSpec:
    priority: str
    name: str
    label: str
    source: str
    value_format: str
    why: str
    rendering: str
    copy: bool
    drilldown: str
    missing_severity: str


_ANCHOR_SPECS: tuple[_AnchorSpec, ...] = (
    _AnchorSpec(
        "P0",
        "run_id",
        "Run ID",
        "RunManifest.run_id; identity graph",
        "UUID v4",
        "Primary correlation anchor for manifest, ledger, logs, and traces.",
        "overview: short; details: full",
        True,
        "Run Manifest details; ledger by run_id; Loki/Tempo links",
        "FAILING",
    ),
    _AnchorSpec(
        "P0",
        "manifest_id",
        "Manifest ID",
        "RunManifest.manifest_id; identity graph",
        "opaque string / UUID-like",
        "Immutable control-plane artifact anchor.",
        "overview: short; details: full",
        True,
        "Manifest JSON; run-manifest CLI show; ledger events",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P0",
        "pipeline_name",
        "Pipeline",
        "RunManifest.pipeline_name",
        "snake_case",
        "Shows which pipeline was executed.",
        "full in card/table",
        False,
        "Pipeline dashboard; manifest filter",
        "FAILING",
    ),
    _AnchorSpec(
        "P0",
        "provider_entity",
        "Provider / Entity",
        "RunManifest.provider + RunManifest.entity",
        "provider.entity",
        "Fixes dataset and contract scope.",
        "full in card/table",
        False,
        "Dataset lineage; contract registry entry",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P0",
        "runtime_mode",
        "Runtime Mode",
        "RunManifest.run_type + runtime_config/launch_context flags",
        "run_type + flags",
        "Shows the runtime mode for the launch.",
        "overview badge; details tuple",
        False,
        "Manifest runtime_config and launch_context",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P0",
        "execution_fingerprint",
        "Execution FP",
        "RunManifest.execution_fingerprint; identity graph",
        "sha256 hex / opaque fingerprint",
        "Semantic reproducibility and compatibility anchor.",
        "overview: short; details: full",
        True,
        "Identity graph; manifest diff; replay diagnostics",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P0",
        "git_commit",
        "Git Commit",
        "RunManifest.code_provenance.git_commit",
        "git SHA",
        "Shows which code produced the result.",
        "overview: short; details: full",
        True,
        "Repository commit / release notes",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P0",
        "pipeline_version",
        "Pipeline Version",
        "RunManifest.code_provenance.pipeline_version",
        "semver / string",
        "Pipeline/config contract version.",
        "full",
        False,
        "Pipeline spec / changelog",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P0",
        "effective_config_hash",
        "Effective Config Hash",
        "RunCodeProvenance.effective_config_hash; checkpoint metadata",
        "sha256 hex",
        "Resolved config actually used by the run.",
        "overview: short; details: full",
        True,
        "Effective config artifact; config diff",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P0",
        "effective_config_artifact_id",
        "Effective Config Artifact",
        "RunCodeProvenance.effective_config_artifact_id; base_summary",
        "artifact ref",
        "Direct handoff to resolved config.",
        "overview: short; details: full",
        True,
        "Resolved config artifact view",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P0",
        "contract_ref",
        "Contract Ref",
        "RunCodeProvenance.contract_ref; contract registry",
        "provider.entity",
        "Gold/DQ contract scope.",
        "full",
        True,
        "Contract registry entry; Gold contract doc",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P0",
        "contract_version",
        "Contract Version",
        "RunCodeProvenance.contract_version; contract registry",
        "semver",
        "Applied Gold/DQ contract version.",
        "full",
        False,
        "Contract registry / migration guide",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P0",
        "contract_schema_hash",
        "Contract Schema Hash",
        "RunCodeProvenance.contract_schema_hash; registry identity.schema_hash",
        "sha256 hex",
        "Protects against schema drift.",
        "overview: short; details: full",
        True,
        "Contract artifact diff",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P0",
        "input_snapshot_identity_fingerprint",
        "Input Snapshot FP",
        "RunManifest.source_refs[*].input_snapshots",
        "sha256 / opaque fingerprint",
        "Fixes the immutable input closure.",
        "overview: short; details: full",
        True,
        "Input snapshots details",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P0",
        "input_snapshot_count",
        "Input Snapshots",
        "RunManifest.source_refs[*].input_snapshots",
        "integer + array",
        "Shows whether input closure was captured.",
        "count in overview; IDs in details",
        False,
        "Input snapshots table",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P0",
        "replay_mode",
        "Replay / Backfill / Rebuild",
        "RunManifest.run_type + replay parentage",
        "enum / badge",
        "Shows whether the run is replay/backfill/rebuild/incremental.",
        "badge in overview",
        False,
        "Replay diagnostics",
        "INFO",
    ),
    _AnchorSpec(
        "P0",
        "replay_of_run_id",
        "Parent Run ID",
        "RunManifest.replay_of_run_id; identity graph",
        "UUID",
        "Parent run for replay lineage.",
        "short when replay; full in details",
        True,
        "Parent manifest/ledger",
        "FAILING",
    ),
    _AnchorSpec(
        "P0",
        "replay_of_manifest_id",
        "Parent Manifest ID",
        "RunManifest.replay_of_manifest_id; identity graph",
        "opaque id / UUID-like",
        "Parent manifest for replay lineage.",
        "short when replay; full in details",
        True,
        "Parent manifest details",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P0",
        "checkpoint_anchor_status",
        "Checkpoint Anchors",
        "Checkpoint metadata compared with current runtime anchors",
        "OK / MISMATCH / MISSING / PARTIAL",
        "Shows whether persisted checkpoint anchors match current runtime anchors.",
        "status badge; pairwise table",
        False,
        "Checkpoint compatibility panel",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P0",
        "composite_run_identity",
        "Composite Run Identity",
        "Composite checkpoint metadata; runtime config",
        "UUID / opaque run-scoped id",
        "Prevents resume across different composite executions.",
        "only for composite; full in details",
        True,
        "Composite checkpoint details",
        "FAILING",
    ),
    _AnchorSpec(
        "P0",
        "identity_graph_complete",
        "Identity Graph",
        "identity evidence gaps",
        "boolean + gap count",
        "Single identity gap indicator.",
        "status badge plus gap count",
        False,
        "Identity gaps table",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P1",
        "config_hash",
        "Source Config Hash",
        "RunCodeProvenance.config_hash",
        "sha256 hex",
        "Raw pipeline config provenance.",
        "details only; compact short",
        True,
        "Manifest/config diff",
        "WARNING",
    ),
    _AnchorSpec(
        "P1",
        "dq_policy_ref",
        "DQ Policy Ref",
        "RunCodeProvenance.dq_policy_ref; contract registry",
        "string ref",
        "Applied DQ policy.",
        "full in contract/DQ details",
        True,
        "DQ contract registry",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P1",
        "rule_bundle_version",
        "Rule Bundle",
        "RunCodeProvenance.rule_bundle_version; contract registry",
        "semver / string",
        "DQ rule bundle version.",
        "full",
        False,
        "DQ rule bundle / migration guide",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P1",
        "dq_contract_compatibility_hash",
        "DQ Compat Hash",
        "RunCodeProvenance.dq_contract_compatibility_hash",
        "sha256 hex",
        "Detects DQ compatibility surface drift.",
        "details only; compact short",
        True,
        "DQ contract diff",
        "WARNING",
    ),
    _AnchorSpec(
        "P1",
        "source_refs",
        "Source Refs",
        "RunManifest.source_refs",
        "array provider/entity/query/input_snapshots",
        "External input lineage closure.",
        "count in summary; full nested table",
        True,
        "Source refs panel",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P1",
        "input_snapshot_ids",
        "Input Snapshot IDs",
        "RunManifest.source_refs[*].input_snapshots[*].snapshot_id",
        "array of opaque ids",
        "Immutable input snapshot list.",
        "details table only",
        True,
        "Input snapshot details",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P1",
        "input_snapshot_content_hashes",
        "Input Snapshot Hashes",
        "RunManifest.source_refs[*].input_snapshots[*].content_hash",
        "array of sha256 hex",
        "Checks input snapshot immutability.",
        "details table only",
        True,
        "Snapshot hash diff",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P1",
        "replay_capability",
        "Replay Capability",
        "RunManifest.replay_capability",
        "enum",
        "Shows reproducibility support.",
        "badge",
        False,
        "Replay diagnostics",
        "WARNING",
    ),
    _AnchorSpec(
        "P1",
        "exact_replay_eligible",
        "Exact Replay Eligible",
        "Derived from manifest anchors",
        "boolean + blockers",
        "Quick exact replay eligibility answer.",
        "badge; blockers in details",
        False,
        "Replay blockers",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P1",
        "resume_contract",
        "Resume Contract",
        "runtime_config/resolved_config resume_contract",
        "object summary",
        "Checkpoint/resume semantics.",
        "details summary",
        False,
        "Checkpoint/resume details",
        "WARNING",
    ),
    _AnchorSpec(
        "P1",
        "lineage_fragment_ids",
        "Lineage Fragments",
        "RunLedger.lineage_fragment_id",
        "array of ids",
        "Lineage closure emitted by run.",
        "details only",
        True,
        "Lineage panel",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P1",
        "artifact_refs",
        "Published Artifact Refs",
        "RunLedger artifact_published details; planned_artifacts",
        "artifact refs / paths",
        "Links identity graph to produced artifacts.",
        "details only",
        True,
        "Artifact details",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P1",
        "latest_event_id",
        "Ledger Watermark",
        "RunLedger latest event",
        "opaque event id",
        "Checkpoint snapshot plus ledger suffix reconstruction anchor.",
        "details only",
        True,
        "Run Ledger event table",
        "INFO",
    ),
    _AnchorSpec(
        "P2",
        "launch_context_hash",
        "Launch Context",
        "RunManifest.launch_context",
        "derived sha256",
        "Audit context for who/how started run.",
        "drilldown only",
        False,
        "Manifest launch_context",
        "INFO",
    ),
    _AnchorSpec(
        "P2",
        "runtime_config_hash",
        "Runtime Config Hash",
        "RunManifest.runtime_config",
        "derived sha256",
        "Debug runtime flag drift.",
        "drilldown only",
        True,
        "Manifest diff",
        "INFO",
    ),
    _AnchorSpec(
        "P2",
        "planned_artifacts",
        "Planned Artifacts",
        "RunManifest.planned_artifacts",
        "layer/path refs",
        "Compare planned outputs with published outputs.",
        "details only",
        True,
        "Artifact table",
        "WARNING",
    ),
    _AnchorSpec(
        "P2",
        "published_artifacts",
        "Published Artifacts",
        "RunLedger artifact_published details",
        "artifact refs / paths",
        "Actual output artifacts.",
        "details only",
        True,
        "Artifact table",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P2",
        "component_run_ids",
        "Composite Component Runs",
        "Composite ledger event details",
        "array of UUIDs",
        "Seed/dependency/enricher run identities for composite.",
        "composite drilldown only",
        True,
        "Component manifest table",
        "DEGRADED",
    ),
    _AnchorSpec(
        "P2",
        "checkpoint_file_id",
        "Checkpoint File",
        "checkpoint metadata path/id",
        "local file name / path",
        "Forensic resume storage debug.",
        "details only; never stat card",
        True,
        "Checkpoint raw view",
        "INFO",
    ),
    _AnchorSpec(
        "P2",
        "lock_owner_id",
        "Lock Owner / Fencing Token",
        "runtime lock metadata",
        "opaque string",
        "Concurrency forensic anchor.",
        "details only",
        True,
        "Runtime locks panel",
        "WARNING",
    ),
    _AnchorSpec(
        "P2",
        "dq_report_paths",
        "DQ Report Paths",
        "RunLedger details/runtime_config",
        "path refs",
        "Open DQ reports without metrics-label pollution.",
        "details only",
        True,
        "DQ report view",
        "INFO",
    ),
    _AnchorSpec(
        "P2",
        "cross_validation_rule_ids",
        "Cross-validation Rules",
        "runtime_config/resolved_config",
        "list of string ids",
        "Composite cross-validation/nullification context.",
        "details only",
        False,
        "Cross-validation details",
        "INFO",
    ),
    _AnchorSpec(
        "P2",
        "bronze_batch_ids",
        "Bronze Batch IDs",
        "source refs / ledger details",
        "UUID/list",
        "Bronze provenance for forensic replay.",
        "details only; never card",
        True,
        "Bronze lineage details",
        "INFO",
    ),
)

_SPEC_BY_NAME = {spec.name: spec for spec in _ANCHOR_SPECS}
_OVERVIEW_NAMES = frozenset(
    {
        "run_id",
        "manifest_id",
        "pipeline_name",
        "provider_entity",
        "runtime_mode",
        "execution_fingerprint",
        "effective_config_hash",
        "contract_ref",
        "contract_version",
        "input_snapshot_identity_fingerprint",
        "replay_capability",
        "replay_mode",
        "checkpoint_anchor_status",
        "composite_run_identity",
        "identity_graph_complete",
    }
)


def build_control_plane_identity_evidence_payload(
    *,
    requested_pipeline: str,
    resolved_manifest: RunManifest | None,
    selected_pipelines: tuple[str, ...],
    selected_run_id: str | None,
    selected_run_types: tuple[str, ...],
    resolved_via: str,
    ledger_port: _LedgerEntryProvider | None,
    view: str = "anchors",
    priority: str | None = None,
) -> dict[str, object]:
    """Build the dedicated Control Plane identity evidence payload."""
    ledger_entries = _ledger_entries_for(resolved_manifest, ledger_port)
    checkpoint_compare = _build_checkpoint_compare(resolved_manifest)
    values = _build_anchor_values(
        resolved_manifest,
        ledger_entries=ledger_entries,
        checkpoint_status=str(checkpoint_compare["status"]),
    )
    anchors = _build_anchor_rows(
        manifest=resolved_manifest,
        ledger_entries=ledger_entries,
        values=values,
        checkpoint_status=str(checkpoint_compare["status"]),
    )
    summary = _build_summary(
        manifest=resolved_manifest,
        anchors=anchors,
        checkpoint_status=str(checkpoint_compare["status"]),
        resolved_via=resolved_via,
    )
    rows = _select_rows(
        view=view,
        priority=priority,
        anchors=anchors,
        checkpoint_rows=checkpoint_compare["rows"],
    )
    return {
        "contract": IDENTITY_EVIDENCE_CONTRACT,
        "pipeline": requested_pipeline,
        "run_type": list(selected_run_types),
        "selected_run_id": selected_run_id,
        "resolved_via": resolved_via,
        "summary": summary,
        "anchors": anchors,
        "checkpoint_compare": checkpoint_compare,
        "rows": rows,
        "forbidden_prometheus_label_policy": {
            "high_cardinality_ids_must_not_be_labels": True,
            "allowed_low_cardinality_labels": [
                "pipeline",
                "run_type",
                "status",
                "layer",
                "event_type",
                "disposition",
                "ref_type",
                "decision_type",
                "selected_source",
            ],
        },
        "scope": {
            "selected_pipelines": list(selected_pipelines),
            "aggregate_scope_requires_exact_run_id": (
                resolved_via == "aggregate_scope_requires_exact_run_id"
            ),
        },
    }


def _ledger_entries_for(
    manifest: RunManifest | None,
    ledger_port: _LedgerEntryProvider | None,
) -> tuple[RunLedgerEntry, ...]:
    if manifest is None or ledger_port is None:
        return ()
    return tuple(ledger_port.list_entries(manifest.manifest_id))


def _build_anchor_rows(
    *,
    manifest: RunManifest | None,
    ledger_entries: tuple[RunLedgerEntry, ...],
    values: dict[str, object | None],
    checkpoint_status: str,
) -> list[dict[str, object]]:
    rows = [
        _build_anchor_row(
            spec,
            value=values.get(spec.name),
            manifest=manifest,
            ledger_entries=ledger_entries,
            checkpoint_status=checkpoint_status,
        )
        for spec in _ANCHOR_SPECS
    ]
    gap_count = sum(1 for row in rows if row["identity_gap"] is True)
    graph_status = "complete" if gap_count == 0 else f"incomplete ({gap_count} gaps)"
    return [
        graph_status_row if row["name"] == "identity_graph_complete" else row
        for row in rows
        for graph_status_row in (
            _build_anchor_row(
                _SPEC_BY_NAME["identity_graph_complete"],
                value=graph_status,
                manifest=manifest,
                ledger_entries=ledger_entries,
                checkpoint_status=checkpoint_status,
            ),
        )
    ]


def _build_anchor_row(
    spec: _AnchorSpec,
    *,
    value: object | None,
    manifest: RunManifest | None,
    ledger_entries: tuple[RunLedgerEntry, ...],
    checkpoint_status: str,
) -> dict[str, object]:
    applicability = _applicability(spec.name, manifest)
    applicable = applicability == "APPLICABLE"
    present = _is_present(value)
    domain_severity = _domain_severity(
        spec,
        value=value,
        present=present,
        manifest=manifest,
        ledger_entries=ledger_entries,
        checkpoint_status=checkpoint_status,
        applicable=applicable,
    )
    ui_status = _ui_status(domain_severity)
    missing_text = "missing" if applicable else applicability
    value_full = _format_full_value(value) if present else missing_text
    copy_enabled = bool(spec.copy and present and applicable)
    return {
        "priority": spec.priority,
        "name": spec.name,
        "label": spec.label,
        "source": spec.source,
        "format": spec.value_format,
        "why": spec.why,
        "rendering": spec.rendering,
        "value_short": _short_value(value) if present else applicability,
        "value_full": value_full,
        "copy": copy_enabled,
        "copy_mode": "full_value" if copy_enabled else "none",
        "copy_value": value_full if copy_enabled else "",
        "drilldown": spec.drilldown,
        "missing_severity": domain_severity,
        "ui_status": ui_status,
        "identity_gap": _is_identity_gap(domain_severity),
        "present": present,
        "status": ui_status,
    }


def _build_anchor_values(
    manifest: RunManifest | None,
    *,
    ledger_entries: tuple[RunLedgerEntry, ...],
    checkpoint_status: str,
) -> dict[str, object | None]:
    if manifest is None:
        return {}
    code = manifest.code_provenance
    input_snapshots = _input_snapshots(manifest)
    return {
        "run_id": str(manifest.run_id),
        "manifest_id": manifest.manifest_id,
        "pipeline_name": manifest.pipeline_name,
        "provider_entity": _join_non_empty((manifest.provider, manifest.entity), "."),
        "runtime_mode": _runtime_mode(manifest),
        "execution_fingerprint": manifest.execution_fingerprint,
        "git_commit": code.git_commit,
        "pipeline_version": code.pipeline_version,
        "effective_config_hash": code.effective_config_hash,
        "effective_config_artifact_id": code.effective_config_artifact_id,
        "contract_ref": code.contract_ref,
        "contract_version": code.contract_version,
        "contract_schema_hash": code.contract_schema_hash,
        "input_snapshot_identity_fingerprint": _input_snapshot_fingerprint(
            input_snapshots
        ),
        "input_snapshot_count": len(input_snapshots) if input_snapshots else None,
        "replay_mode": _replay_mode(manifest),
        "replay_of_run_id": manifest.replay_of_run_id,
        "replay_of_manifest_id": manifest.replay_of_manifest_id,
        "checkpoint_anchor_status": checkpoint_status,
        "composite_run_identity": _composite_run_identity(manifest),
        "config_hash": code.config_hash,
        "dq_policy_ref": code.dq_policy_ref,
        "rule_bundle_version": code.rule_bundle_version,
        "dq_contract_compatibility_hash": code.dq_contract_compatibility_hash,
        "source_refs": _source_ref_values(manifest.source_refs),
        "input_snapshot_ids": [item.snapshot_id for item in input_snapshots],
        "input_snapshot_content_hashes": [
            item.content_hash for item in input_snapshots
        ],
        "replay_capability": manifest.replay_capability.value,
        "exact_replay_eligible": _exact_replay_eligible(manifest, input_snapshots),
        "resume_contract": _first_payload_value(
            manifest,
            "resume_contract",
            "checkpoint_resume_contract",
        ),
        "lineage_fragment_ids": _lineage_fragment_ids(ledger_entries),
        "artifact_refs": _artifact_refs(manifest, ledger_entries),
        "latest_event_id": ledger_entries[-1].entry_id if ledger_entries else None,
        "launch_context_hash": _stable_hash(manifest.launch_context),
        "runtime_config_hash": _stable_hash(manifest.runtime_config),
        "planned_artifacts": _artifact_ref_values(manifest.planned_artifacts),
        "published_artifacts": _published_artifacts(ledger_entries),
        "component_run_ids": _component_run_ids(ledger_entries),
        "checkpoint_file_id": _checkpoint_value(
            manifest, "checkpoint_file_id", "checkpoint_path"
        ),
        "lock_owner_id": _first_payload_value(
            manifest, "lock_owner_id", "fencing_token"
        ),
        "dq_report_paths": _dq_report_paths(manifest, ledger_entries),
        "cross_validation_rule_ids": _first_payload_value(
            manifest,
            "cross_validation_rule_ids",
            "cross_validation_rules",
        ),
        "bronze_batch_ids": _bronze_batch_ids(manifest, ledger_entries),
    }


def _build_summary(
    *,
    manifest: RunManifest | None,
    anchors: list[dict[str, object]],
    checkpoint_status: str,
    resolved_via: str,
) -> dict[str, object]:
    gap_rows = [row for row in anchors if row["identity_gap"] is True]
    critical = any(row["ui_status"] == "CRIT" for row in gap_rows)
    warning = any(row["ui_status"] == "WARN" for row in gap_rows)
    overall = "CRIT" if critical else "WARN" if warning else "OK"
    if manifest is None:
        overall = "UNKNOWN"
    return {
        "overall_status": overall,
        "identity_graph_complete": not gap_rows and manifest is not None,
        "identity_gap_count": len(gap_rows),
        "checkpoint_anchor_status": checkpoint_status,
        "replay_mode": None if manifest is None else _replay_mode(manifest),
        "resolved_via": resolved_via,
    }


def _build_checkpoint_compare(manifest: RunManifest | None) -> dict[str, object]:
    if manifest is None:
        return {"status": "UNKNOWN", "rows": []}
    current = _current_checkpoint_anchors(manifest)
    checkpoint = _checkpoint_anchor_payload(manifest)
    if not checkpoint:
        return {
            "status": "MISSING",
            "rows": [
                _checkpoint_row(name, current.get(name), None, "MISSING")
                for name in _CHECKPOINT_ANCHORS
                if _is_present(current.get(name))
            ],
        }
    rows: list[dict[str, object]] = []
    statuses: list[str] = []
    for name in _CHECKPOINT_ANCHORS:
        current_value = current.get(name)
        checkpoint_value = checkpoint.get(name)
        status = _checkpoint_pair_status(current_value, checkpoint_value)
        statuses.append(status)
        rows.append(_checkpoint_row(name, current_value, checkpoint_value, status))
    if "MISMATCH" in statuses:
        status = "MISMATCH"
    elif "MISSING" in statuses and "OK" in statuses:
        status = "PARTIAL"
    elif all(item == "MISSING" for item in statuses):
        status = "MISSING"
    elif all(item in {"OK", "N/A"} for item in statuses):
        status = "OK"
    else:
        status = "PARTIAL"
    return {"status": status, "rows": rows}


def _checkpoint_row(
    name: str,
    current_value: object | None,
    checkpoint_value: object | None,
    status: str,
) -> dict[str, object]:
    return {
        "anchor": name,
        "current_value_short": _short_value(current_value),
        "current_value_full": _format_full_value(current_value),
        "checkpoint_value_short": _short_value(checkpoint_value),
        "checkpoint_value_full": _format_full_value(checkpoint_value),
        "status": status,
        "ui_status": {
            "OK": "OK",
            "MISMATCH": "CRIT",
            "MISSING": "WARN",
            "N/A": "OK",
        }.get(
            status,
            "WARN",
        ),
    }


def _current_checkpoint_anchors(manifest: RunManifest) -> dict[str, object | None]:
    input_snapshots = _input_snapshots(manifest)
    return {
        "manifest_id": manifest.manifest_id,
        "execution_fingerprint": manifest.execution_fingerprint,
        "effective_config_hash": manifest.code_provenance.effective_config_hash,
        "effective_config_artifact_id": (
            manifest.code_provenance.effective_config_artifact_id
        ),
        "input_snapshot_fingerprint": _input_snapshot_fingerprint(input_snapshots),
        "composite_run_identity": _composite_run_identity(manifest),
    }


def _checkpoint_pair_status(
    current_value: object | None,
    checkpoint_value: object | None,
) -> str:
    if not _is_present(current_value) and not _is_present(checkpoint_value):
        return "N/A"
    if not _is_present(current_value) or not _is_present(checkpoint_value):
        return "MISSING"
    return "OK" if current_value == checkpoint_value else "MISMATCH"


def _select_rows(
    *,
    view: str,
    priority: str | None,
    anchors: list[dict[str, object]],
    checkpoint_rows: object,
) -> list[dict[str, object]]:
    normalized_view = view.strip().lower()
    selected = anchors
    if normalized_view == "overview":
        selected = [row for row in anchors if row["name"] in _OVERVIEW_NAMES]
    elif normalized_view == "gaps":
        selected = [row for row in anchors if row["identity_gap"] is True]
    elif normalized_view == "copy_values":
        selected = [row for row in anchors if row["copy"] is True]
    elif normalized_view == "checkpoint_compare":
        return list(checkpoint_rows) if isinstance(checkpoint_rows, list) else []
    if priority:
        selected = [row for row in selected if row["priority"] == priority.upper()]
    return selected


def _domain_severity(
    spec: _AnchorSpec,
    *,
    value: object | None,
    present: bool,
    manifest: RunManifest | None,
    ledger_entries: tuple[RunLedgerEntry, ...],
    checkpoint_status: str,
    applicable: bool,
) -> str:
    if not applicable:
        return "N/A"
    if spec.name == "checkpoint_anchor_status":
        return {"OK": "OK", "MISMATCH": "FAILING", "MISSING": "DEGRADED"}.get(
            checkpoint_status,
            "DEGRADED",
        )
    if (
        spec.name == "exact_replay_eligible"
        and manifest is not None
        and _requested_exact_replay(manifest)
        and value is False
    ):
        return "FAILING"
    if present:
        return "OK"
    if spec.name == "manifest_id":
        return "FAILING" if _is_terminal(ledger_entries) else "DEGRADED"
    if (
        spec.name
        in {
            "effective_config_hash",
            "input_snapshot_identity_fingerprint",
            "input_snapshot_ids",
            "input_snapshot_content_hashes",
        }
        and manifest is not None
        and _requested_exact_replay(manifest)
    ):
        return "FAILING"
    return spec.missing_severity


def _ui_status(domain_severity: str) -> str:
    if domain_severity == "FAILING":
        return "CRIT"
    if domain_severity in {"DEGRADED", "WARNING"}:
        return "WARN"
    return "OK"


def _is_identity_gap(domain_severity: str) -> bool:
    return domain_severity in {"FAILING", "DEGRADED", "WARNING"}


def _applicability(name: str, manifest: RunManifest | None) -> str:
    if manifest is None:
        return "not available for current scope"
    if name in {"replay_of_run_id", "replay_of_manifest_id"} and not _is_replay(
        manifest
    ):
        return "N/A"
    if name in {
        "composite_run_identity",
        "component_run_ids",
        "cross_validation_rule_ids",
    }:
        return "N/A" if not _is_composite(manifest) else "APPLICABLE"
    return "APPLICABLE"


def _is_replay(manifest: RunManifest) -> bool:
    return (
        bool(manifest.replay_of_run_id)
        or bool(manifest.replay_of_manifest_id)
        or _requested_exact_replay(manifest)
    )


def _is_composite(manifest: RunManifest) -> bool:
    return (
        manifest.pipeline_name.startswith("composite_")
        or manifest.provider == "composite"
        or bool(_composite_run_identity(manifest))
    )


def _is_terminal(ledger_entries: tuple[RunLedgerEntry, ...]) -> bool:
    return any(
        str(entry.status or "").lower() in _TERMINAL_STATUSES
        for entry in ledger_entries
    )


def _runtime_mode(manifest: RunManifest) -> str:
    flags = []
    for name in (
        "execution_context",
        "resume",
        "dry_run",
        "exact_replay",
        "use_cached_bronze",
    ):
        value = _first_payload_value(manifest, name)
        if value not in (None, False, "", [], {}):
            flags.append(f"{name}={value}")
    return " | ".join([manifest.run_type.value, *flags])


def _replay_mode(manifest: RunManifest) -> str:
    if _requested_exact_replay(manifest):
        return "exact_replay"
    if manifest.replay_of_run_id or manifest.replay_of_manifest_id:
        return "replay"
    return manifest.run_type.value


def _exact_replay_eligible(
    manifest: RunManifest,
    input_snapshots: tuple[RunInputSnapshotRef, ...],
) -> bool:
    code = manifest.code_provenance
    required = (
        manifest.execution_fingerprint,
        code.effective_config_hash,
        code.effective_config_artifact_id,
        _input_snapshot_fingerprint(input_snapshots),
    )
    return all(_is_present(item) for item in required)


def _requested_exact_replay(manifest: RunManifest) -> bool:
    value = _first_payload_value(manifest, "exact_replay", "requested_exact_replay")
    return value is True or str(value).strip().lower() == "true"


def _input_snapshots(manifest: RunManifest) -> tuple[RunInputSnapshotRef, ...]:
    snapshots: list[RunInputSnapshotRef] = []
    for source_ref in manifest.source_refs:
        snapshots.extend(source_ref.input_snapshots)
    return tuple(snapshots)


def _input_snapshot_fingerprint(
    snapshots: tuple[RunInputSnapshotRef, ...],
) -> str | None:
    if not snapshots:
        return None
    payload = [
        {
            "snapshot_id": item.snapshot_id,
            "content_hash": item.content_hash,
            "immutable_uri": item.immutable_uri,
            "query_fingerprint": item.query_fingerprint,
        }
        for item in snapshots
    ]
    return compute_input_snapshot_identity_fingerprint(payload)


def _source_ref_values(source_refs: Sequence[RunSourceRef]) -> list[str]:
    return [
        _join_non_empty((item.provider, item.entity, item.pipeline_name), "/")
        for item in source_refs
    ]


def _artifact_ref_values(artifacts: Sequence[RunArtifactRef]) -> list[str]:
    return [_join_non_empty((item.layer, item.path), ":") for item in artifacts]


def _artifact_refs(
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> list[str]:
    values = _published_artifacts(ledger_entries)
    if values:
        return values
    return _artifact_ref_values(manifest.planned_artifacts)


def _published_artifacts(ledger_entries: tuple[RunLedgerEntry, ...]) -> list[str]:
    values: list[str] = []
    for entry in ledger_entries:
        details = entry.details or {}
        for key in ("artifact_ref", "artifact_path", "path", "uri"):
            _append_value(values, details.get(key))
    return _dedupe(values)


def _lineage_fragment_ids(ledger_entries: tuple[RunLedgerEntry, ...]) -> list[str]:
    return _dedupe(
        [
            entry.lineage_fragment_id
            for entry in ledger_entries
            if entry.lineage_fragment_id
        ]
    )


def _component_run_ids(ledger_entries: tuple[RunLedgerEntry, ...]) -> list[str]:
    values: list[str] = []
    for entry in ledger_entries:
        if entry.event_type not in _COMPOSITE_EVENTS:
            continue
        details = entry.details or {}
        for key in ("component_run_id", "child_run_id", "upstream_run_id", "run_id"):
            _append_value(values, details.get(key))
        _append_value(values, details.get("component_run_ids"))
    return _dedupe(values)


def _dq_report_paths(
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> list[str]:
    values: list[str] = []
    _append_value(
        values, _first_payload_value(manifest, "dq_report_paths", "dq_report_path")
    )
    for entry in ledger_entries:
        details = entry.details or {}
        _append_value(values, details.get("dq_report_paths"))
        _append_value(values, details.get("dq_report_path"))
    return _dedupe(values)


def _bronze_batch_ids(
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> list[str]:
    values = [item.snapshot_id for item in _input_snapshots(manifest)]
    for entry in ledger_entries:
        details = entry.details or {}
        for key in ("bronze_batch_id", "bronze_batch_ids", "source_batch_ids"):
            _append_value(values, details.get(key))
    return _dedupe(values)


def _checkpoint_anchor_payload(manifest: RunManifest) -> dict[str, object]:
    for payload in (
        manifest.runtime_config,
        manifest.resolved_config,
        manifest.launch_context,
    ):
        checkpoint = _mapping_value(
            payload,
            "checkpoint_metadata",
            "checkpoint_anchors",
            "persisted_checkpoint_anchors",
        )
        if checkpoint:
            return dict(checkpoint)
    reproducibility = _mapping_value(
        manifest.resolved_config,
        "reproducibility_diagnostics",
        "reproducibility",
    )
    if reproducibility:
        checkpoint = _mapping_value(reproducibility, "checkpoint_anchors")
        if checkpoint:
            persisted = _mapping_value(
                checkpoint,
                "checkpoint",
                "persisted_checkpoint_anchors",
            )
            return dict(persisted or checkpoint)
    return {}


def _checkpoint_value(manifest: RunManifest, *keys: str) -> object | None:
    checkpoint = _checkpoint_anchor_payload(manifest)
    for key in keys:
        value = checkpoint.get(key)
        if _is_present(value):
            return value
    return _first_payload_value(manifest, *keys)


def _composite_run_identity(manifest: RunManifest) -> object | None:
    return _checkpoint_value(manifest, "composite_run_identity")


def _first_payload_value(manifest: RunManifest, *keys: str) -> object | None:
    for payload in (
        manifest.runtime_config,
        manifest.launch_context,
        manifest.resolved_config,
    ):
        for key in keys:
            value = payload.get(key)
            if _is_present(value):
                return value
    return None


def _mapping_value(mapping: Mapping[str, object], *keys: str) -> Mapping[str, object]:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def _stable_hash(value: object) -> str | None:
    if not _is_present(value):
        return None
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _short_value(value: object | None) -> str:
    full = _format_full_value(value)
    if not full:
        return ""
    if "," in full:
        return f"{len([item for item in full.split(',') if item.strip()])} items"
    return full if len(full) <= 12 else full[:12]


def _format_full_value(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list | tuple | set):
        return ", ".join(str(item) for item in value if _is_present(item))
    if isinstance(value, Mapping):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value).strip()


def _is_present(value: object | None) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() not in {"none", "null"}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return bool(value)
    if isinstance(value, Mapping):
        return bool(value)
    return True


def _append_value(values: list[str], raw_value: object) -> None:
    if raw_value is None:
        return
    if isinstance(raw_value, list | tuple | set):
        for item in raw_value:
            _append_value(values, item)
        return
    text = str(raw_value).strip()
    if text:
        values.append(text)


def _dedupe(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _join_non_empty(values: Iterable[object | None], separator: str) -> str | None:
    parts = [str(value).strip() for value in values if str(value or "").strip()]
    return separator.join(parts) if parts else None
