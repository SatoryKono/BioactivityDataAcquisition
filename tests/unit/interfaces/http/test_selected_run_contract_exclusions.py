"""Phase 3a §3.1 — contract_exclusions_* and records_in on selected-run-status."""

from __future__ import annotations

from typing import Any

import pytest

from bioetl.interfaces.http._selected_run_contract_exclusions import (
    attach_contract_fields,
    evaluate_contract_exclusions,
    extract_records_in,
)
from bioetl.interfaces.http.selected_run_status import (
    load_selected_run_status,
    unavailable_status,
)
from tests.unit.interfaces.http.test_selected_run_status import persist, report

pytestmark = pytest.mark.unit


def _full_funnel(*, excluded: int = 0, bronze_out: int = 100) -> list[dict[str, Any]]:
    def stage(
        stage_id: str, records_in: int, records_out: int, rem: int = 0
    ) -> dict[str, Any]:
        removals = (
            [{"outcome": "excluded_by_contract", "reason_code": "x", "count": rem}]
            if rem
            else []
        )
        return {
            "stage_id": stage_id,
            "records_in": records_in,
            "records_out": records_out,
            "tracking": "full",
            "removals": removals,
        }

    return [
        stage("bronze", bronze_out, bronze_out),
        stage("silver", bronze_out, bronze_out, rem=excluded),
        stage("gold", bronze_out, bronze_out - excluded),
    ]


def test_unknown_without_pipeline_config() -> None:
    fields = evaluate_contract_exclusions("no_such_pipeline", _full_funnel())
    assert fields == {
        "contract_exclusions_status": "UNKNOWN",
        "contract_exclusions_rate": None,
        "contract_exclusions_soft_limit": None,
        "contract_exclusions_hard_limit": None,
    }


def test_path_traversal_pipeline_segments_stay_unknown() -> None:
    fields = evaluate_contract_exclusions("../x_../../y", _full_funnel(excluded=50))
    assert fields == {
        "contract_exclusions_status": "UNKNOWN",
        "contract_exclusions_rate": None,
        "contract_exclusions_soft_limit": None,
        "contract_exclusions_hard_limit": None,
    }


def test_ok_warn_crit_boundaries_for_chembl_activity() -> None:
    # chembl_activity soft=0.05 hard=0.5
    ok = evaluate_contract_exclusions("chembl_activity", _full_funnel(excluded=4))
    assert ok["contract_exclusions_status"] == "OK"
    assert ok["contract_exclusions_rate"] == pytest.approx(0.04)
    assert ok["contract_exclusions_soft_limit"] == pytest.approx(0.05)
    assert ok["contract_exclusions_hard_limit"] == pytest.approx(0.5)

    warn = evaluate_contract_exclusions("chembl_activity", _full_funnel(excluded=5))
    assert warn["contract_exclusions_status"] == "WARN"
    assert warn["contract_exclusions_rate"] == pytest.approx(0.05)

    crit = evaluate_contract_exclusions("chembl_activity", _full_funnel(excluded=50))
    assert crit["contract_exclusions_status"] == "CRIT"
    assert crit["contract_exclusions_rate"] == pytest.approx(0.5)


def test_four_stage_funnel_with_extract_computes_rate() -> None:
    """Saved reports include extract; rate still uses bronze/silver/gold only."""
    funnel = [
        {
            "stage_id": "extract",
            "records_in": 120,
            "records_out": 100,
            "tracking": "full",
            "removals": [],
        },
        *_full_funnel(excluded=50, bronze_out=100),
    ]
    fields = evaluate_contract_exclusions("chembl_activity", funnel)
    assert fields["contract_exclusions_status"] == "CRIT"
    assert fields["contract_exclusions_rate"] == pytest.approx(0.5)


def test_incomplete_funnel_keeps_limits_but_unknown_rate() -> None:
    fields = evaluate_contract_exclusions(
        "chembl_activity",
        [
            {
                "stage_id": "bronze",
                "records_in": 10,
                "records_out": 10,
                "tracking": "full",
                "removals": [],
            }
        ],
    )
    assert fields["contract_exclusions_status"] == "UNKNOWN"
    assert fields["contract_exclusions_rate"] is None
    assert fields["contract_exclusions_soft_limit"] == pytest.approx(0.05)
    assert fields["contract_exclusions_hard_limit"] == pytest.approx(0.5)


def test_extract_records_in_prefers_bronze() -> None:
    assert extract_records_in(_full_funnel(bronze_out=42)) == 42
    assert extract_records_in(None) is None
    assert (
        extract_records_in(
            [
                {
                    "stage_id": "extract",
                    "records_in": 7,
                    "records_out": 7,
                    "tracking": "full",
                    "removals": [],
                }
            ]
        )
        == 7
    )


def test_attach_and_saved_status_expose_fields(tmp_path) -> None:
    from bioetl.domain.run_reports.models import (
        BalanceStatus,
        ReasonRemoval,
        StageFunnelRow,
        TrackingCoverage,
    )

    original = report()
    funnel = (
        StageFunnelRow(
            stage_id="bronze",
            records_in=100,
            records_out=100,
            removals=(),
            removed_total=0,
            balance_status=BalanceStatus.OK,
            tracking=TrackingCoverage.FULL,
        ),
        StageFunnelRow(
            stage_id="silver",
            records_in=100,
            records_out=100,
            removals=(
                ReasonRemoval(
                    outcome="excluded_by_contract", reason_code="x", count=10
                ),
            ),
            removed_total=10,
            balance_status=BalanceStatus.OK,
            tracking=TrackingCoverage.FULL,
        ),
        StageFunnelRow(
            stage_id="gold",
            records_in=100,
            records_out=90,
            removals=(),
            removed_total=0,
            balance_status=BalanceStatus.OK,
            tracking=TrackingCoverage.FULL,
        ),
    )
    from dataclasses import replace

    persist(tmp_path, replace(original, funnel=funnel))
    result = load_selected_run_status(
        pipeline="chembl_activity", run_id="run-a", root=tmp_path
    )
    assert result["records_in"] == 100
    assert result["contract_exclusions_status"] == "WARN"
    assert result["contract_exclusions_rate"] == pytest.approx(0.1)
    assert result["contract_exclusions_soft_limit"] == pytest.approx(0.05)
    assert result["contract_exclusions_hard_limit"] == pytest.approx(0.5)


def test_unavailable_payload_has_null_contract_fields() -> None:
    # Pipeline with DQ config: limits present, rate null without funnel.
    known = unavailable_status(
        "chembl_activity", "-", "НЕТ ЗАПУСКОВ", "no_runs_in_scope"
    )
    assert known["contract_exclusions_status"] == "UNKNOWN"
    assert known["contract_exclusions_rate"] is None
    assert known["contract_exclusions_soft_limit"] == pytest.approx(0.05)
    assert known["contract_exclusions_hard_limit"] == pytest.approx(0.5)
    assert known["records_in"] is None
    # Pipeline without DQ config: all nulls.
    unknown = unavailable_status(
        "no_such_pipeline", "-", "НЕТ ЗАПУСКОВ", "no_runs_in_scope"
    )
    assert unknown["contract_exclusions_soft_limit"] is None
    assert unknown["contract_exclusions_hard_limit"] is None
    assert unknown["records_in"] is None
    enriched = attach_contract_fields(dict(unknown))
    assert enriched["records_in"] is None
