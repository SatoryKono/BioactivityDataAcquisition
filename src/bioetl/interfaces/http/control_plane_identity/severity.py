"""Missing-anchor severity rules for Control Plane identity evidence."""

from __future__ import annotations

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.interfaces.http.control_plane_identity.extractors import (
    is_composite,
    is_replay,
    is_terminal,
    requested_exact_replay,
)
from bioetl.interfaces.http.control_plane_identity.types import AnchorSpec

_CHECKPOINT_ANCHOR_SEVERITY_BY_STATUS = {
    "OK": "OK",
    "MISMATCH": "FAILING",
    "MISSING": "DEGRADED",
    "PARTIAL": "DEGRADED",
}

_EXACT_REPLAY_REQUIRED_ANCHORS = frozenset(
    {
        "effective_config_hash",
        "effective_config_artifact_id",
        "input_snapshot_identity_fingerprint",
        "input_snapshot_ids",
        "input_snapshot_content_hashes",
    }
)


def domain_severity(
    spec: AnchorSpec,
    *,
    value: object | None,
    present: bool,
    manifest: RunManifest | None,
    ledger_entries: tuple[RunLedgerEntry, ...],
    checkpoint_status: str,
    applicable: bool,
) -> str:
    """Map one identity anchor to a domain severity token.

    Returns N/A, OK, DEGRADED, WARNING, or FAILING from applicability,
    checkpoint status, exact-replay eligibility, and missing-anchor policy.
    """
    if not applicable:
        return "N/A"
    if spec.name == "checkpoint_anchor_status":
        return _checkpoint_anchor_severity(checkpoint_status)
    if spec.name == "identity_graph_complete" and present:
        return _identity_graph_severity(value)
    if _exact_replay_eligibility_failed(spec, manifest=manifest, value=value):
        return "FAILING"
    if present:
        return "OK"
    return _missing_anchor_severity(
        spec,
        manifest=manifest,
        ledger_entries=ledger_entries,
    )


def _checkpoint_anchor_severity(checkpoint_status: str) -> str:
    return _CHECKPOINT_ANCHOR_SEVERITY_BY_STATUS.get(checkpoint_status, "DEGRADED")


def _identity_graph_severity(value: object | None) -> str:
    if value is True:
        return "OK"
    rendered_value = str(value).strip().lower()
    if rendered_value in {"true", "ok"} or rendered_value.startswith("complete"):
        return "OK"
    if "run_id" in rendered_value or "manifest_id" in rendered_value:
        return "FAILING"
    return "DEGRADED"


def _exact_replay_eligibility_failed(
    spec: AnchorSpec,
    *,
    manifest: RunManifest | None,
    value: object | None,
) -> bool:
    return (
        spec.name == "exact_replay_eligible"
        and manifest is not None
        and requested_exact_replay(manifest)
        and value is False
    )


def _missing_anchor_severity(
    spec: AnchorSpec,
    *,
    manifest: RunManifest | None,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> str:
    if spec.name == "manifest_id":
        return "FAILING" if is_terminal(ledger_entries) else "DEGRADED"
    if (
        spec.name == "replay_of_manifest_id"
        and manifest is not None
        and requested_exact_replay(manifest)
    ):
        return "FAILING"
    if (
        spec.name in _EXACT_REPLAY_REQUIRED_ANCHORS
        and manifest is not None
        and requested_exact_replay(manifest)
    ):
        return "FAILING"
    return spec.missing_severity


def ui_status(domain_status: str) -> str:
    """Map a domain severity token to the Control Plane UI status."""
    if domain_status == "FAILING":
        return "CRIT"
    if domain_status in {"DEGRADED", "WARNING"}:
        return "WARN"
    return "OK"


def is_identity_gap(domain_status: str) -> bool:
    """Return True when the domain status is a failing or degraded gap."""
    return domain_status in {"FAILING", "DEGRADED", "WARNING"}


def applicability(name: str, manifest: RunManifest | None) -> str:
    """Return APPLICABLE, N/A, or a scope note for one identity anchor."""
    if manifest is None:
        return "not available for current scope"
    if name in {"replay_of_run_id", "replay_of_manifest_id"} and not is_replay(
        manifest
    ):
        return "N/A"
    if name in {
        "composite_run_identity",
        "component_run_ids",
        "cross_validation_rule_ids",
    }:
        return "N/A" if not is_composite(manifest) else "APPLICABLE"
    return "APPLICABLE"
