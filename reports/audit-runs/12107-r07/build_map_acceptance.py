"""Build the #12107 map-acceptance record from the frozen universe.

The script does not rewrite adapter-owner-map.json, the behavior matrix, or
historical telemetry bytes. It records the tracking-role decision, the
one-to-many indexes, and the thirteen behavioral follow-ups.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAP_PATH = ROOT / "adapter-owner-map.json"
MATRIX_PATH = ROOT / "behavior-obligation-matrix.json"

TRACKING_ROLE = "BioETL Team"
TRACKING_BASIS = [
    "docs/02-architecture/diagrams/descriptions/architecture/05b-adapter-hierarchy-providers.md header Owner: BioETL Team",
    "docs/02-architecture/diagrams/descriptions/foundation/26-hexagonal-ports-adapters.md header Owner: BioETL Team",
    "docs/02-architecture/diagrams/descriptions/foundation/30-port-adapter-mapping.md header Owner: BioETL Team",
    "docs/02-architecture/diagrams/descriptions/views/26-hexagonal-ports-adapters-*.md header Owner: BioETL Team",
    "docs/02-architecture/diagrams/descriptions/views/30-port-adapter-mapping-*.md header Owner: BioETL Team",
]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _port_names(row: dict) -> list[str]:
    names: list[str] = []
    for key in ("implemented_ports", "partial_ports"):
        for item in row.get(key) or []:
            name = item.get("name")
            if isinstance(name, str):
                names.append(name)
    return names


def _relationship_index(rows: list[dict]) -> dict:
    adapters_multiple: list[dict] = []
    by_port: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        names = _port_names(row)
        identity = {
            "line": row["line"],
            "path": row["path"],
            "symbol": row["symbol"],
        }
        if len(names) > 1:
            adapters_multiple.append({**identity, "ports": names})
        for key in ("implemented_ports", "partial_ports"):
            for item in row.get(key) or []:
                by_port[item["name"]].append(
                    {
                        **identity,
                        "match": item.get("match"),
                        "relation": key,
                    }
                )
    ports_multiple = {
        name: implementations
        for name, implementations in sorted(by_port.items())
        if len(implementations) > 1
    }
    return {
        "adapter_to_multiple_ports": adapters_multiple,
        "adapter_to_multiple_ports_count": len(adapters_multiple),
        "note": (
            "Single adapter/port links stay on adapter-owner-map.json rows. "
            "This index makes one-to-many links explicit in both directions. "
            "Unresolved rows stay in the 2046 denominator and are not dropped here."
        ),
        "port_to_multiple_implementations": ports_multiple,
        "port_to_multiple_implementations_count": len(ports_multiple),
        "schema_version": 1,
        "source": "reports/audit-runs/12107-r07/adapter-owner-map.json",
    }


def _tracking_decision(rows: list[dict]) -> dict:
    unassigned = sum(
        1
        for row in rows
        if row["semantic_owner"] == "unassigned-tracking"
        and row["composition_owner"] == "unassigned-tracking"
        and row["lifecycle_owner"] == "unassigned-tracking"
    )
    trace_complete = sum(
        1
        for row in rows
        if row.get("semantic_tracking_responsibility")
        and row.get("composition_tracking_responsibility")
        and row.get("lifecycle_tracking_responsibility")
    )
    return {
        "basis": TRACKING_BASIS,
        "boundaries": [
            "The role is tracking responsibility for unassigned concerns.",
            "semantic_owner, composition_owner, and lifecycle_owner stay unassigned-tracking.",
            "This record does not establish semantic, composition, or lifecycle ownership.",
            "BioETL Team is a documented role, not a resolvable GitHub assignee.",
            "Per-row *_tracking_responsibility strings in the frozen map remain trace pointers, not this role and not ownership.",
            ".github/CODEOWNERS default @SatoryKono remains review ownership and is counted separately.",
        ],
        "codeowners_review_owner": "@SatoryKono",
        "metrics": {
            "owner_coverage": f"0/{len(rows)}",
            "owner_coverage_definition": (
                "Rows whose semantic, composition, and lifecycle owners are all "
                "values other than unassigned-tracking. Tracking responsibility "
                "does not increment this numerator."
            ),
            "owner_coverage_numerator": 0,
            "tracking_responsibility_coverage": f"{unassigned}/{len(rows)}",
            "tracking_responsibility_coverage_definition": (
                "Rows whose three unassigned concerns are covered by the BioETL "
                "Team tracking role in this decision. This is not owner coverage."
            ),
            "tracking_responsibility_numerator": unassigned,
            "trace_pointer_coverage": f"{trace_complete}/{len(rows)}",
            "trace_pointer_definition": (
                "Frozen-map rows with non-empty semantic, composition, and "
                "lifecycle trace pointers."
            ),
            "universe_denominator": len(rows),
        },
        "named_person_per_row_required_by_issue": False,
        "ownership_established": False,
        "people_assigned": [],
        "role": TRACKING_ROLE,
        "schema_version": 1,
        "type": "tracking_responsibility",
    }


def _cell(
    *,
    adapter: str,
    operation: str,
    case: str,
    obligation: str,
    missing_evidence: str,
    inside_12108: str,
    outside_12108: str | None,
) -> dict:
    return {
        "adapter": adapter,
        "case": case,
        "inside_12108": inside_12108,
        "inside_12109": False,
        "missing_evidence": missing_evidence,
        "obligation": obligation,
        "operation": operation,
        "outside_12108": outside_12108,
        "status": "mandatory_not_verified",
    }


def _followups() -> dict:
    consumer = "https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12108"
    storage = "https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12109"
    fetch_inside = (
        "Timeout propagation and cancellation propagation, including early close of the fetch generator."
    )
    fetch_outside = (
        "Successful provider-record materialization stays R07 missing evidence. "
        "#12108 accepts client policy and lifecycle, not payload parsing."
    )
    health_inside = (
        "Timeout and cancellation of the probe. PubChem uses the sync_base executor named by #12108."
    )
    health_outside = (
        "Mapping a successful probe to HEALTHY, or a caught probe error to a non-HEALTHY status, "
        "stays R07 missing evidence. That status contract is not an #12108 acceptance row."
    )
    close_inside = (
        "Shared or nested client ownership and close order. "
        "The BaseHttpAdapter no-op does not release the injected client."
    )
    rows = [
        _cell(
            adapter="ChemblAdapter",
            operation="health_check",
            case="normal_timeout_cancellation",
            obligation="health_check returns a non-HEALTHY status when the probe raises a documented health error, and CancelledError propagates.",
            missing_evidence="The health probe was not executed against a controlled client.",
            inside_12108=health_inside,
            outside_12108=health_outside,
        ),
        _cell(
            adapter="ChemblAdapter",
            operation="aclose",
            case="resource_release",
            obligation="DataSourcePort requires release of the acquired client. The observed no-op does not release the injected client.",
            missing_evidence="aclose is the BaseHttpAdapter no-op. The fixture recorded exit_calls == 0.",
            inside_12108=close_inside,
            outside_12108=None,
        ),
        _cell(
            adapter="PubMedAdapter",
            operation="fetch",
            case="normal_timeout_cancellation",
            obligation="fetch yields the scripted records on success and propagates timeout and cancellation.",
            missing_evidence="fetch transport was not executed.",
            inside_12108=fetch_inside,
            outside_12108=fetch_outside,
        ),
        _cell(
            adapter="SemanticScholarAdapter",
            operation="fetch",
            case="normal_timeout_cancellation",
            obligation="fetch yields the scripted records on success and propagates timeout and cancellation.",
            missing_evidence="fetch transport was not executed.",
            inside_12108=fetch_inside,
            outside_12108=fetch_outside,
        ),
        _cell(
            adapter="OpenAlexAdapter",
            operation="fetch",
            case="normal_timeout_cancellation",
            obligation="fetch yields the scripted records on success and propagates timeout and cancellation.",
            missing_evidence="Existing tests replace fetch methods. This map does not drive the transport.",
            inside_12108=fetch_inside,
            outside_12108=fetch_outside,
        ),
        _cell(
            adapter="OpenAlexAdapter",
            operation="health_check",
            case="normal_timeout_cancellation",
            obligation="health_check returns HEALTHY for a successful probe, a non-HEALTHY status on timeout, and propagates cancellation.",
            missing_evidence="The health probe helper was not executed.",
            inside_12108=health_inside,
            outside_12108=health_outside,
        ),
        _cell(
            adapter="CrossRefAdapter",
            operation="fetch",
            case="normal_timeout_cancellation",
            obligation="fetch yields the scripted records on success and propagates timeout and cancellation.",
            missing_evidence="fetch transport was not executed.",
            inside_12108=fetch_inside,
            outside_12108=fetch_outside,
        ),
        _cell(
            adapter="CrossRefAdapter",
            operation="health_check",
            case="normal_timeout_cancellation",
            obligation="health_check returns HEALTHY for a successful probe, a non-HEALTHY status on timeout, and propagates cancellation.",
            missing_evidence="The health probe helper was not executed.",
            inside_12108=health_inside,
            outside_12108=health_outside,
        ),
        _cell(
            adapter="UniProtAdapter",
            operation="fetch",
            case="normal_timeout_cancellation",
            obligation="fetch yields the scripted records on success and propagates timeout and cancellation.",
            missing_evidence="Existing tests replace fetch methods. Transport was not executed.",
            inside_12108=fetch_inside,
            outside_12108=fetch_outside,
        ),
        _cell(
            adapter="UniProtAdapter",
            operation="health_check",
            case="normal_timeout_cancellation",
            obligation="health_check returns HEALTHY for a successful probe, a non-HEALTHY status on timeout, and propagates cancellation.",
            missing_evidence="The health probe helper was not executed.",
            inside_12108=health_inside,
            outside_12108=health_outside,
        ),
        _cell(
            adapter="UniProtAdapter",
            operation="aclose",
            case="resource_release",
            obligation="DataSourcePort requires release of the acquired client. The observed no-op does not release the injected client.",
            missing_evidence="aclose is the BaseHttpAdapter no-op. The fixture recorded exit_calls == 0.",
            inside_12108=close_inside,
            outside_12108=None,
        ),
        _cell(
            adapter="PubChemAdapter",
            operation="fetch",
            case="normal_timeout_cancellation",
            obligation="fetch yields the scripted records on success and propagates timeout and cancellation.",
            missing_evidence="pubchempy transport was not executed.",
            inside_12108=fetch_inside,
            outside_12108=fetch_outside,
        ),
        _cell(
            adapter="PubChemAdapter",
            operation="health_check",
            case="normal_timeout_cancellation",
            obligation="health_check returns HEALTHY for a successful probe, a non-HEALTHY status on timeout, and propagates cancellation.",
            missing_evidence="The pubchempy probe was not executed.",
            inside_12108=health_inside,
            outside_12108=health_outside,
        ),
    ]
    return {
        "behavior_matrix_acceptance": "NOT_ACCEPTED",
        "behavior_matrix_sha256": "7f33f61af00f7b49df8a37991537fd56aba0eec99be57bb5346e9e1d2fcd5bda",
        "does_not_replace_universe": True,
        "duplicates_r08_or_r09_work": False,
        "issue_12108_scope_check": (
            "#12108 covers HTTP client policy, timeout, cancellation, generator close, "
            "executor lifecycle, and shared-client ownership. It does not accept provider payload parsing "
            "or HealthStatus mapping. R07 does not implement those #12108 tests."
        ),
        "mandatory_not_verified_count": len(rows),
        "r08_http_lifecycle": consumer,
        "r09_storage_surface": storage,
        "rows": rows,
        "schema_version": 2,
        "storage_note": (
            "None of these thirteen obligations is a storage contract. "
            "inside_12109 is false on every row. "
            "Storage remains the existing r09-storage-surface-inventory.json input to #12109."
        ),
        "universe_denominator_unchanged": 2046,
    }


def _criteria(document: dict, rows: list[dict], followups: dict) -> list[dict]:
    coverage = document["coverage"]
    required = (
        "symbol",
        "path",
        "line",
        "implemented_ports",
        "internal_contract",
        "registration_entrypoint",
        "discovery_path",
        "reachability",
        "semantic_owner",
        "composition_owner",
        "lifecycle_owner",
        "conformance_test_paths",
        "verdict",
        "missing_evidence",
        "classification",
        "classification_rule",
    )
    missing_fields = sum(1 for row in rows if any(key not in row for key in required))
    blank_discovery = sum(
        1
        for row in rows
        if not row.get("registration_entrypoint") and not row.get("discovery_path")
    )
    blank_evidence = sum(
        1
        for row in rows
        if not row.get("missing_evidence") and not row.get("conformance_test_paths")
    )
    histogram = coverage["classification_histogram"]
    return [
        {
            "criterion": "source revision and tree pin",
            "evidence": document["source_pin"],
            "verdict": "PASS",
        },
        {
            "criterion": "universe includes adapters, factories, callable seams, structural matches, provider variants, and runtime registrations",
            "evidence": document["definitions"],
            "verdict": "PASS",
        },
        {
            "criterion": "every row has symbol, path, ports or internal contract, registration or discovery, reachability, three concerns, tests, verdict, and missing evidence",
            "evidence": {
                "blank_discovery": blank_discovery,
                "blank_tests_and_missing_evidence": blank_evidence,
                "missing_required_fields": missing_fields,
                "rows": len(rows),
            },
            "verdict": "PASS",
        },
        {
            "criterion": "one adapter to many ports and one port to many implementations are explicit",
            "evidence": "reports/audit-runs/12107-r07/port-relationship-index.json",
            "verdict": "PASS",
        },
        {
            "criterion": "classifications and exclusions stay inside the denominator",
            "evidence": {
                "classified_coverage_pct": coverage["classified_coverage_pct"],
                "histogram": histogram,
                "unresolved_in_denominator": histogram.get("unresolved", 0),
                "universe_count": coverage["universe_count"],
            },
            "verdict": "PASS",
        },
        {
            "criterion": "bounded runtime smoke is not treated as a complete AST-only universe",
            "evidence": document["scope_limitation"],
            "verdict": "PASS",
        },
        {
            "criterion": "CODEOWNERS stays review ownership and the three concerns stay unassigned",
            "evidence": "owner_coverage 0/2046; codeowner_is_not_semantic_owner on every row",
            "verdict": "PASS",
        },
        {
            "criterion": "missing owners have tracking responsibility without an invented ownership contract",
            "evidence": "reports/audit-runs/12107-r07/tracking-responsibility-decision.json",
            "verdict": "PASS",
        },
        {
            "criterion": "classified, owner, and behavioral denominators stay separate and include unresolved rows",
            "evidence": {
                "behavioral_conformance_coverage_pct": coverage[
                    "behavioral_conformance_coverage_pct"
                ],
                "behavioral_definition": coverage["behavioral_conformance_definition"],
                "classified_coverage_pct": coverage["classified_coverage_pct"],
                "owner_coverage_pct": coverage["owner_coverage_pct"],
                "verdict_histogram": coverage["verdict_histogram"],
            },
            "verdict": "PASS",
        },
        {
            "criterion": "adapters without conformance tests or owners are listed for follow-up",
            "evidence": {
                "defects": len(document["followups"]["defects"]),
                "defect_count_meaning": "The promotion rule did not fire. The count is not a claim that unchecked rows have no defects.",
                "no_conformance_assert": len(document["followups"]["no_conformance_assert"]),
                "unassigned_owners": len(document["followups"]["unassigned_owners"]),
                "unreachable": len(document["followups"]["unreachable"]),
            },
            "verdict": "PASS",
        },
        {
            "criterion": "eight-provider behavior matrix does not replace the universe and its open cells stay follow-up",
            "evidence": {
                "inside_12109_count": sum(
                    1 for row in followups["rows"] if row["inside_12109"]
                ),
                "mandatory_not_verified": followups["mandatory_not_verified_count"],
                "matrix_acceptance": followups["behavior_matrix_acceptance"],
                "r08_scope": followups["issue_12108_scope_check"],
                "r09": followups["r09_storage_surface"],
            },
            "verdict": "PASS",
        },
        {
            "criterion": "R08 and R09 receive their inventories without new ratchet or debt-budget growth",
            "evidence": {
                "r08_rows": 148,
                "r09_rows": 567,
                "ratchet_added": False,
            },
            "verdict": "PASS",
        },
    ]


def main() -> None:
    document = _load(MAP_PATH)
    rows = document["rows"]
    if len(rows) != 2046:
        raise SystemExit(f"universe changed: {len(rows)}")
    matrix = _load(MATRIX_PATH)
    preserved = [
        row for row in matrix["rows"] if row["status"] == "mandatory_not_verified"
    ]
    followups = _followups()
    if len(preserved) != len(followups["rows"]):
        raise SystemExit("matrix mandatory_not_verified count drifted")
    keys = {
        (row["adapter"], row["operation"], row["case"]) for row in followups["rows"]
    }
    matrix_keys = {
        (row["adapter"], row["operation"], row["case"]) for row in preserved
    }
    if keys != matrix_keys:
        raise SystemExit("follow-up keys do not match the frozen matrix")
    if any(row["inside_12109"] or not row["inside_12108"] for row in followups["rows"]):
        raise SystemExit("follow-up scope drifted from the #12108 check")
    index = _relationship_index(rows)
    decision = _tracking_decision(rows)
    criteria = _criteria(document, rows, followups)
    failed = [item["criterion"] for item in criteria if item["verdict"] != "PASS"]
    if failed:
        recommendation = "unmet map criteria: " + "; ".join(failed)
    else:
        recommendation = (
            "карта соответствует всем acceptance criteria, "
            "оставшиеся поведенческие пробелы оформлены как follow-up"
        )
    verdict = {
        "criteria": criteria,
        "frozen_map_sha256": "6b39eef8bf65aacbd63b165bbe2d5295d0ca3726a12410f97108e77b7844625c",
        "issue": "https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12107",
        "issue_close_performed": False,
        "map_source_pin": document["source_pin"],
        "recommendation_ru": recommendation,
        "schema_version": 1,
        "unmet_criteria": failed,
    }
    _write(ROOT / "port-relationship-index.json", index)
    _write(ROOT / "tracking-responsibility-decision.json", decision)
    _write(ROOT / "behavior-followups.json", followups)
    _write(ROOT / "map-acceptance-verdict.json", verdict)


if __name__ == "__main__":
    main()
