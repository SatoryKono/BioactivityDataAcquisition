#!/usr/bin/env python3
"""Run deterministic Silver/Gold filter parity checks for ADR-050 migration.

The harness compares a legacy normalized filter config with the cleaned YAML
shape against the same Bronze snapshot and source profile. It proves Gold
output parity while making bounded Silver widening explicit.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

from bioetl.infrastructure.config.silver_filter_migration import (
    normalize_silver_gold_filter_payload,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "golden"
    / "reproducibility"
    / "silver_gold_filter_parity_v1.json"
)
DEFAULT_REPORT_OUT = (
    PROJECT_ROOT / "reports" / "quality" / "silver-gold-filter-parity-report.json"
)
GENERATED_BY = "scripts/data_quality/run_silver_gold_filter_parity.py"
SCHEMA_VERSION = "silver-gold-filter-parity-report-v1"

JsonDict = dict[str, Any]
PkTuple = tuple[str, ...]


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(value[key]) for key in sorted(value)}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    return value


def _canonical(value: Any) -> str:
    return json.dumps(_json_ready(value), sort_keys=True, separators=(",", ":"))


def _read_json(path: Path) -> JsonDict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _pk_tuple(raw_pk: Any) -> PkTuple:
    if not isinstance(raw_pk, list | tuple):
        raise ValueError(f"Record pk must be a list, got {raw_pk!r}")
    pk = tuple(str(part) for part in raw_pk)
    if not pk:
        raise ValueError("Record pk must not be empty")
    return pk


def _pk_list(pk: PkTuple) -> list[str]:
    return list(pk)


def _record_hash_map(records: Iterable[Mapping[str, Any]]) -> dict[PkTuple, str]:
    result: dict[PkTuple, str] = {}
    for record in records:
        pk = _pk_tuple(record.get("pk"))
        content_hash = record.get("content_hash")
        if not isinstance(content_hash, str) or not content_hash:
            raise ValueError(f"Record {pk!r} must contain a non-empty content_hash")
        if pk in result:
            raise ValueError(f"Duplicate record pk in parity fixture: {pk!r}")
        result[pk] = content_hash
    return result


def _reject_pk(reject: Mapping[str, Any]) -> PkTuple:
    return _pk_tuple(reject.get("pk"))


def _reject_stage(reject: Mapping[str, Any]) -> str:
    value = reject.get("stage", reject.get("scope", "unknown"))
    return str(value or "unknown")


def _reject_origin(reject: Mapping[str, Any]) -> str:
    return str(reject.get("compatibility_origin") or "")


def _reject_class(reject: Mapping[str, Any]) -> str:
    return str(reject.get("rule_class") or reject.get("rule_type") or "unknown")


def _reject_reason(reject: Mapping[str, Any]) -> str:
    return str(reject.get("reason_code") or "unknown")


def _distribution(
    rejects: Iterable[Mapping[str, Any]],
    *,
    fields: Sequence[str],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for reject in rejects:
        values: list[str] = []
        for field in fields:
            if field == "stage":
                values.append(_reject_stage(reject))
            elif field == "rule_class":
                values.append(_reject_class(reject))
            elif field == "reason_code":
                values.append(_reject_reason(reject))
            elif field == "compatibility_origin":
                values.append(_reject_origin(reject))
            else:
                values.append(str(reject.get(field) or ""))
        counts["|".join(values)] += 1
    return dict(sorted(counts.items()))


def _legacy_semantic_silver_rejects(
    rejects: Iterable[Mapping[str, Any]],
) -> dict[PkTuple, str]:
    result: dict[PkTuple, str] = {}
    for reject in rejects:
        if _reject_stage(reject) != "silver":
            continue
        origin = _reject_origin(reject)
        rule_class = _reject_class(reject)
        if origin != "legacy_semantic_silver_filter" and rule_class != "semantic":
            continue
        result[_reject_pk(reject)] = _reject_reason(reject)
    return result


def _migrated_gold_semantic_rejects(
    rejects: Iterable[Mapping[str, Any]],
) -> dict[PkTuple, str]:
    result: dict[PkTuple, str] = {}
    for reject in rejects:
        if _reject_stage(reject) != "gold":
            continue
        origin = _reject_origin(reject)
        if origin != "promoted_legacy_semantic_silver_filter":
            continue
        result[_reject_pk(reject)] = _reject_reason(reject)
    return result


def _sorted_pk_lists(pks: Iterable[PkTuple]) -> list[list[str]]:
    return [_pk_list(pk) for pk in sorted(pks)]


def _hash_delta(
    legacy: Mapping[PkTuple, str],
    cleaned: Mapping[PkTuple, str],
) -> JsonDict:
    legacy_pks = set(legacy)
    cleaned_pks = set(cleaned)
    common = legacy_pks & cleaned_pks
    changed = sorted(pk for pk in common if legacy[pk] != cleaned[pk])
    return {
        "missing_pks": _sorted_pk_lists(legacy_pks - cleaned_pks),
        "extra_pks": _sorted_pk_lists(cleaned_pks - legacy_pks),
        "changed_content_hash_pks": _sorted_pk_lists(changed),
    }


def _same_canonical(left: Any, right: Any) -> bool:
    return _canonical(left) == _canonical(right)


def _required_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"Scenario missing object field: {key}")
    return value


def _required_list(payload: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ValueError(f"Scenario missing object-list field: {key}")
    return value


def _compare_config(legacy_run: Mapping[str, Any], cleaned_run: Mapping[str, Any]) -> bool:
    legacy_config = _required_mapping(legacy_run, "filter_config")
    cleaned_config = _required_mapping(cleaned_run, "filter_config")
    return _same_canonical(
        normalize_silver_gold_filter_payload(legacy_config),
        normalize_silver_gold_filter_payload(cleaned_config),
    )


def _identity_anchor_delta(
    legacy: Mapping[str, Any],
    cleaned: Mapping[str, Any],
) -> dict[str, JsonDict]:
    keys = sorted(set(legacy) | set(cleaned))
    delta: dict[str, JsonDict] = {}
    for key in keys:
        left = legacy.get(key)
        right = cleaned.get(key)
        if not _same_canonical(left, right):
            delta[key] = {"legacy": _json_ready(left), "cleaned": _json_ready(right)}
    return delta


def evaluate_scenario(scenario: Mapping[str, Any]) -> JsonDict:
    """Evaluate one fixture scenario and return a deterministic report object."""
    scenario_id = str(scenario.get("scenario_id") or "")
    if not scenario_id:
        raise ValueError("Scenario missing scenario_id")

    legacy_run = _required_mapping(scenario, "legacy_normalized")
    cleaned_run = _required_mapping(scenario, "cleaned_yaml")

    source_profile_same = _same_canonical(
        legacy_run.get("source_profile"),
        cleaned_run.get("source_profile"),
    )
    bronze_snapshot_same = _same_canonical(
        legacy_run.get("bronze_snapshot"),
        cleaned_run.get("bronze_snapshot"),
    )

    legacy_anchors = _required_mapping(legacy_run, "identity_anchors")
    cleaned_anchors = _required_mapping(cleaned_run, "identity_anchors")
    anchor_delta = _identity_anchor_delta(legacy_anchors, cleaned_anchors)

    legacy_silver = _record_hash_map(_required_list(legacy_run, "silver_records"))
    cleaned_silver = _record_hash_map(_required_list(cleaned_run, "silver_records"))
    legacy_gold = _record_hash_map(_required_list(legacy_run, "gold_records"))
    cleaned_gold = _record_hash_map(_required_list(cleaned_run, "gold_records"))

    silver_delta = _hash_delta(legacy_silver, cleaned_silver)
    gold_delta = _hash_delta(legacy_gold, cleaned_gold)
    common_silver_changed = silver_delta["changed_content_hash_pks"]

    legacy_rejects = _required_list(legacy_run, "rejects")
    cleaned_rejects = _required_list(cleaned_run, "rejects")
    legacy_semantic_rejects = _legacy_semantic_silver_rejects(legacy_rejects)
    cleaned_migrated_rejects = _migrated_gold_semantic_rejects(cleaned_rejects)

    added_silver_pks = set(cleaned_silver) - set(legacy_silver)
    removed_silver_pks = set(legacy_silver) - set(cleaned_silver)
    allowed_widening_pks = set(legacy_semantic_rejects)
    unbounded_added_pks = added_silver_pks - allowed_widening_pks
    migrated_reason_mismatches = sorted(
        pk
        for pk in added_silver_pks & allowed_widening_pks
        if cleaned_migrated_rejects.get(pk) != legacy_semantic_rejects.get(pk)
    )

    legacy_reason_distribution = _distribution(
        legacy_rejects,
        fields=("reason_code",),
    )
    cleaned_reason_distribution = _distribution(
        cleaned_rejects,
        fields=("reason_code",),
    )
    legacy_stage_distribution = _distribution(
        legacy_rejects,
        fields=("stage", "rule_class", "reason_code"),
    )
    cleaned_stage_distribution = _distribution(
        cleaned_rejects,
        fields=("stage", "rule_class", "reason_code"),
    )

    checks = {
        "config_normalization_equal": _compare_config(legacy_run, cleaned_run),
        "same_source_profile": source_profile_same,
        "same_bronze_snapshot": bronze_snapshot_same,
        "identity_anchors_equal": not anchor_delta,
        "gold_pk_content_hash_parity": not any(gold_delta.values()),
        "silver_no_removed_pks": not removed_silver_pks,
        "silver_common_content_hash_parity": not common_silver_changed,
        "silver_widening_bounded_to_legacy_semantic_rejects": not unbounded_added_pks,
        "migrated_semantic_reject_reasons_preserved": not migrated_reason_mismatches,
        "reject_reason_distribution_conserved": (
            legacy_reason_distribution == cleaned_reason_distribution
        ),
    }
    verdict = "pass" if all(checks.values()) else "fail"

    return {
        "scenario_id": scenario_id,
        "pipeline_name": cleaned_anchors.get("pipeline_name"),
        "provider": cleaned_anchors.get("provider"),
        "entity": cleaned_anchors.get("entity"),
        "run_type": cleaned_anchors.get("run_type"),
        "source_profile": _json_ready(cleaned_run.get("source_profile")),
        "bronze_snapshot": _json_ready(cleaned_run.get("bronze_snapshot")),
        "verdict": verdict,
        "checks": checks,
        "identity_anchor_delta": _json_ready(anchor_delta),
        "gold_delta": gold_delta,
        "silver_delta": silver_delta,
        "silver_widening": {
            "added_pks": _sorted_pk_lists(added_silver_pks),
            "bounded_added_pks": _sorted_pk_lists(added_silver_pks & allowed_widening_pks),
            "unbounded_added_pks": _sorted_pk_lists(unbounded_added_pks),
            "removed_pks": _sorted_pk_lists(removed_silver_pks),
            "legacy_semantic_silver_reject_pks": _sorted_pk_lists(
                legacy_semantic_rejects
            ),
            "migrated_gold_semantic_reject_pks": _sorted_pk_lists(
                cleaned_migrated_rejects
            ),
            "migrated_reason_mismatch_pks": _sorted_pk_lists(
                migrated_reason_mismatches
            ),
        },
        "reject_distribution": {
            "legacy_by_stage_class_reason": legacy_stage_distribution,
            "cleaned_by_stage_class_reason": cleaned_stage_distribution,
            "legacy_by_reason": legacy_reason_distribution,
            "cleaned_by_reason": cleaned_reason_distribution,
        },
    }


def build_parity_report(
    fixture_path: Path = DEFAULT_FIXTURE,
    *,
    root: Path = PROJECT_ROOT,
) -> JsonDict:
    """Build the deterministic parity report for a fixture file."""
    fixture = _read_json(fixture_path)
    scenarios = fixture.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("Parity fixture must contain a non-empty scenarios list")

    scenario_reports = [evaluate_scenario(deepcopy(scenario)) for scenario in scenarios]
    failing = [report["scenario_id"] for report in scenario_reports if report["verdict"] != "pass"]
    silver_widening_count = sum(
        1
        for report in scenario_reports
        if report["silver_widening"]["added_pks"]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "fixture_path": fixture_path.resolve().relative_to(root.resolve()).as_posix(),
        "overall_status": "pass" if not failing else "fail",
        "scenario_count": len(scenario_reports),
        "summary": {
            "failing_scenarios": sorted(failing),
            "gold_parity_passed": sum(
                1
                for report in scenario_reports
                if report["checks"]["gold_pk_content_hash_parity"]
            ),
            "silver_widening_scenarios": silver_widening_count,
            "violating_scenarios": len(failing),
        },
        "scenarios": sorted(scenario_reports, key=lambda item: item["scenario_id"]),
    }


def _diff_message(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> str:
    if expected == actual:
        return ""
    return (
        "Silver/Gold parity report is stale. "
        f"Expected sha payload {_canonical(expected)} but generated {_canonical(actual)}"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or validate Silver/Gold filter parity report."
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
        help="Parity fixture JSON path.",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=DEFAULT_REPORT_OUT,
        help="Report JSON output path.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the committed report differs from the generated report.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = build_parity_report(args.fixture)

    if args.check:
        if not args.report_out.exists():
            print(f"Missing parity report: {args.report_out}", file=sys.stderr)
            return 1
        existing = _read_json(args.report_out)
        message = _diff_message(existing, report)
        if message:
            print(message, file=sys.stderr)
            return 1
    else:
        _write_json(args.report_out, report)

    if report["overall_status"] != "pass":
        print(
            "Silver/Gold parity violations: "
            + ", ".join(report["summary"]["failing_scenarios"]),
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
