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
"""Property-based determinism tests for DQ rule evaluator orchestration."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.dq_rule_evaluator import evaluate_dq_rules_for_record
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.config.validation import (
    ConditionalValidation,
    CrossFieldValidation,
    FieldValidation,
)
from bioetl.domain.types.dq_contracts import DQDisposition

pytestmark = pytest.mark.unit

try:
    from hypothesis import HealthCheck, given, settings
    from hypothesis import strategies as st

    HAS_HYPOTHESIS = True
except ImportError:  # pragma: no cover - exercised when hypothesis is absent
    HAS_HYPOTHESIS = False


def _build_property_config() -> DQConfig:
    return DQConfig(
        field_validations=(
            FieldValidation(
                field="required_field",
                validation_type="required",
                nullable=False,
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


def _project_outcomes(
    record: dict[str, object], config: DQConfig
) -> list[tuple[str, str, tuple[str, ...], str | None]]:
    outcomes = evaluate_dq_rules_for_record(record, dq_config=config)
    return [
        (
            outcome.rule_id,
            outcome.disposition.value,
            tuple(outcome.affected_fields or ()),
            outcome.config_path,
        )
        for outcome in outcomes
    ]


_RECORD_STRATEGY = st.fixed_dictionaries(
    {
        "required_field": st.one_of(st.none(), st.text(min_size=1, max_size=8)),
        "field1": st.one_of(st.none(), st.text(min_size=1, max_size=8)),
        "field2": st.one_of(st.none(), st.text(min_size=1, max_size=8)),
        "activity_type": st.sampled_from(["IC50", "EC50", "Ki", ""]),
        "activity_value": st.one_of(
            st.none(),
            st.integers(min_value=-100, max_value=100),
            st.text(min_size=1, max_size=6),
        ),
        "standard_value": st.one_of(
            st.none(),
            st.integers(min_value=-100, max_value=100),
            st.text(min_size=1, max_size=6),
        ),
    }
)

_FUZZ_RECORDS: tuple[dict[str, object], ...] = (
    {
        "required_field": None,
        "field1": "present",
        "field2": None,
        "activity_type": "IC50",
        "activity_value": "-1",
        "standard_value": "-5",
    },
    {
        "required_field": "ok",
        "field1": "a",
        "field2": "b",
        "activity_type": "EC50",
        "activity_value": 42,
        "standard_value": "10",
    },
    {
        "required_field": "",
        "field1": None,
        "field2": "only-one",
        "activity_type": "IC50",
        "activity_value": 0,
        "standard_value": None,
    },
)


if HAS_HYPOTHESIS:

    @pytest.mark.hypothesis
    @settings(
        deadline=None,
        max_examples=25,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(record=_RECORD_STRATEGY)
    def test_evaluate_dq_rules_is_idempotent(record: dict[str, object]) -> None:
        config = _build_property_config()
        first = _project_outcomes(record, config)
        second = _project_outcomes(record, config)
        assert first == second

    @pytest.mark.hypothesis
    @settings(
        deadline=None,
        max_examples=25,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(record=_RECORD_STRATEGY)
    def test_evaluate_dq_rules_preserves_stable_family_ordering(
        record: dict[str, object],
    ) -> None:
        config = _build_property_config()
        outcomes = evaluate_dq_rules_for_record(record, dq_config=config)
        rule_families = [outcome.rule_id.split(".", 1)[0] for outcome in outcomes]
        family_rank = {"field": 0, "cross": 1, "conditional": 2}
        ranks = [family_rank.get(family, 99) for family in rule_families]
        assert ranks == sorted(ranks)


@pytest.mark.parametrize("record", _FUZZ_RECORDS)
def test_evaluate_dq_rules_idempotent_without_hypothesis(
    record: dict[str, object],
) -> None:
    if HAS_HYPOTHESIS:
        pytest.skip("Hypothesis-backed property tests cover this path")
    config = _build_property_config()
    assert _project_outcomes(record, config) == _project_outcomes(record, config)


@pytest.mark.parametrize("record", _FUZZ_RECORDS)
def test_evaluate_dq_rules_stable_ordering_without_hypothesis(
    record: dict[str, object],
) -> None:
    if HAS_HYPOTHESIS:
        pytest.skip("Hypothesis-backed property tests cover this path")
    config = _build_property_config()
    outcomes = evaluate_dq_rules_for_record(record, dq_config=config)
    rule_families = [outcome.rule_id.split(".", 1)[0] for outcome in outcomes]
    family_rank = {"field": 0, "cross": 1, "conditional": 2}
    ranks = [family_rank.get(family, 99) for family in rule_families]
    assert ranks == sorted(ranks)


def test_known_violation_projection_matches_expected_dispositions() -> None:
    config = _build_property_config()
    record = {
        "required_field": None,
        "field1": "present",
        "field2": None,
        "activity_type": "IC50",
        "activity_value": "-1",
        "standard_value": "-5",
    }
    projected = _project_outcomes(record, config)
    assert projected[0][1] == DQDisposition.FAIL.value
    assert projected[-1][0] == "conditional.ic50_positive.activity_value.range"
