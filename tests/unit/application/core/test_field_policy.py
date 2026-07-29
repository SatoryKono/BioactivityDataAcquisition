# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for resolved structural field policy overlays."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.core.base_transformer.field_policy import FieldPolicyResolver
from bioetl.domain.config import DQConfig, FieldPolicyConfig
from bioetl.domain.filtering import SilverFilterConfig


@pytest.mark.unit
def test_field_policy_resolver_falls_back_to_derived_optionality() -> None:
    resolver = FieldPolicyResolver.from_domain_config(
        SimpleNamespace(
            silver_filters=SilverFilterConfig(required_fields=("activity_id",)),
            dq=DQConfig(),
        )
    )

    result = resolver.resolve("activity_id")

    assert result.optional is False
    assert result.optional_sources == ("silver_required_fields",)
    assert result.empty_as_missing is None
    assert result.coercion_policy == "default"
    assert result.boolean_true_values == ()
    assert result.boolean_false_values == ()


@pytest.mark.unit
def test_field_policy_resolver_includes_explicit_overlay_values() -> None:
    resolver = FieldPolicyResolver.from_domain_config(
        SimpleNamespace(
            field_policy=(
                FieldPolicyConfig(
                    field="reviewed",
                    optional=True,
                    empty_as_missing=True,
                    coercion_policy="no_string_coercion",
                    boolean_true_values=("yes", "да"),
                    boolean_false_values=("no", "нет"),
                ),
            ),
            silver_filters=SilverFilterConfig(required_fields=("reviewed",)),
            dq=DQConfig(),
        )
    )

    result = resolver.resolve("reviewed")

    assert result.optional is True
    assert result.optional_sources == ("field_policy_optional_true",)
    assert result.empty_as_missing is True
    assert result.coercion_policy == "no_string_coercion"
    assert result.boolean_true_values == ("yes", "да")
    assert result.boolean_false_values == ("no", "нет")


@pytest.mark.unit
def test_field_policy_resolver_falls_back_to_default_for_unknown_coercion_policy() -> (
    None
):
    resolver = FieldPolicyResolver.from_domain_config(
        SimpleNamespace(
            field_policy=(
                SimpleNamespace(
                    field="reviewed",
                    optional=True,
                    coercion_policy="unexpected_mode",
                ),
            ),
            silver_filters=SilverFilterConfig(required_fields=("reviewed",)),
            dq=DQConfig(),
        )
    )

    result = resolver.resolve("reviewed")

    assert result.coercion_policy == "default"
