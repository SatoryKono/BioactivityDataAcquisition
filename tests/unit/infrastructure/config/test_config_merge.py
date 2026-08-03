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
"""Unit tests for shared config_merge utility."""

from __future__ import annotations

import pytest

from typing import Any

from bioetl.infrastructure.config_merge import config_merge


pytestmark = pytest.mark.unit


def test_default_merge_overrides_scalars_and_lists() -> None:
    base = {
        "a": 1,
        "nested": {"x": 1, "y": 2},
        "items": [1, 2, 3],
    }
    override = {
        "a": 2,
        "nested": {"y": 9, "z": 3},
        "items": [4, 5],
    }

    result = config_merge(base, override)

    assert result["a"] == 2
    assert result["nested"] == {"x": 1, "y": 9, "z": 3}
    assert result["items"] == [4, 5]


def test_concat_keys_deduplicate_string_lists() -> None:
    base = {"gold_filters": {"required_fields": ["a", "b"]}}
    override = {"gold_filters": {"required_fields": ["b", "c"]}}

    result = config_merge(
        base,
        override,
        list_concat_keys=frozenset({"required_fields"}),
    )

    assert result["gold_filters"]["required_fields"] == ["a", "b", "c"]


def test_concat_keys_concatenate_non_string_lists() -> None:
    base = {"nested": {"nums": [1, 2]}}
    override = {"nested": {"nums": [3]}}

    result = config_merge(
        base,
        override,
        list_concat_keys=frozenset({"nums"}),
    )

    assert result["nested"]["nums"] == [1, 2, 3]


def test_custom_concat_list_merger_is_applied() -> None:
    def reverse_concat(base: list[Any], override: list[Any], _key: str) -> list[Any]:
        return [*override, *base]

    base = {"nested": {"values": [1, 2]}}
    override = {"nested": {"values": [3]}}

    result = config_merge(
        base,
        override,
        list_concat_keys=frozenset({"values"}),
        concat_list_merger=reverse_concat,
    )

    assert result["nested"]["values"] == [3, 1, 2]


def test_list_merger_resolver_has_priority_over_concat_keys() -> None:
    def resolver(key: str):
        if key == "entity_field_validations":
            return lambda _b, o, _k: [*o]
        return None

    base = {
        "entity_field_validations": [
            {"field": "a", "type": "required"},
            {"field": "b", "type": "range"},
        ]
    }
    override = {"entity_field_validations": [{"field": "c", "type": "enum"}]}

    result = config_merge(
        base,
        override,
        list_concat_keys=frozenset({"entity_field_validations"}),
        list_merger_resolver=resolver,
    )

    assert result["entity_field_validations"] == [{"field": "c", "type": "enum"}]
