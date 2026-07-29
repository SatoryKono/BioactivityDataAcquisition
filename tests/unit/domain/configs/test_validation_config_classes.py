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
"""Unit tests for domain config validation classes — FieldValidation, CrossFieldValidation, etc."""

from __future__ import annotations

import pytest

from bioetl.domain.config.validation import (
    ConditionalValidation,
    CrossFieldValidation,
    FieldValidation,
)


@pytest.mark.unit
class TestFieldValidation:
    """Tests for FieldValidation config dataclass."""

    def test_creation_required_type(self) -> None:
        fv = FieldValidation(field="name", validation_type="required")
        assert fv.field == "name"
        assert fv.validation_type == "required"
        assert fv.nullable is True
        assert fv.severity == "error"

    def test_creation_range_type(self) -> None:
        fv = FieldValidation(
            field="value",
            validation_type="range",
            min_value=0.0,
            max_value=100.0,
        )
        assert fv.min_value == pytest.approx(0.0)
        assert fv.max_value == pytest.approx(100.0)

    def test_creation_pattern_type(self) -> None:
        fv = FieldValidation(
            field="doi",
            validation_type="pattern",
            pattern=r"^10\.\d{4,}",
        )
        assert fv.pattern == r"^10\.\d{4,}"

    def test_creation_enum_type(self) -> None:
        fv = FieldValidation(
            field="status",
            validation_type="enum",
            allowed=("active", "inactive"),
        )
        assert fv.allowed == ("active", "inactive")

    def test_allowed_list_frozen_to_tuple(self) -> None:
        fv = FieldValidation(
            field="status",
            validation_type="enum",
            allowed=["active", "inactive"],  # type: ignore[arg-type]
        )
        assert isinstance(fv.allowed, tuple)
        assert fv.allowed == ("active", "inactive")

    def test_field_validation__severity_default__3fa50b50(self) -> None:
        fv = FieldValidation(field="x", validation_type="required", severity="error")
        assert fv.effective_severity() == "error"
        assert fv.effective_severity(is_enricher=True) == "error"

    def test_field_validation__enricher_override__a02ba514(self) -> None:
        fv = FieldValidation(
            field="x",
            validation_type="required",
            severity="error",
            severity_enricher="warn",
        )
        assert fv.effective_severity(is_enricher=False) == "error"
        assert fv.effective_severity(is_enricher=True) == "warn"

    def test_field_validation__immutable__ca2b7f07(self) -> None:
        fv = FieldValidation(field="x", validation_type="required")
        with pytest.raises((AttributeError, TypeError)):
            fv.field = "other"  # type: ignore[misc]

    @pytest.mark.parametrize(
        "vtype",
        [
            "required",
            "not_null",
            "range",
            "pattern",
            "enum",
            "max_length",
            "not_empty_list",
            "custom",
        ],
    )
    def test_all_validation_types(self, vtype: str) -> None:
        fv = FieldValidation(field="x", validation_type=vtype)  # type: ignore[arg-type]
        assert fv.validation_type == vtype


@pytest.mark.unit
class TestCrossFieldValidation:
    """Tests for CrossFieldValidation config dataclass."""

    def test_creation_all_present(self) -> None:
        cfv = CrossFieldValidation(
            name="all_ids_present",
            fields=("doi", "pmid"),
            condition="all_present",
        )
        assert cfv.name == "all_ids_present"
        assert cfv.fields == ("doi", "pmid")
        assert cfv.condition == "all_present"
        assert cfv.severity == "error"

    def test_creation_conditional_required(self) -> None:
        cfv = CrossFieldValidation(
            name="cond_req",
            fields=("target_id", "organism"),
            condition="conditional_required",
            trigger_field="target_id",
            required_field="organism",
        )
        assert cfv.trigger_field == "target_id"
        assert cfv.required_field == "organism"

    def test_fields_list_frozen_to_tuple(self) -> None:
        cfv = CrossFieldValidation(
            name="test",
            fields=["a", "b", "c"],  # type: ignore[arg-type]
            condition="any_present",
        )
        assert isinstance(cfv.fields, tuple)
        assert cfv.fields == ("a", "b", "c")

    @pytest.mark.parametrize(
        "condition",
        [
            "all_present",
            "any_present",
            "mutually_exclusive",
            "conditional_required",
            "custom",
        ],
    )
    def test_all_condition_types(self, condition: str) -> None:
        cfv = CrossFieldValidation(
            name="test",
            fields=("a",),
            condition=condition,  # type: ignore[arg-type]
        )
        assert cfv.condition == condition

    def test_cross_field_validation__immutable__08954ce2(self) -> None:
        cfv = CrossFieldValidation(name="t", fields=("a",), condition="all_present")
        with pytest.raises((AttributeError, TypeError)):
            cfv.name = "other"  # type: ignore[misc]


@pytest.mark.unit
class TestConditionalValidation:
    """Tests for ConditionalValidation config dataclass."""

    def test_creation_simple(self) -> None:
        cv = ConditionalValidation(
            name="assay_type_b",
            condition_field="assay_type",
            condition_value="B",
        )
        assert cv.name == "assay_type_b"
        assert cv.condition_field == "assay_type"
        assert cv.condition_operator == "eq"
        assert cv.then_validations == ()

    def test_creation_with_in_operator(self) -> None:
        cv = ConditionalValidation(
            name="type_check",
            condition_field="status",
            condition_value=("active", "pending"),
            condition_operator="in",
        )
        assert cv.condition_value == ("active", "pending")
        assert cv.condition_operator == "in"

    def test_condition_value_list_frozen_to_tuple(self) -> None:
        cv = ConditionalValidation(
            name="test",
            condition_field="f",
            condition_value=["a", "b"],  # type: ignore[arg-type]
        )
        assert isinstance(cv.condition_value, tuple)

    def test_with_then_validations(self) -> None:
        fv = FieldValidation(field="target_id", validation_type="required")
        cv = ConditionalValidation(
            name="test",
            condition_field="assay_type",
            condition_value="B",
            then_validations=(fv,),
        )
        assert len(cv.then_validations) == 1
        assert cv.then_validations[0].field == "target_id"

    def test_then_validations_list_frozen(self) -> None:
        fv = FieldValidation(field="x", validation_type="required")
        cv = ConditionalValidation(
            name="test",
            condition_field="f",
            condition_value="v",
            then_validations=[fv],  # type: ignore[arg-type]
        )
        assert isinstance(cv.then_validations, tuple)

    @pytest.mark.parametrize("op", ["eq", "ne", "in", "not_in"])
    def test_all_operators(self, op: str) -> None:
        cv = ConditionalValidation(
            name="test",
            condition_field="f",
            condition_value="v",
            condition_operator=op,  # type: ignore[arg-type]
        )
        assert cv.condition_operator == op

    def test_conditional_validation__immutable__9346e1cb(self) -> None:
        cv = ConditionalValidation(name="t", condition_field="f", condition_value="v")
        with pytest.raises((AttributeError, TypeError)):
            cv.name = "other"  # type: ignore[misc]
