"""Golden fixtures for deterministic DQ rule evaluator projections."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from bioetl.domain.behavior.dq_rule_evaluator import evaluate_dq_rules_for_record
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.config.validation import (
    ConditionalValidation,
    CrossFieldValidation,
    FieldValidation,
)

pytestmark = pytest.mark.unit

FIXTURE_DIR = Path("tests/fixtures/golden/dq_rule_evaluator")
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"


def _save_fixture(name: str, payload: list[dict[str, object]]) -> None:
    fixture_path = FIXTURE_DIR / f"{name}.json"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_fixture(name: str) -> list[dict[str, object]]:
    fixture_path = FIXTURE_DIR / f"{name}.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _assert_matches_fixture(name: str, payload: list[dict[str, object]]) -> None:
    if UPDATE_SNAPSHOTS:
        _save_fixture(name, payload)
        pytest.skip(f"Updated DQ rule evaluator golden fixture {name}")

    fixture_path = FIXTURE_DIR / f"{name}.json"
    if not fixture_path.exists():
        pytest.fail(
            f"Missing DQ rule evaluator golden fixture {fixture_path}. "
            "Run with UPDATE_SNAPSHOTS=1 to create it."
        )

    assert payload == _load_fixture(name)


def _build_coercion_vocab_cross_config() -> DQConfig:
    return DQConfig(
        field_validations=(
            FieldValidation(
                field="required_field",
                validation_type="required",
                nullable=False,
            ),
            FieldValidation(
                field="component_types",
                validation_type="custom",
                validator="validate_target_component_types_json_vocab",
            ),
            FieldValidation(
                field="standard_value",
                validation_type="range",
                min_value=0,
            ),
        ),
        cross_field_validations=(
            CrossFieldValidation(
                name="all_present",
                fields=("field1", "field2"),
                condition="all_present",
                severity="error",
            ),
        ),
        conditional_validations=(
            ConditionalValidation(
                name="ic50_positive",
                condition_field="activity_type",
                condition_value="IC50",
                condition_operator="eq",
                then_validations=(
                    FieldValidation(
                        field="activity_value",
                        validation_type="range",
                        min_value=0,
                    ),
                ),
            ),
        ),
        contract_ref="chembl.activity",
        invalid_record_policy="fail",
    )


def _build_coercion_vocab_cross_record() -> dict[str, object]:
    return {
        "required_field": None,
        "field1": "present",
        "field2": None,
        "activity_type": "IC50",
        "activity_value": "-1",
        "standard_value": "-5",
        "component_types": '["PROTEIN","UNKNOWN_COMPONENT"]',
    }


def _project_outcomes(record: dict[str, object], config: DQConfig) -> list[dict[str, object]]:
    outcomes = evaluate_dq_rules_for_record(record, dq_config=config)
    return [
        {
            "rule_id": outcome.rule_id,
            "disposition": outcome.disposition.value,
            "affected_fields": list(outcome.affected_fields or ()),
            "config_path": outcome.config_path,
        }
        for outcome in outcomes
    ]


def test_coercion_vocab_cross_ordering_golden_fixture() -> None:
    config = _build_coercion_vocab_cross_config()
    record = _build_coercion_vocab_cross_record()

    _assert_matches_fixture(
        "coercion_vocab_cross_ordering",
        _project_outcomes(record, config),
    )
