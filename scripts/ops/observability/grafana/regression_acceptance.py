"""Verify RF-005 evidence without interpreting absent measurements as success.

This is an offline verifier of reviewed receipts, not a measurement producer.
All input paths are relative to the immutable reviewer bundle.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from statistics import median
from typing import Any

UIDS = frozenset(
    {
        "bioetl-control-plane-v1",
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-provider-health-v2",
        "bioetl-dq-v2",
        "bioetl-incident-v1",
        "bioetl-run-explorer-v1",
    }
)
MEASUREMENT_GATES = (
    "provenance",
    "layout",
    "lineage",
    "integrity",
    "text_contrast",
    "graphics_contrast",
    "color_only",
    "semantic_parity",
    "regression_search",
    "windows_full_profile",
)
FINDINGS = frozenset(
    [f"F{i:02}" for i in range(1, 21)]
    + [
        f"{prefix}{i:02}"
        for prefix, n in (
            ("G", 3),
            ("T", 3),
            ("O", 3),
            ("R", 2),
            ("P", 3),
            ("D", 3),
            ("I", 4),
            ("E", 7),
        )
        for i in range(1, n + 1)
    ]
)


def _read(root: Path, descriptor: dict[str, Any]) -> dict[str, Any]:
    relative = Path(descriptor["path"])
    path = (root / relative).resolve()
    if relative.is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError("evidence path must stay in reviewer bundle")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != descriptor["sha256"]:
        raise ValueError(f"evidence hash mismatch: {relative}")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("evidence must be an object")
    return payload


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _measurement_pass(row: dict[str, Any]) -> bool:
    actual, expected, tolerance = (
        row.get(k) for k in ("actual", "expected", "tolerance")
    )
    if not all(_number(v) for v in (actual, expected, tolerance)) or tolerance < 0:
        return False
    if not row.get("evidence") or not row.get("reference"):
        return False
    comparison = row.get("comparison")
    if comparison == "eq":
        return abs(actual - expected) <= tolerance
    if comparison == "ge":
        return actual >= expected and tolerance == 0
    if comparison == "le":
        return actual <= expected and tolerance == 0
    return False


def _bound(payload: dict[str, Any], contract: dict[str, Any]) -> None:
    for key in (
        "candidate_ref",
        "occurrence_id",
        "time_range",
        "variable_matrix",
        "viewports",
    ):
        if payload.get(key) != contract[key]:
            raise ValueError(f"mismatched {key}")
    if set(payload.get("dashboard_uids", [])) != UIDS:
        raise ValueError("incomplete seven-dashboard scope")


def _measurements(payload: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    required = inventory["checks"]
    if not required and inventory.get("na_reason") and inventory.get("approved_by"):
        if (
            payload.get("measurements")
            or payload.get("na_reason") != inventory["na_reason"]
        ):
            raise ValueError("NA scope differs from approved baseline")
        return {
            "status": "NA",
            "numerator": 0,
            "denominator": 0,
            "percentage": None,
            "reason": inventory["na_reason"],
        }
    required_ids = [row["id"] for row in required]
    rows = payload.get("measurements", [])
    ids = [row["id"] for row in rows]
    if not required or len(set(required_ids)) != len(required):
        raise ValueError(
            "mandatory inventory empty or duplicated; reviewed NA cannot imply 100%"
        )
    if len(set(ids)) != len(ids) or set(ids) != set(required_ids):
        raise ValueError("measurement inventory differs from approved baseline")
    limits = {row["id"]: row for row in required}
    if any(
        any(
            row.get(k) != limits[row["id"]].get(k)
            for k in ("expected", "comparison", "tolerance")
        )
        for row in rows
    ):
        raise ValueError("measurement limits differ from approved baseline")
    passed = sum(_measurement_pass(row) for row in rows)
    return {
        "status": "PASS" if passed == len(required) else "FAIL",
        "numerator": passed,
        "denominator": len(required),
    }


def _task_statistics(
    rows: list[dict[str, Any]], participant_type: str, attempt_kind: str, task_id: str
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "participant_type": participant_type,
        "attempt_kind": attempt_kind,
        "task_id": task_id,
        "attempt_count": len(rows),
        "participant_count": len(
            {r.get("participant_id") for r in rows if r.get("participant_id")}
        ),
        "success_count": sum(r.get("success") is True for r in rows),
    }
    for field in (
        "first_correct_seconds",
        "clicks",
        "interactions",
        "diagnostic_depth",
        "context_loss",
        "back_navigation",
    ):
        values = [r[field] for r in rows if _number(r.get(field)) and r[field] >= 0]
        row[field] = {
            "sample_size": len(values),
            "median": median(values) if values else None,
            "max": max(values) if values else None,
        }
    return row


def _operator_statistics(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    statistics = []
    for participant_type in ("HUMAN", "AI_AGENT"):
        for attempt_kind in ("first", "repeat"):
            group = [
                r
                for r in observations
                if r.get("participant_type") == participant_type
                and r.get("attempt_kind") == attempt_kind
            ]
            for task_id in ["ALL", *sorted({r["task_id"] for r in group})]:
                rows = (
                    group
                    if task_id == "ALL"
                    else [r for r in group if r["task_id"] == task_id]
                )
                statistics.append(
                    _task_statistics(rows, participant_type, attempt_kind, task_id)
                )
    return statistics


def _completed_human_attempt(row: dict[str, Any]) -> bool:
    seconds = row.get("first_correct_seconds")
    if (
        row.get("participant_type") != "HUMAN"
        or row.get("attempt_kind") != "first"
        or row.get("success") is not True
        or not row.get("participant_id")
        or not row.get("reviewer")
        or not row.get("answer_key_evidence")
        or not row.get("answer")
        or not row.get("path")
        or not row.get("evidence")
        or not _number(seconds)
        or seconds < 0
    ):
        return False
    if not all(
        type(row.get(k)) is int and row[k] >= 0
        for k in (
            "clicks",
            "interactions",
            "diagnostic_depth",
            "back_navigation",
            "context_loss",
        )
    ):
        return False
    if seconds > 10 and not row.get("deviation_disposition"):
        return False
    if row["context_loss"] and not row.get("context_loss_disposition"):
        return False
    return True


def _operator(payload: dict[str, Any]) -> dict[str, Any]:
    expected = {f"{uid}:Q{q}" for uid in UIDS for q in (1, 2, 3)}
    observations = payload.get("observations", [])
    completed: set[str] = set()
    first_keys = [
        (r.get("participant_type"), r.get("participant_id"), r.get("task_id"))
        for r in observations
        if r.get("attempt_kind") == "first"
    ]
    if len(first_keys) != len(set(first_keys)):
        raise ValueError("duplicate first attempt for participant/task")
    for row in observations:
        if _completed_human_attempt(row):
            completed.add(row["task_id"])
    approved = bool(
        payload.get("page_goals_approved_by") and payload.get("primary_role")
    )
    return {
        "status": "PASS" if approved and completed == expected else "CANNOT_VERIFY",
        "numerator": len(completed & expected),
        "denominator": 21,
        "human_required": True,
        "agent_observations_do_not_measure_human_insight": True,
        "statistics": _operator_statistics(observations),
    }


def _validate_scope(contract: dict[str, Any]) -> None:
    for key in ("baseline_ref", "candidate_ref"):
        if not re.fullmatch(r"[0-9a-f]{40}", contract[key]):
            raise ValueError(f"{key} must be immutable full SHA")
    if contract["baseline_ref"] == contract["candidate_ref"]:
        raise ValueError("baseline and candidate refs are identical")
    window = contract["time_range"]
    if (
        window.get("timezone") != "UTC"
        or not str(window["from"]).isascii()
        or not str(window["from"]).isdigit()
        or not str(window["to"]).isascii()
        or not str(window["to"]).isdigit()
        or int(window["from"]) >= int(window["to"])
    ):
        raise ValueError("fixed increasing UTC millisecond window required")
    if not contract["occurrence_id"] or not contract["variable_matrix"]:
        raise ValueError("occurrence and variable matrix required")
    if [1366, 768] not in contract["viewports"] or [900, 768] not in contract[
        "viewports"
    ]:
        raise ValueError("original wide and narrow viewports required")


def _validate_baseline(baseline: dict[str, Any], contract: dict[str, Any]) -> None:
    if baseline.get("baseline_ref") != contract["baseline_ref"] or not baseline.get(
        "approved_by"
    ):
        raise ValueError("baseline identity/approval missing")
    rows = baseline["findings"]
    baseline_ids = [r["id"] for r in rows]
    if len(set(baseline_ids)) != len(baseline_ids) or not FINDINGS <= set(baseline_ids):
        raise ValueError(
            "baseline must include F01-F20 and all 28 original observations"
        )
    if any(
        r.get("severity") not in ("P0", "P1", "P2", "P3")
        or not r.get("acceptance_test")
        for r in rows
    ):
        raise ValueError("baseline severity and original acceptance tests required")


def _verify_finding(root: Path, row: dict[str, Any], before: dict[str, Any]) -> None:
    for key in ("before", "after", "reference", "evidence"):
        _read(root, row[key])
    if any(
        row.get(k) != before.get(k)
        for k in (
            "severity",
            "acceptance_test",
            "expected",
            "comparison",
            "tolerance",
        )
    ):
        raise ValueError("severity or original acceptance test changed")
    if (
        row.get("disposition") != "FIXED"
        or not row.get("before")
        or not row.get("after")
        or not _measurement_pass(row)
    ):
        raise ValueError(f"unproven finding: {row['id']}")


def _findings(
    root: Path, payload: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, Any]:
    retests = payload["findings"]
    ids = [r["id"] for r in retests]
    original = {r["id"]: r for r in baseline["findings"]}
    if set(ids) != set(original) or len(set(ids)) != len(ids):
        raise ValueError("missing or duplicate baseline retest")
    for row in retests:
        _verify_finding(root, row, original[row["id"]])
    return {"status": "PASS", "numerator": len(ids), "denominator": len(ids)}


def _new_regressions(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("search_evidence") or not payload.get("reviewer"):
        raise ValueError("new regression search evidence/reviewer missing")
    _read(root, payload["search_evidence"])
    findings = payload["findings"]
    if not isinstance(findings, list) or any(
        r.get("severity") not in ("P0", "P1", "P2", "P3") for r in findings
    ):
        raise ValueError("invalid regression findings")
    blockers = sum(r["severity"] in ("P0", "P1") for r in findings)
    return {
        "status": "PASS" if blockers == 0 else "FAIL",
        "actual": blockers,
    }


def _verify_evidence(root: Path, name: str, payload: dict[str, Any]) -> None:
    evidence_rows = payload.get("measurements", payload.get("observations", []))
    for row in evidence_rows:
        for key in (
            ("evidence", "answer_key_evidence")
            if name == "operator"
            else ("evidence", "reference")
        ):
            _read(root, row[key])


def _evaluate_gate(
    root: Path, name: str, contract: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, Any]:
    payload = _read(root, contract["artifacts"][name])
    _bound(payload, contract)
    _verify_evidence(root, name, payload)
    if name == "operator":
        return _operator(payload)
    if name == "findings":
        return _findings(root, payload, baseline)
    if name == "new_regressions":
        return _new_regressions(root, payload)
    return _measurements(payload, baseline["required_measurements"][name])


def evaluate(input_path: Path) -> dict[str, Any]:
    """Return all available gate results; malformed/missing inputs fail closed."""
    gates: dict[str, Any] = {}
    result: dict[str, Any] = {
        "schema_version": 1,
        "release_passed": False,
        "gates": gates,
    }
    try:
        contract = json.loads(input_path.read_text(encoding="utf-8"))
        result["candidate_ref"] = contract["candidate_ref"]
        _validate_scope(contract)
        baseline = _read(input_path.parent, contract["baseline"])
        _validate_baseline(baseline, contract)
        gates["contract"] = {"status": "PASS"}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        gates["contract"] = {"status": "CANNOT_VERIFY", "reason": str(exc)}
        return result
    for name in (*MEASUREMENT_GATES, "operator", "findings", "new_regressions"):
        try:
            gates[name] = _evaluate_gate(input_path.parent, name, contract, baseline)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            gates[name] = {"status": "CANNOT_VERIFY", "reason": str(exc)}
    result["release_passed"] = all(
        g["status"] in {"PASS", "NA"} for g in gates.values()
    )
    return result


def write_report(
    input_path: Path,
    output_path: Path,
    *,
    expected_candidate: str | None = None,
    working_tree_clean: bool = True,
) -> bool:
    """Write once; historical acceptance artifacts must not be overwritten."""
    payload = evaluate(input_path)
    if not working_tree_clean:
        payload["gates"]["working_tree"] = {
            "status": "CANNOT_VERIFY",
            "reason": "tracked changes are not part of candidate HEAD",
        }
        payload["release_passed"] = False
    if (
        expected_candidate is not None
        and payload.get("candidate_ref") != expected_candidate
    ):
        payload["gates"]["checkout_identity"] = {
            "status": "CANNOT_VERIFY",
            "reason": "candidate is not the current checkout HEAD",
        }
        payload["release_passed"] = False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return bool(payload["release_passed"])
