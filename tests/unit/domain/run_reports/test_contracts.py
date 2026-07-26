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
