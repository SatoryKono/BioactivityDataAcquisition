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
"""Fail-closed residuals for #8958 domain hashing/workflow leftovers."""

from __future__ import annotations

import pytest

from bioetl.domain.config.validation import ValidationConfig
from bioetl.domain.transformations.coercion import safe_float
from bioetl.domain.transformations.hashing import (
    generate_content_hash,
    generate_entity_id,
)
from bioetl.domain.transformations.quality import calculate_dq_score
from bioetl.domain.validation.chemical import validate_molecular_weight
from bioetl.domain.workflow.config import TransformStepConfig, WorkflowRunOptionsConfig
from bioetl.domain.workflow.step_transition import WorkflowStepTransitionPolicy

pytestmark = pytest.mark.unit


class TestGenerateEntityIdNullBusinessKey:
    def test_none_business_key_falls_back_to_content_hash(self) -> None:
        record = {"chembl_id": None, "name": "aspirin"}
        entity_id = generate_entity_id(record, "chembl", id_field="chembl_id")
        content_hash = generate_content_hash(record, "chembl")
        assert entity_id == f"chembl:{content_hash[:16]}"
        assert entity_id != "chembl:None"


class TestCalculateDqScoreFailClosed:
    def test_negative_counts_raise(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            calculate_dq_score(-1, 10)
        with pytest.raises(ValueError, match="non-negative"):
            calculate_dq_score(1, -10)

    def test_valid_count_cannot_exceed_total(self) -> None:
        with pytest.raises(ValueError, match="cannot exceed"):
            calculate_dq_score(11, 10)


class TestWorkflowConfigCopiesMutables:
    def test_run_options_copy_multi_filter_and_fallback(self) -> None:
        multi = {"assay": ["A", "B"]}
        fallback = {"old": "new"}
        cfg = WorkflowRunOptionsConfig(
            multi_filter_ids=multi,
            fallback_mapping=fallback,
        )
        multi["assay"].append("C")
        fallback["extra"] = "mutated"
        assert cfg.multi_filter_ids == {"assay": ("A", "B")}
        assert cfg.fallback_mapping == {"old": "new"}

    def test_transform_step_copies_config_mapping(self) -> None:
        payload = {"threshold": 1}
        step = TransformStepConfig(
            step_id="t1",
            transform_name="normalize",
            config=payload,
        )
        payload["threshold"] = 99
        assert step.config == {"threshold": 1}


class TestWorkflowStepTransitionPolicyValidation:
    def test_unknown_disposition_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown workflow step disposition"):
            WorkflowStepTransitionPolicy(disposition="maybe", stores_output=False)

    def test_skip_cannot_store_output(self) -> None:
        with pytest.raises(ValueError, match="cannot set stores_output=True"):
            WorkflowStepTransitionPolicy(
                disposition="skip_completed",
                stores_output=True,
            )


class TestSafeFloatOverflow:
    def test_overflow_returns_default(self) -> None:
        assert safe_float("1e10000") is None
        assert safe_float("1e10000", default=0.0) == pytest.approx(0.0)


class TestMolecularWeightRoundedBounds:
    def test_compares_rounded_value_to_bounds(self) -> None:
        config = ValidationConfig(
            min_molecular_weight=0.0,
            max_molecular_weight=100.0,
            molecular_weight_precision=0,
        )
        assert validate_molecular_weight(99.4, config=config) == pytest.approx(99.0)
        assert validate_molecular_weight(99.6, config=config) is None
