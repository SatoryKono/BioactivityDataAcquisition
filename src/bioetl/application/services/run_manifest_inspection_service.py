"""Application service for inspecting run manifests and ledger history."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from uuid import UUID

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.ports import RunLedgerPort, RunManifestPort
from bioetl.domain.types import RunID

__all__ = [
    "RunManifestDiffEntry",
    "RunManifestDiffResult",
    "RunManifestInspectionResult",
    "RunManifestInspectionService",
]


@dataclass(frozen=True, slots=True)
class RunManifestInspectionResult:
    """Resolved control-plane view for one manifest and its ledger history."""

    manifest: RunManifest
    ledger_entries: tuple[RunLedgerEntry, ...] = ()
    diagnostics: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return JSON/YAML-safe payload for CLI presentation."""
        return {
            "manifest": self.manifest.to_dict(),
            "ledger_entries": [entry.to_dict() for entry in self.ledger_entries],
            "diagnostics": self.diagnostics,
        }


@dataclass(frozen=True, slots=True)
class RunManifestDiffEntry:
    """One top-level manifest field difference."""

    field: str
    left: object
    right: object

    def to_dict(self) -> dict[str, object]:
        """Return JSON/YAML-safe payload for CLI presentation."""
        return {
            "field": self.field,
            "left": self.left,
            "right": self.right,
        }


@dataclass(frozen=True, slots=True)
class RunManifestDiffResult:
    """Top-level diff between two resolved manifests."""

    left_manifest_id: str
    right_manifest_id: str
    differences: tuple[RunManifestDiffEntry, ...]

    def to_dict(self) -> dict[str, object]:
        """Return JSON/YAML-safe payload for CLI presentation."""
        return {
            "left_manifest_id": self.left_manifest_id,
            "right_manifest_id": self.right_manifest_id,
            "differences": [entry.to_dict() for entry in self.differences],
        }


@dataclass(slots=True)
class RunManifestInspectionService:
    """Resolve run manifests and compute CLI-facing diffs."""

    manifest_port: RunManifestPort
    ledger_port: RunLedgerPort | None = None

    def show(self, identifier: str) -> RunManifestInspectionResult:
        """Resolve one manifest by manifest_id or run_id."""
        manifest = self._resolve_manifest(identifier)
        ledger_entries: tuple[RunLedgerEntry, ...] = ()
        if self.ledger_port is not None:
            ledger_entries = tuple(self.ledger_port.list_entries(manifest.manifest_id))
        diagnostics = _build_diagnostics_summary(manifest, ledger_entries)
        return RunManifestInspectionResult(
            manifest=manifest,
            ledger_entries=ledger_entries,
            diagnostics=diagnostics,
        )

    def diff(
        self, left_identifier: str, right_identifier: str
    ) -> RunManifestDiffResult:
        """Compute a stable top-level diff between two manifests."""
        left_manifest = self._resolve_manifest(left_identifier)
        right_manifest = self._resolve_manifest(right_identifier)
        left_payload = left_manifest.to_dict()
        right_payload = right_manifest.to_dict()
        diff_fields = tuple(
            RunManifestDiffEntry(
                field=field,
                left=left_payload.get(field),
                right=right_payload.get(field),
            )
            for field in sorted(set(left_payload) | set(right_payload))
            if not self._json_equal(left_payload.get(field), right_payload.get(field))
        )
        return RunManifestDiffResult(
            left_manifest_id=left_manifest.manifest_id,
            right_manifest_id=right_manifest.manifest_id,
            differences=diff_fields,
        )

    def _resolve_manifest(self, identifier: str) -> RunManifest:
        """Resolve manifest_id first, then run_id lookup when identifier is UUID-like."""
        manifest = self.manifest_port.get(identifier)
        if manifest is not None:
            return manifest
        run_id = self._parse_run_id(identifier)
        if run_id is not None:
            manifest = self.manifest_port.get_by_run_id(run_id)
            if manifest is not None:
                return manifest
        raise ValueError(f"Run manifest not found for identifier: {identifier}")

    @staticmethod
    def _parse_run_id(identifier: str) -> RunID | None:
        """Parse UUID-like run identifiers safely."""
        try:
            return RunID(UUID(identifier))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _json_equal(left: object, right: object) -> bool:
        """Compare nested payloads using canonical JSON normalization."""
        return json.dumps(left, sort_keys=True, default=str) == json.dumps(
            right,
            sort_keys=True,
            default=str,
        )


def _build_diagnostics_summary(
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, object]:
    """Build compact operator-oriented diagnostics summary."""
    code_provenance = manifest.code_provenance
    summary: dict[str, object] = {
        "execution_fingerprint": manifest.execution_fingerprint,
        "config_hash": code_provenance.config_hash,
        "contract_ref": code_provenance.contract_ref,
        "contract_version": code_provenance.contract_version,
        "dq_policy_ref": code_provenance.dq_policy_ref,
        "rule_bundle_version": code_provenance.rule_bundle_version,
        "dq_contract_compatibility_hash": (
            code_provenance.dq_contract_compatibility_hash
        ),
        "effective_config_artifact_id": code_provenance.effective_config_artifact_id,
    }
    if not ledger_entries:
        return summary

    family_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    artifact_refs: list[dict[str, object]] = []
    lineage_fragment_ids: set[str] = set()
    dq_rule_ids: set[str] = set()
    dq_dispositions: set[str] = set()
    dq_report_paths: set[str] = set()
    dq_signal_present = False
    missing_link_count = 0
    for entry in ledger_entries:
        family_counter.update([entry.event_family or "diagnostic"])
        type_counter.update([entry.event_type])
        artifact_ref = _build_artifact_ref(entry)
        if artifact_ref is not None:
            artifact_refs.append(artifact_ref)
            if (
                artifact_ref.get("dataset_ref") is None
                and artifact_ref.get("lineage_fragment_id") is None
            ):
                missing_link_count += 1
        if entry.lineage_fragment_id:
            lineage_fragment_ids.add(entry.lineage_fragment_id)
        dq_details = _extract_dq_details(entry)
        dq_rule_ids.update(dq_details["rule_ids"])
        dq_dispositions.update(dq_details["dispositions"])
        dq_report_paths.update(dq_details["report_paths"])
        dq_signal_present = dq_signal_present or dq_details["has_signal"]

    latest_entry = ledger_entries[-1]
    alert_signals = _build_alert_signals(
        latest_status=latest_entry.status,
        artifact_refs=artifact_refs,
        lineage_fragment_ids=lineage_fragment_ids,
        missing_link_count=missing_link_count,
        dq_signal_present=dq_signal_present,
    )
    next_steps = _build_next_steps(alert_signals)
    summary.update(
        {
        "total_events": len(ledger_entries),
        "latest_event_type": latest_entry.event_type,
        "latest_status": latest_entry.status,
        "event_family_counts": dict(sorted(family_counter.items())),
        "event_type_counts": dict(sorted(type_counter.items())),
        "artifact_refs": artifact_refs,
        "lineage_fragment_ids": sorted(lineage_fragment_ids),
        "missing_artifact_links": missing_link_count,
        "dq_rule_ids": sorted(dq_rule_ids),
        "dq_dispositions": sorted(dq_dispositions),
        "dq_report_paths": sorted(dq_report_paths),
        "alert_signals": alert_signals,
        "next_steps": next_steps,
        }
    )
    return summary


def _build_artifact_ref(entry: RunLedgerEntry) -> dict[str, object] | None:
    if entry.event_family != "artifact" and entry.event_type != "artifact_published":
        return None
    details = entry.details or {}
    artifact_path = details.get("artifact_path")
    return {
        "event_type": entry.event_type,
        "stage": entry.stage,
        "dataset_ref": entry.dataset_ref,
        "lineage_fragment_id": entry.lineage_fragment_id,
        "artifact_path": None if artifact_path is None else str(artifact_path),
    }


def _build_alert_signals(
    *,
    latest_status: str | None,
    artifact_refs: list[dict[str, object]],
    lineage_fragment_ids: set[str],
    missing_link_count: int,
    dq_signal_present: bool,
) -> dict[str, bool]:
    """Map diagnostics summary to alert-oriented boolean signals."""
    latest_status_normalized = (latest_status or "").strip().lower()
    artifact_ref_count = len(artifact_refs)
    has_artifact_refs = artifact_ref_count > 0
    return {
        "run_failed": latest_status_normalized == "failed",
        "run_shutdown": latest_status_normalized == "shutdown",
        "artifact_linkage_gap": missing_link_count > 0,
        "lineage_gap": has_artifact_refs and not lineage_fragment_ids,
        "dq_signal_present": dq_signal_present,
    }


def _build_next_steps(alert_signals: dict[str, bool]) -> list[str]:
    """Return operator-oriented next steps based on active alert signals."""
    steps: list[str] = []
    if alert_signals.get("run_failed", False):
        steps.append(
            "Inspect failure classification and decide retry/quarantine/escalation."
        )
    if alert_signals.get("artifact_linkage_gap", False):
        steps.append(
            "Validate artifact publication metadata and repair dataset/lineage links."
        )
    if alert_signals.get("lineage_gap", False):
        steps.append(
            "Investigate lineage persistence for published artifacts before restart."
        )
    if alert_signals.get("dq_signal_present", False):
        steps.append(
            "Review DQ report artifacts, rule IDs, and contract policy anchors before retry or escalation."
        )
    if alert_signals.get("run_shutdown", False):
        steps.append(
            "Confirm graceful shutdown reason and resume policy compatibility."
        )
    if not steps:
        steps.append("No alert signals detected; continue routine monitoring.")
    return steps


def _extract_dq_details(entry: RunLedgerEntry) -> dict[str, object]:
    """Extract DQ-oriented anchors from one ledger entry."""
    details = entry.details or {}
    rule_ids: set[str] = set()
    dispositions: set[str] = set()
    report_paths: set[str] = set()

    single_rule_id = details.get("rule_id")
    if single_rule_id is not None:
        rule_ids.add(str(single_rule_id))
    rule_ids.update(_load_str_collection(details.get("dq_rule_ids")))
    rule_ids.update(_load_str_collection(details.get("rule_ids")))

    single_disposition = details.get("disposition")
    if single_disposition is not None:
        dispositions.add(str(single_disposition))
    dispositions.update(_load_str_collection(details.get("dq_dispositions")))
    dispositions.update(_load_str_collection(details.get("dispositions")))

    dq_report_path = details.get("dq_report_path")
    if dq_report_path is not None:
        report_paths.add(str(dq_report_path))

    has_signal = (
        entry.event_family == "dq"
        or entry.event_type.startswith("dq_")
        or bool(rule_ids)
        or bool(dispositions)
        or bool(report_paths)
    )
    return {
        "rule_ids": rule_ids,
        "dispositions": dispositions,
        "report_paths": report_paths,
        "has_signal": has_signal,
    }


def _load_str_collection(raw_value: object) -> set[str]:
    """Normalize list-like diagnostic payloads into string sets."""
    if not isinstance(raw_value, list):
        return set()
    return {str(item) for item in raw_value}
