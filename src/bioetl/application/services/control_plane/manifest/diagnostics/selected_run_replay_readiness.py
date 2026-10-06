# pyright: reportPrivateUsage=false
# Sibling-module helpers in replay_readiness_checks are intra-package private by design.
"""Exact-replay readiness for one selected run, independent of Prometheus."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypedDict

from bioetl.application.services.control_plane.manifest.diagnostics.replay_readiness_checks import (
    _artifact_checks,
    _capability,
    _check,
    _identity_checks,
    _manifest_checks,
)
from bioetl.domain.control_plane import ReplayCapability
from bioetl.domain.control_plane.reproducibility_policy import (
    ReplayReadinessVerdict,
    resolve_replay_readiness_verdict,
)

RULES_VERSION = "exact-replay-readiness-v1"
READY = "READY"
BLOCKED = "BLOCKED"
INSUFFICIENT = "INSUFFICIENT"
UNSUPPORTED = "UNSUPPORTED"
SELECT_RUN = "SELECT RUN"
QUERY_ERROR = "QUERY ERROR"


class ReplayReadinessProjection(TypedDict):
    """Operator-facing replay-readiness projection for one selected run."""

    run_id: str
    pipeline: str
    run_type: str
    replay_mode: str
    verdict: str
    domain_verdict: str
    checks: list[dict[str, str]]
    blockers: list[str]
    unknown_checks: list[str]
    checked_at: str
    rules_version: str
    evidence_revision: str


def _only_family_blocked(required: list[dict[str, str]]) -> bool:
    """Return True when the replay family gate is the sole failing check."""
    return any(
        item["code"] == "exact_replay_family" and item["result"] == "fail"
        for item in required
    ) and not any(
        item["result"] == "fail" and item["code"] != "exact_replay_family"
        for item in required
    )


def _operator_verdict(
    checks: list[dict[str, str]],
    domain_verdict: ReplayReadinessVerdict,
) -> str:
    required = [item for item in checks if item["result"] != "n/a"]
    if any(item["result"] == "fail" for item in required):
        if _only_family_blocked(required):
            return UNSUPPORTED
        return BLOCKED
    if any(item["result"] == "unknown" for item in required):
        return INSUFFICIENT
    if domain_verdict != ReplayReadinessVerdict.EXACT_REPLAY_READY:
        return UNSUPPORTED
    return READY


def _resolve_domain_verdict(
    identity: Mapping[str, object],
    manifest: Mapping[str, object] | None,
    checks: list[dict[str, str]],
) -> ReplayReadinessVerdict:
    """Resolve the domain replay verdict for the current blocking gaps."""
    capability, _known = _capability(manifest or {})
    blocking = tuple(
        item["code"] for item in checks if item["result"] in {"fail", "unknown"}
    )
    return resolve_replay_readiness_verdict(
        replay_capability=capability,
        strict_requirement_requested=True,
        strict_exact_replay_supported=capability
        == ReplayCapability.EXACT_REPLAY_SUPPORTED,
        blocking_gaps=blocking,
        exact_replay_requested=True,
        run_type=identity.get("run_type"),
    )


def _settle_operator_verdict(
    verdict: str,
    *,
    checks: list[dict[str, str]],
    inventory_present: bool,
) -> str:
    """Downgrade READY unless every applicable check passed with inventory."""
    if verdict == READY and (
        not inventory_present
        or any(item["result"] != "pass" for item in checks if item["result"] != "n/a")
    ):
        return INSUFFICIENT
    return verdict


def _readiness_identity_fields(identity: Mapping[str, object]) -> dict[str, str]:
    """Project run identity labels for one readiness projection."""
    run_type = str(identity.get("run_type") or "")
    replay_mode = "exact_replay" if identity.get("exact_replay") is True else run_type
    return {
        "run_id": str(identity.get("run_id") or ""),
        "pipeline": str(
            identity.get("pipeline_name") or identity.get("pipeline") or ""
        ),
        "run_type": run_type,
        "replay_mode": replay_mode or "—",
    }


def project_selected_run_replay_readiness(
    *,
    identity: Mapping[str, object],
    manifest: Mapping[str, object] | None = None,
    artifact_probes: tuple[Mapping[str, object], ...] | list[Mapping[str, object]] = (),
    inventory_present: bool = False,
    evidence_revision: str = "",
    checked_at: str = "",
) -> ReplayReadinessProjection:
    """Project operator readiness. Capability alone never yields READY."""
    checks = [
        *_identity_checks(identity),
        *_manifest_checks(manifest),
        *_artifact_checks(artifact_probes, inventory_present=inventory_present),
    ]
    domain_verdict = _resolve_domain_verdict(identity, manifest, checks)
    verdict = _settle_operator_verdict(
        _operator_verdict(checks, domain_verdict),
        checks=checks,
        inventory_present=inventory_present,
    )
    blockers = [item["code"] for item in checks if item["result"] == "fail"]
    unknown = [item["code"] for item in checks if item["result"] == "unknown"]
    identity_fields = _readiness_identity_fields(identity)
    return {
        "run_id": identity_fields["run_id"],
        "pipeline": identity_fields["pipeline"],
        "run_type": identity_fields["run_type"],
        "replay_mode": identity_fields["replay_mode"],
        "verdict": verdict,
        "domain_verdict": domain_verdict.value,
        "checks": checks,
        "blockers": blockers,
        "unknown_checks": unknown,
        "checked_at": checked_at,
        "rules_version": RULES_VERSION,
        "evidence_revision": evidence_revision,
    }


def empty_replay_readiness(
    *,
    pipeline: str,
    run_id: str,
    verdict: str,
    reason: str,
) -> ReplayReadinessProjection:
    """HTTP states that are not a domain READY."""
    if verdict not in {SELECT_RUN, QUERY_ERROR, INSUFFICIENT, BLOCKED, UNSUPPORTED}:
        verdict = INSUFFICIENT
    return {
        "run_id": run_id,
        "pipeline": pipeline,
        "run_type": "",
        "replay_mode": "—",
        "verdict": verdict,
        "domain_verdict": "",
        "checks": [
            _check(
                "selection",
                "unknown" if verdict == INSUFFICIENT else "n/a",
                reason,
                "#/request",
            )
        ],
        "blockers": [],
        "unknown_checks": [reason],
        "checked_at": "",
        "rules_version": RULES_VERSION,
        "evidence_revision": "",
    }
