"""Exact-replay readiness for one selected run, independent of Prometheus."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

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

CheckResult = Literal["pass", "fail", "unknown", "n/a"]
_TERMINAL_STATUSES = frozenset({"success", "failed", "shutdown", "cancelled"})
_UNFINISHED_STATUSES = frozenset({"running", "started", "unfinished"})
_EXPLICIT_UNSUPPORTED = frozenset(
    {
        ReplayCapability.RESUME_ONLY.value,
        ReplayCapability.REBUILD_ONLY.value,
    }
)


def _check(
    code: str,
    result: CheckResult,
    reason: str,
    evidence_ref: str,
) -> dict[str, str]:
    return {
        "code": code,
        "result": result,
        "reason": reason,
        "evidence_ref": evidence_ref,
    }


def _present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def _capability(identity: Mapping[str, object]) -> tuple[ReplayCapability, bool]:
    token = str(identity.get("replay_capability") or "").strip().lower()
    try:
        return ReplayCapability(token), True
    except ValueError:
        return ReplayCapability.REBUILD_ONLY, False


def _identity_checks(identity: Mapping[str, object]) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    status = str(identity.get("status") or "").strip().lower()
    if status in _TERMINAL_STATUSES:
        checks.append(_check("terminal_status", "pass", status, "#/identity/status"))
    elif status in _UNFINISHED_STATUSES:
        checks.append(
            _check("terminal_status", "fail", "unfinished_run", "#/identity/status")
        )
    else:
        checks.append(
            _check(
                "terminal_status",
                "unknown",
                "terminal_status_not_recorded",
                "#/identity/status",
            )
        )
    is_replay = bool(
        identity.get("replay_of_manifest_id") or identity.get("exact_replay") is True
    )
    if is_replay or _present(identity.get("replay_of_run_id")):
        if _present(identity.get("replay_of_run_id")):
            checks.append(
                _check(
                    "replay_of_run_id",
                    "pass",
                    "replay_anchor_present",
                    "#/identity/replay_of_run_id",
                )
            )
        else:
            checks.append(
                _check(
                    "replay_of_run_id",
                    "fail",
                    "replay_anchor_missing",
                    "#/identity/replay_of_run_id",
                )
            )
    else:
        checks.append(
            _check(
                "replay_of_run_id",
                "n/a",
                "source_run_not_a_replay",
                "#/identity/replay_of_run_id",
            )
        )
    for code in (
        "effective_config_hash",
        "dependency_lock_hash",
        "input_snapshot_fingerprint",
    ):
        if _present(identity.get(code)):
            checks.append(
                _check(code, "pass", "recorded_in_saved_report", f"#/identity/{code}")
            )
        else:
            checks.append(_check(code, "unknown", "not_recorded", f"#/identity/{code}"))
    supported = identity.get("exact_replay_supported")
    capability, capability_known = _capability(identity)
    if supported is False or (
        capability_known and capability.value in _EXPLICIT_UNSUPPORTED
    ):
        checks.append(
            _check(
                "exact_replay_family",
                "fail",
                "family_outside_supported_exact_replay_boundary",
                "#/identity/replay_capability",
            )
        )
    elif capability_known and capability == ReplayCapability.EXACT_REPLAY_SUPPORTED:
        checks.append(
            _check(
                "exact_replay_family",
                "pass",
                capability.value,
                "#/identity/replay_capability",
            )
        )
    else:
        checks.append(
            _check(
                "exact_replay_family",
                "unknown",
                "replay_capability_not_recorded",
                "#/identity/replay_capability",
            )
        )
    return checks


def _artifact_checks(
    probes: tuple[Mapping[str, object], ...] | list[Mapping[str, object]],
    *,
    inventory_present: bool,
) -> list[dict[str, str]]:
    if not inventory_present:
        return [
            _check(
                "artifact_inventory",
                "unknown",
                "artifact_inventory_absent",
                "#/artifacts",
            )
        ]
    checks = [_check("artifact_inventory", "pass", "inventory_present", "#/artifacts")]
    if not probes:
        checks.append(
            _check(
                "artifact_inventory",
                "unknown",
                "artifact_inventory_empty",
                "#/artifacts",
            )
        )
        return checks
    for index, probe in enumerate(probes):
        raw_result = str(probe.get("result") or "unknown")
        result: CheckResult = (
            raw_result
            if raw_result in {"pass", "fail", "unknown", "n/a"}
            else "unknown"
        )
        checks.append(
            _check(
                str(probe.get("code") or f"artifact_{index}"),
                result,
                str(probe.get("reason") or "unspecified"),
                str(probe.get("evidence_ref") or f"#/artifacts/{index}"),
            )
        )
    return checks


def _operator_verdict(
    checks: list[dict[str, str]],
    domain_verdict: ReplayReadinessVerdict,
) -> str:
    required = [item for item in checks if item["result"] != "n/a"]
    if any(item["result"] == "fail" for item in required):
        if any(
            item["code"] == "exact_replay_family" and item["result"] == "fail"
            for item in required
        ) and not any(
            item["result"] == "fail" and item["code"] != "exact_replay_family"
            for item in required
        ):
            return UNSUPPORTED
        return BLOCKED
    if any(item["result"] == "unknown" for item in required):
        return INSUFFICIENT
    if domain_verdict != ReplayReadinessVerdict.EXACT_REPLAY_READY:
        return UNSUPPORTED
    return READY


def project_selected_run_replay_readiness(
    *,
    identity: Mapping[str, object],
    artifact_probes: tuple[Mapping[str, object], ...] | list[Mapping[str, object]] = (),
    inventory_present: bool = False,
    evidence_revision: str = "",
    checked_at: str = "",
) -> dict[str, object]:
    """Project operator readiness. Capability alone never yields READY."""
    checks = [
        *_identity_checks(identity),
        *_artifact_checks(artifact_probes, inventory_present=inventory_present),
    ]
    capability, _known = _capability(identity)
    blocking = tuple(
        item["code"] for item in checks if item["result"] in {"fail", "unknown"}
    )
    domain_verdict = resolve_replay_readiness_verdict(
        replay_capability=capability,
        strict_requirement_requested=True,
        strict_exact_replay_supported=capability
        == ReplayCapability.EXACT_REPLAY_SUPPORTED,
        blocking_gaps=blocking,
        exact_replay_requested=True,
        run_type=identity.get("run_type"),
    )
    verdict = _operator_verdict(checks, domain_verdict)
    if verdict == READY and (
        not inventory_present
        or any(item["result"] != "pass" for item in checks if item["result"] != "n/a")
    ):
        verdict = INSUFFICIENT
    blockers = [item["code"] for item in checks if item["result"] == "fail"]
    unknown = [item["code"] for item in checks if item["result"] == "unknown"]
    run_type = str(identity.get("run_type") or "")
    replay_mode = "exact_replay" if identity.get("exact_replay") is True else run_type
    return {
        "run_id": str(identity.get("run_id") or ""),
        "pipeline": str(
            identity.get("pipeline_name") or identity.get("pipeline") or ""
        ),
        "run_type": run_type,
        "replay_mode": replay_mode or "—",
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
) -> dict[str, object]:
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
