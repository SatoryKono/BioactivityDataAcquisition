# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Executable contract checks for versioned run-report payloads."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema.validators import validator_for

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
CONTRACT_ROOT = ROOT / "configs" / "contracts" / "reports"
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "reports"


def validate_fixture(*, schema_name: str, fixture_name: str) -> None:
    schema = json.loads((CONTRACT_ROOT / schema_name).read_text(encoding="utf-8"))
    payload = json.loads((FIXTURE_ROOT / fixture_name).read_text(encoding="utf-8"))
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    validator_class(schema).validate(payload)


def test_pipeline_run_report_golden_matches_v1_schema() -> None:
    validate_fixture(
        schema_name="pipeline_run_report.v1.json",
        fixture_name="pipeline_run_report_golden.json",
    )


def test_chembl_assay_backfill_run_report_golden_matches_v1_schema() -> None:
    validate_fixture(
        schema_name="pipeline_run_report.v1.json",
        fixture_name="chembl_assay_backfill_run_report_golden.json",
    )


def test_workflow_run_report_golden_matches_v1_schema() -> None:
    validate_fixture(
        schema_name="workflow_run_report.v1.json",
        fixture_name="workflow_run_report_golden.json",
    )


def test_golden_json_is_canonically_ordered() -> None:
    for path in sorted(FIXTURE_ROOT.glob("*_run_report_golden.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        canonical = (
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n"
        )
        assert json.loads(canonical) == payload


@pytest.mark.parametrize("dry_run", [False, True])
def test_reconciliation_report_keeps_last_table_count_and_expiry(dry_run: bool) -> None:
    from bioetl.domain.run_reports.workflow_builder import build_workflow_run_report

    execution = [
        {
            "step_id": "load",
            "kind": "pipeline",
            "status": "success",
            "payload": {"records_gold": 983},
        },
    ]
    for index, (scanned, retained) in enumerate(((983, 550), (550, 5))):
        execution.append(
            {
                "step_id": f"reconcile-{index}",
                "kind": "transform",
                "status": "success",
                "payload": {
                    "transform_name": "reconcile_foreign_keys",
                    "source_table": "chembl.assay",
                    "source_layer": "gold",
                    "source_scope": "all_current",
                    "scanned_rows": scanned,
                    "retained_rows": retained,
                    "source_snapshot": {
                        "version": index + 1,
                        "physical_rows": 983,
                        "current_rows": retained,
                    },
                    "orphan_rows_deleted": scanned - retained,
                    "mutation_mode": "dry_run" if dry_run else "gold_scd2_expiry",
                    "dry_run": dry_run,
                },
            }
        )
    payload = build_workflow_run_report(
        identity={"workflow_name": "baseline", "status": "success"},
        plan_steps=[],
        execution_steps=execution,
    ).to_dict()
    totals = payload["totals"]
    assert totals["records_gold_loaded_sum"] == 983
    assert totals["records_gold_expired_sum"] == (0 if dry_run else 978)
    assert totals["gold_current_after_reconciliation_by_table"] == {
        "chembl.assay": None if dry_run else 5,
    }
    assert payload["execution"][1]["reconciliation"]["scanned_rows"] == 983
    schema = json.loads((CONTRACT_ROOT / "workflow_run_report.v1.json").read_text())
    validator_for(schema)(schema).validate(payload)
