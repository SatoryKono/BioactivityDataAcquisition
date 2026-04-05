"""Unit tests for config-surface derived optionality."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.core.base_transformer.optionality import (
    ConfigSurfaceOptionalityResolver,
    is_framework_managed_field,
)
from bioetl.domain.config import (
    DQConfig,
    FieldPolicyConfig,
    FieldValidation,
    KeyNullabilityRule,
)
from bioetl.domain.filtering import SilverFilterConfig


@pytest.mark.unit
def test_optionality_resolver_marks_silver_required_fields_as_non_optional() -> None:
    resolver = ConfigSurfaceOptionalityResolver.from_domain_config(
        SimpleNamespace(
            silver_filters=SilverFilterConfig(required_fields=("activity_id",)),
            dq=DQConfig(),
        )
    )

    result = resolver.resolve("activity_id")

    assert result.optional is False
    assert result.sources == ("silver_required_fields",)


@pytest.mark.unit
def test_optionality_resolver_marks_dq_required_fields_as_non_optional() -> None:
    resolver = ConfigSurfaceOptionalityResolver.from_domain_config(
        SimpleNamespace(
            silver_filters=SilverFilterConfig(required_fields=()),
            dq=DQConfig(
                field_validations=(
                    FieldValidation(
                        field="publication_year", validation_type="required"
                    ),
                )
            ),
        )
    )

    result = resolver.resolve("publication_year")

    assert result.optional is False
    assert result.sources == ("dq_required_validation",)


@pytest.mark.unit
def test_optionality_resolver_marks_dq_not_null_fields_as_non_optional() -> None:
    resolver = ConfigSurfaceOptionalityResolver.from_domain_config(
        SimpleNamespace(
            silver_filters=SilverFilterConfig(required_fields=()),
            dq=DQConfig(
                field_validations=(
                    FieldValidation(field="src_id", validation_type="not_null"),
                )
            ),
        )
    )

    result = resolver.resolve("src_id")

    assert result.optional is False
    assert result.sources == ("dq_not_null_validation",)


@pytest.mark.unit
def test_optionality_resolver_marks_nonnullable_key_fields_as_non_optional() -> None:
    resolver = ConfigSurfaceOptionalityResolver.from_domain_config(
        SimpleNamespace(
            silver_filters=SilverFilterConfig(required_fields=()),
            dq=DQConfig(
                key_nullability_rules=(
                    KeyNullabilityRule(
                        field="record_id", key_type="merge", nullable=False
                    ),
                )
            ),
        )
    )

    result = resolver.resolve("record_id")

    assert result.optional is False
    assert result.sources == ("dq_key_nullability",)


@pytest.mark.unit
def test_optionality_resolver_accumulates_multiple_sources() -> None:
    resolver = ConfigSurfaceOptionalityResolver.from_domain_config(
        SimpleNamespace(
            silver_filters=SilverFilterConfig(required_fields=("activity_id",)),
            dq=DQConfig(
                field_validations=(
                    FieldValidation(field="activity_id", validation_type="required"),
                    FieldValidation(field="activity_id", validation_type="not_null"),
                ),
                key_nullability_rules=(
                    KeyNullabilityRule(
                        field="activity_id",
                        key_type="merge",
                        nullable=False,
                    ),
                ),
            ),
        )
    )

    result = resolver.resolve("activity_id")

    assert result.optional is False
    assert result.sources == (
        "silver_required_fields",
        "dq_required_validation",
        "dq_not_null_validation",
        "dq_key_nullability",
    )


@pytest.mark.unit
def test_optionality_resolver_explicit_optional_false_overrides_default_optional() -> (
    None
):
    resolver = ConfigSurfaceOptionalityResolver.from_domain_config(
        SimpleNamespace(
            field_policy=(FieldPolicyConfig(field="curation_flag", optional=False),),
            silver_filters=SilverFilterConfig(required_fields=()),
            dq=DQConfig(),
        )
    )

    result = resolver.resolve("curation_flag")

    assert result.optional is False
    assert result.sources == ("field_policy_optional_false",)


@pytest.mark.unit
def test_optionality_resolver_explicit_optional_true_overrides_required_signals() -> (
    None
):
    resolver = ConfigSurfaceOptionalityResolver.from_domain_config(
        SimpleNamespace(
            field_policy=(FieldPolicyConfig(field="activity_id", optional=True),),
            silver_filters=SilverFilterConfig(required_fields=("activity_id",)),
            dq=DQConfig(
                field_validations=(
                    FieldValidation(field="activity_id", validation_type="required"),
                    FieldValidation(field="activity_id", validation_type="not_null"),
                ),
                key_nullability_rules=(
                    KeyNullabilityRule(
                        field="activity_id",
                        key_type="merge",
                        nullable=False,
                    ),
                ),
            ),
        )
    )

    result = resolver.resolve("activity_id")

    assert result.optional is True
    assert result.sources == ("field_policy_optional_true",)


@pytest.mark.unit
def test_optionality_resolver_defaults_to_optional_without_signals() -> None:
    resolver = ConfigSurfaceOptionalityResolver.from_domain_config(
        SimpleNamespace(
            silver_filters=SilverFilterConfig(required_fields=()),
            dq=DQConfig(),
        )
    )

    result = resolver.resolve("manual_curation_flag")

    assert result.optional is True
    assert result.sources == ("default_optional",)


@pytest.mark.unit
def test_framework_managed_fields_are_detected() -> None:
    assert is_framework_managed_field("_dq_warn") is True
    assert is_framework_managed_field("entity_id") is True
    assert is_framework_managed_field("activity_id") is False
