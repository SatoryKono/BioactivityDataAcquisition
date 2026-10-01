"""Frozen-report assessment loaders for the exact-run status projection."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from uuid import UUID

from bioetl.application.observability.reason_aliases import display_reasons_text
from bioetl.application.services.control_plane.manifest.diagnostics.selected_run_replay_readiness import (
    INSUFFICIENT,
)
from bioetl.application.services.run_reports.query import list_pipeline_reports
from bioetl.composition.observability_runtime import create_run_report_store
from bioetl.domain.run_reports.selected_status import (
    assess_report,
    evidence_digest,
    verify_snapshot,
)
from bioetl.interfaces.http import run_report_ops
from bioetl.interfaces.http._selected_run_live import pipeline_owners

_REPORT_SCHEMAS = {"pipeline_run_report_v1", "pipeline_run_report_v2"}

_CONTROL_PLANE = "Control Plane"


class _RevisionMissingError(LookupError):
    """Selected-run snapshot revision file is absent after identity checks."""


class _IdentityMismatchError(LookupError):
    """Persisted report identity does not match the requested pipeline/run."""


def _accounting_conflicts(reconciliation: object, verdict: object) -> list[str]:
    if not isinstance(reconciliation, dict):
        return []
    conflicts: list[str] = []
    for stage in ("silver", "gold"):
        prior = "bronze" if stage == "silver" else "silver"
        key = f"{stage}_vs_{prior}_status"
        if reconciliation.get(key) == "FAILING":
            conflicts.append(
                f"Saved report accounting conflict: {key}=FAILING, "
                f"delta={reconciliation.get(f'{stage}_delta', 'UNKNOWN')}. "
                f"Saved Trust verdict: {verdict}; inspect report and ledger."
            )
    return conflicts


def _saved_trust(
    report: dict[str, object], summary: dict[str, object], rows: list[dict[str, object]]
) -> dict[str, object]:
    """Project Trust from the same frozen inputs as the six-domain summary."""
    control = next(row for row in rows if row["domain"] == _CONTROL_PLANE)
    reasons: object = report
    for key in (
        "observations",
        _CONTROL_PLANE,
        "facts",
        "checks",
        "trust",
        "reasons_text",
    ):
        reasons = reasons.get(key) if isinstance(reasons, dict) else None
    reasons_text = reasons if isinstance(reasons, str) else str(control["reason"])
    conflicts = _accounting_conflicts(report.get("reconciliation"), control["verdict"])
    if conflicts:
        reasons_text = "\n".join(filter(None, (reasons_text, *conflicts)))
    reasons_count = sum(bool(line.strip()) for line in reasons_text.splitlines())
    return {
        "processing_status": str(summary["execution_state"]).lower(),
        "trust_status": "ERROR" if conflicts else control["verdict"],
        "saved_trust_status": control["verdict"],
        "accounting_integrity": "CONFLICT" if conflicts else "NO REPORTED CONFLICT",
        "reasons_text": reasons_text,
        "reasons_display": display_reasons_text(reasons_text),
        "reasons_count": reasons_count,
        "trust_reasons_action": "View trust reasons" if reasons_count > 0 else None,
        "evidence_observed_at": summary["evaluation_at"],
        "pipeline": summary["pipeline"],
        "run_id": summary["run_id"],
        "rules_version": summary["rules_version"],
        "revision": summary["revision"],
        "replay_readiness_now": summary.get("replay_readiness_now", INSUFFICIENT),
    }


def _selected_pipeline(pipeline: str, run_id: str, root: Path | None) -> str | None:
    """Resolve an aggregate selector only from an unambiguous exact report path."""
    owners = pipeline_owners(pipeline)
    if owners is not None and len(owners) == 1:
        return next(iter(owners))
    if run_report_ops._safe_segment(run_id) != run_id:
        raise ValueError("invalid_run_id")
    base = run_report_ops._effective_root(root)
    entries = list_pipeline_reports(
        pipeline_name=None,
        limit=None,
        root=base,
        store=create_run_report_store(),
    )
    matches = [
        entry.owner
        for entry in entries
        if entry.run_id == run_id and (owners is None or entry.owner in owners)
    ]
    if len(matches) > 1:
        raise ValueError("run_id_ambiguous")
    return matches[0] if matches else None


def _legacy_assessment(report: dict[str, object]) -> tuple[dict[str, object], str, str]:
    assessment = assess_report(report)
    assessment["evidence_completeness"] = "INCOMPLETE"
    if assessment["verdict"] in {"OK", "N/A"}:
        assessment["verdict"] = "INCOMPLETE"
    return assessment, "legacy_no_snapshot", evidence_digest(report)


def _snapshot_assessment(
    report: dict[str, object], snapshot: dict[str, object], path: Path
) -> tuple[dict[str, object], str, str]:
    if not verify_snapshot(snapshot):
        raise ValueError("snapshot_corrupt_or_rules_unsupported")
    evidence = {
        key: value for key, value in report.items() if key != "selected_run_snapshot"
    }
    if snapshot.get("evidence") != evidence:
        raise ValueError("snapshot_evidence_mismatch")
    revision = str(snapshot["revision"])
    revision_path = path.parent / "status-revisions" / f"{revision}.json"
    if not revision_path.resolve().is_relative_to(path.parent.resolve()):
        raise ValueError("revision_outside_selected_run")
    if not revision_path.is_file():
        raise _RevisionMissingError("revision_missing")
    if json.loads(revision_path.read_text(encoding="utf-8")) != snapshot:
        raise ValueError("revision_corrupt")
    assessment = snapshot["assessment"]
    if not isinstance(assessment, Mapping):
        raise ValueError("assessment_invalid")
    return dict(assessment), "AVAILABLE", revision


def _load_report_assessment(
    path: Path, pipeline: str, run_id: str
) -> tuple[dict[str, object], dict[str, object], dict[str, object], str, str]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(report, dict)
        or report.get("schema_version") not in _REPORT_SCHEMAS
    ):
        raise ValueError("report_schema_invalid")
    identity = report.get("identity")
    if (
        not isinstance(identity, dict)
        or identity.get("run_id") != run_id
        or identity.get("pipeline_name") != pipeline
    ):
        raise _IdentityMismatchError("identity_mismatch")
    snapshot = report.get("selected_run_snapshot")
    if snapshot is None:
        assessment, availability, revision = _legacy_assessment(report)
    else:
        if not isinstance(snapshot, dict):
            raise ValueError("snapshot_corrupt_or_rules_unsupported")
        assessment, availability, revision = _snapshot_assessment(
            report, snapshot, path
        )
    return report, identity, assessment, availability, revision


def _recorded_object_flags(manifest: object) -> dict[str, bool]:
    """Return recorded object verifications, ignoring non-boolean noise."""
    recorded = getattr(manifest, "objects", None)
    if not isinstance(recorded, Mapping):
        return {}
    return {
        str(code): flag for code, flag in recorded.items() if isinstance(flag, bool)
    }


def _snapshot_file_verified(raw_uri: object) -> bool | None:
    """Verify one snapshot URI against local disk (#11711).

    Returns True for an existing local file, False for a missing local
    file, and None for remote or empty references.
    """
    if not isinstance(raw_uri, str) or not raw_uri.strip():
        return None
    candidate = raw_uri.strip()
    if "://" in candidate:
        if not candidate.lower().startswith("file://"):
            return None
        candidate = candidate[7:]
    if not candidate:
        return None
    return Path(candidate).is_file()


def _verify_snapshot_objects(manifest: object) -> bool | None:
    """File-verify Bronze input snapshots referenced by the manifest.

    True only when every checkable local file exists. Any missing local
    file — or nothing checkable at all — stays unset so readers report
    object_not_verified instead of assuming presence from a recorded hash.
    """
    sources = getattr(manifest, "source_refs", ()) or ()
    results: list[bool] = []
    for source in sources:
        for snapshot in getattr(source, "input_snapshots", ()) or ():
            for attr in ("immutable_uri", "bronze_batch_ref"):
                result = _snapshot_file_verified(getattr(snapshot, attr, None))
                if result is not None:
                    results.append(result)
                    break
    if not results or not all(results):
        return None
    return True


def _manifest_snapshot(port: object, run_id: str) -> dict[str, object] | None:
    """Read manifest fields for this run. A missing port is not report identity."""
    if port is None:
        return None
    try:
        selected_id = UUID(run_id)
    except ValueError:
        return None
    getter = getattr(port, "get_by_run_id", None)
    if getter is None:
        return None
    manifest = getter(selected_id)
    if manifest is None:
        return None
    provenance = getattr(manifest, "code_provenance", None)
    fingerprints: list[str] = []
    for source in getattr(manifest, "source_refs", ()) or ():
        for snapshot in getattr(source, "input_snapshots", ()) or ():
            content_hash = getattr(snapshot, "content_hash", None)
            if isinstance(content_hash, str) and content_hash.strip():
                fingerprints.append(content_hash.strip())
    capability = getattr(manifest, "replay_capability", None)
    capability_value = getattr(capability, "value", capability)
    launch_context = getattr(manifest, "launch_context", None)
    family_supported = None
    if isinstance(launch_context, Mapping):
        family_supported = launch_context.get("strict_exact_replay_supported")
    config_hash = getattr(provenance, "effective_config_hash", None)
    lock_hash = getattr(provenance, "dependency_lock_hash", None)
    fingerprint = ",".join(fingerprints) if fingerprints else None
    recorded = _recorded_object_flags(manifest)
    snapshot_verified = _verify_snapshot_objects(manifest)
    objects = {
        code: flag
        for code, flag in (
            ("effective_config_hash", recorded.get("effective_config_hash")),
            ("dependency_lock_hash", recorded.get("dependency_lock_hash")),
            (
                "input_snapshot_fingerprint",
                recorded.get("input_snapshot_fingerprint", snapshot_verified),
            ),
        )
        if isinstance(flag, bool)
    }
    verify_objects = getattr(port, "verify_replay_objects", None)
    if callable(verify_objects):
        verified = verify_objects(manifest)
        if isinstance(verified, dict):
            objects = verified
    return {
        "effective_config_hash": config_hash,
        "dependency_lock_hash": lock_hash,
        "input_snapshot_fingerprint": fingerprint,
        "replay_capability": capability_value,
        "exact_replay_supported": family_supported,
        "strict_exact_replay_supported": family_supported,
        "objects": objects,
        "replay_of_run_id": getattr(manifest, "replay_of_run_id", None),
        "replay_of_manifest_id": getattr(manifest, "replay_of_manifest_id", None),
    }


__all__ = [
    "_IdentityMismatchError",
    "_RevisionMissingError",
    "_accounting_conflicts",
    "_load_report_assessment",
    "_manifest_snapshot",
    "_saved_trust",
    "_selected_pipeline",
]
