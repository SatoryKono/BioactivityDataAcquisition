"""Silver/Gold filter migration parity harness contracts."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.data_quality.run_silver_gold_filter_parity import (
    build_parity_report,
    evaluate_scenario,
    main as parity_main,
)
from tests.integration.ci.reproducibility_contract_support import (
    SILVER_GOLD_PARITY_FIXTURE,
    SILVER_GOLD_PARITY_REPORT,
    build_silver_gold_parity_report,
    load_silver_gold_parity_fixture,
    load_silver_gold_parity_report,
)


pytestmark = pytest.mark.integration
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_COVERAGE_MATRIX = (
    PROJECT_ROOT / "reports" / "quality" / "contract-coverage-matrix.json"
)


def _fixture_scenario() -> dict[str, object]:
    fixture = load_silver_gold_parity_fixture()
    scenarios = fixture["scenarios"]
    assert isinstance(scenarios, list)
    return deepcopy(scenarios[0])


def test_silver_gold_filter_parity_report_matches_golden_fixture() -> None:
    generated = build_silver_gold_parity_report()
    committed = load_silver_gold_parity_report()

    assert generated == committed
    assert generated["overall_status"] == "pass"
    assert generated["summary"]["gold_parity_passed"] == 1
    assert generated["summary"]["silver_widening_scenarios"] == 1


def test_silver_gold_filter_parity_cli_check_round_trip(tmp_path: Path) -> None:
    report_out = tmp_path / "silver-gold-filter-parity-report.json"

    assert (
        parity_main(
            [
                "--fixture",
                str(SILVER_GOLD_PARITY_FIXTURE),
                "--report-out",
                str(report_out),
            ]
        )
        == 0
    )
    assert (
        parity_main(
            [
                "--fixture",
                str(SILVER_GOLD_PARITY_FIXTURE),
                "--report-out",
                str(report_out),
                "--check",
            ]
        )
        == 0
    )

    report_out.write_text('{"drift": true}\n', encoding="utf-8")

    assert (
        parity_main(
            [
                "--fixture",
                str(SILVER_GOLD_PARITY_FIXTURE),
                "--report-out",
                str(report_out),
                "--check",
            ]
        )
        == 1
    )


def test_silver_gold_filter_parity_enforces_gold_pk_content_hash_parity() -> None:
    scenario = _fixture_scenario()
    cleaned_gold = scenario["cleaned_yaml"]["gold_records"]  # type: ignore[index]
    cleaned_gold[0]["content_hash"] = "sha256:gold-a1-regression"  # type: ignore[index]

    report = evaluate_scenario(scenario)

    assert report["verdict"] == "fail"
    assert report["checks"]["gold_pk_content_hash_parity"] is False
    assert report["gold_delta"]["changed_content_hash_pks"] == [["activity", "A1"]]


def test_silver_gold_filter_parity_bounds_silver_widening_to_semantic_rejects() -> None:
    scenario = _fixture_scenario()
    cleaned_silver = scenario["cleaned_yaml"]["silver_records"]  # type: ignore[index]
    cleaned_silver.append(  # type: ignore[attr-defined]
        {
            "content_hash": "sha256:silver-a99",
            "pk": ["activity", "A99"],
        }
    )

    report = evaluate_scenario(scenario)

    assert report["verdict"] == "fail"
    assert (
        report["checks"]["silver_widening_bounded_to_legacy_semantic_rejects"] is False
    )
    assert report["silver_widening"]["unbounded_added_pks"] == [["activity", "A99"]]


def test_silver_gold_filter_parity_rejects_source_profile_drift() -> None:
    scenario = _fixture_scenario()
    source_profile = scenario["cleaned_yaml"]["source_profile"]  # type: ignore[index]
    source_profile["version"] = "2.0.0"  # type: ignore[index]

    report = evaluate_scenario(scenario)

    assert report["verdict"] == "fail"
    assert report["checks"]["same_source_profile"] is False


def test_silver_gold_filter_parity_public_builder_uses_default_fixture() -> None:
    assert (
        build_parity_report(SILVER_GOLD_PARITY_FIXTURE)
        == load_silver_gold_parity_report()
    )
    assert SILVER_GOLD_PARITY_REPORT.name == "silver-gold-filter-parity-report.json"


def test_silver_gold_filter_parity_scenarios_link_to_gold_contract_matrix() -> None:
    matrix = json.loads(CONTRACT_COVERAGE_MATRIX.read_text(encoding="utf-8"))
    rows = {
        (row["pipeline_name"], row["contract_ref"], row["registry_contract_version"])
        for row in matrix["rows"]
        if row["gold_enabled"] and row["parity_status"] == "covered"
    }

    report = load_silver_gold_parity_report()
    missing: list[str] = []
    for scenario in report["scenarios"]:
        key = (
            scenario["pipeline_name"],
            scenario["contract_ref"],
            scenario["contract_version"],
        )
        if key not in rows:
            missing.append(f"{scenario['scenario_id']}: {key}")

    assert not missing, (
        "Silver/Gold parity scenarios must map to covered gold contract rows:\n"
        + "\n".join(missing)
    )
