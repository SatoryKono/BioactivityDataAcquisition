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
    if not applicable:
        return "N/A"
    if spec.name == "checkpoint_anchor_status":
        return {
            "OK": "OK",
            "MISMATCH": "FAILING",
            "MISSING": "DEGRADED",
            "PARTIAL": "DEGRADED",
        }.get(
            checkpoint_status,
            "DEGRADED",
        )
    if spec.name == "identity_graph_complete" and present:
        rendered_value = str(value).strip().lower()
        if rendered_value.startswith("complete"):
            return "OK"
        if "run_id" in rendered_value or "manifest_id" in rendered_value:
            return "FAILING"
        return "DEGRADED"
    if (
        spec.name == "exact_replay_eligible"
        and manifest is not None
        and requested_exact_replay(manifest)
        and value is False
    ):
        return "FAILING"
    if present:
        return "OK"
    if spec.name == "manifest_id":
        return "FAILING" if is_terminal(ledger_entries) else "DEGRADED"
    if (
        spec.name == "replay_of_manifest_id"
        and manifest is not None
        and requested_exact_replay(manifest)
    ):
        return "FAILING"
    if (
        spec.name
        in {
            "effective_config_hash",
            "effective_config_artifact_id",
            "input_snapshot_identity_fingerprint",
            "input_snapshot_ids",
            "input_snapshot_content_hashes",
        }
        and manifest is not None
        and requested_exact_replay(manifest)
    ):
        return "FAILING"
    return spec.missing_severity


def ui_status(domain_status: str) -> str:
    if domain_status == "FAILING":
        return "CRIT"
    if domain_status in {"DEGRADED", "WARNING"}:
        return "WARN"
    return "OK"


def is_identity_gap(domain_status: str) -> bool:
    return domain_status in {"FAILING", "DEGRADED", "WARNING"}


def applicability(name: str, manifest: RunManifest | None) -> str:
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
