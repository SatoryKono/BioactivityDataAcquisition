"""Replay-readiness check builders for one selected run."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, cast

from bioetl.domain.control_plane import ReplayCapability

CheckResult = Literal["pass", "fail", "unknown", "n/a"]
_TERMINAL_STATUSES = frozenset({"success", "failed", "shutdown", "cancelled"})
_UNFINISHED_STATUSES = frozenset({"running", "started", "unfinished"})
_RUN_SCOPED_CAPABILITIES = frozenset(
    {
        ReplayCapability.RESUME_ONLY.value,
        ReplayCapability.REBUILD_ONLY.value,
    }
)
_MISSING_SNAPSHOTS_REASON = "run_missing_input_snapshots"
_FAMILY_OUTSIDE_REASON = "family_outside_supported_exact_replay_boundary"


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
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return value is not None


def _capability(source: Mapping[str, object]) -> tuple[ReplayCapability, bool]:
    token = str(source.get("replay_capability") or "").strip().lower()
    try:
        return ReplayCapability(token), True
    except ValueError:
        return ReplayCapability.REBUILD_ONLY, False


def _recorded_object_check(
    manifest: Mapping[str, object],
    code: str,
) -> dict[str, str]:
    """A recorded hash is not a pass until its object is verified."""
    objects = manifest.get("objects")
    verified = objects.get(code) if isinstance(objects, Mapping) else None
    if not _present(manifest.get(code)):
        return _check(code, "unknown", "not_recorded", f"#/manifest/{code}")
    if verified is True:
        return _check(code, "pass", "object_verified", f"#/manifest/{code}")
    if verified is False:
        return _check(code, "fail", "hash_without_object", f"#/manifest/{code}")
    return _check(code, "unknown", "object_not_verified", f"#/manifest/{code}")


def _manifest_checks(
    manifest: Mapping[str, object] | None,
) -> list[dict[str, str]]:
    if manifest is None:
        return [
            _check(
                "manifest_not_recorded",
                "unknown",
                "manifest_not_recorded",
                "#/manifest",
            )
        ]
    checks = [
        _recorded_object_check(manifest, code)
        for code in (
            "effective_config_hash",
            "dependency_lock_hash",
            "input_snapshot_fingerprint",
        )
    ]
    checks.append(_exact_replay_family_check(manifest))
    return checks


def _family_supported(manifest: Mapping[str, object]) -> bool | None:
    """Return explicit family support; None means the flag was not recorded."""
    supported = manifest.get("exact_replay_supported")
    if supported is None:
        supported = manifest.get("strict_exact_replay_supported")
    if supported is None:
        return None
    token = str(supported).strip().lower()
    if token in {"true", "1", "yes", "false", "0", "no"}:
        return token in {"true", "1", "yes"}
    return None


def _exact_replay_family_check(manifest: Mapping[str, object]) -> dict[str, str]:
    """Classify family support separately from this run's snapshot envelope."""
    capability, capability_known = _capability(manifest)
    family_supported = _family_supported(manifest)
    if family_supported is False:
        return _check(
            "exact_replay_family",
            "fail",
            _FAMILY_OUTSIDE_REASON,
            "#/manifest/replay_capability",
        )
    if capability_known and capability == ReplayCapability.EXACT_REPLAY_SUPPORTED:
        return _check(
            "exact_replay_family",
            "pass",
            capability.value,
            "#/manifest/replay_capability",
        )
    if capability_known and capability.value in _RUN_SCOPED_CAPABILITIES:
        return _check(
            "exact_replay_family",
            "unknown",
            _MISSING_SNAPSHOTS_REASON,
            "#/manifest/replay_capability",
        )
    return _check(
        "exact_replay_family",
        "unknown",
        "replay_capability_not_recorded",
        "#/manifest/replay_capability",
    )


def _identity_checks(identity: Mapping[str, object]) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    status = str(identity.get("status") or "").strip().lower()
    if status in _TERMINAL_STATUSES:
        checks.append(_check("terminal_status", "pass", status, "#/identity/status"))
    elif status in _UNFINISHED_STATUSES:
        checks.append(
            _check(
                "terminal_status",
                "fail",
                "unfinished_run",
                "#/identity/status",
            )
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
            cast("CheckResult", raw_result)
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
