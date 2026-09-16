"""Complete behavioral coverage for Click option narrowing helpers."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from bioetl.interfaces.cli.commands._typed_option_values import (
    option_or_default,
    optional_option,
    require_option,
    string_tuple_option,
)
from bioetl.interfaces.cli.commands.domains.shared.option_mapping import (
    option_bool,
    option_bool_get,
    option_int,
    option_int_get,
    option_optional_bool_get,
    option_optional_int,
    option_optional_int_get,
    option_optional_str,
    option_optional_str_get,
    option_str,
)

pytestmark = pytest.mark.unit


def test_generic_option_helpers_return_typed_values_and_defaults() -> None:
    assert require_option({"name": "value"}, "name", str) == "value"
    assert optional_option({}, "name", str) is None
    assert optional_option({"name": "value"}, "name", str) == "value"
    assert option_or_default({}, "limit", 5, int) == 5
    assert option_or_default({"limit": 3}, "limit", 5, int) == 3
    assert string_tuple_option({}, "tags") == ()
    assert string_tuple_option({"tags": ("a", "b")}, "tags") == ("a", "b")


@pytest.mark.parametrize(
    "operation",
    [
        lambda: require_option({"limit": "1"}, "limit", int),
        lambda: require_option({"limit": True}, "limit", int),
        lambda: optional_option({"limit": "1"}, "limit", int),
        lambda: optional_option({"limit": True}, "limit", int),
        lambda: option_or_default({"limit": "1"}, "limit", 1, int),
        lambda: option_or_default({"limit": True}, "limit", 1, int),
        lambda: string_tuple_option({"tags": ["a"]}, "tags"),
        lambda: string_tuple_option({"tags": ("a", 2)}, "tags"),
    ],
)
def test_generic_option_helpers_reject_wrong_runtime_types(
    operation: Callable[[], object],
) -> None:
    with pytest.raises(TypeError):
        operation()


def test_mapping_option_helpers_cover_present_absent_and_none_values() -> None:
    assert option_str({"name": "x"}, "name") == "x"
    assert option_optional_str({"name": None}, "name") is None
    assert option_optional_str({"name": "x"}, "name") == "x"
    assert option_optional_str_get({}, "name") is None
    assert option_optional_str_get({"name": "x"}, "name") == "x"
    assert option_bool({"enabled": True}, "enabled") is True
    assert option_bool_get({}, "enabled", False) is False
    assert option_bool_get({"enabled": None}, "enabled", True) is True
    assert option_bool_get({"enabled": False}, "enabled", True) is False
    assert option_optional_bool_get({}, "enabled") is None
    assert option_optional_bool_get({"enabled": None}, "enabled") is None
    assert option_optional_bool_get({"enabled": True}, "enabled") is True
    assert option_int({"limit": 1}, "limit") == 1
    assert option_int_get({}, "limit", 2) == 2
    assert option_int_get({"limit": None}, "limit", 2) == 2
    assert option_int_get({"limit": 3}, "limit", 2) == 3
    assert option_optional_int({"limit": None}, "limit") is None
    assert option_optional_int({"limit": 3}, "limit") == 3
    assert option_optional_int_get({}, "limit") is None
    assert option_optional_int_get({"limit": 3}, "limit") == 3


@pytest.mark.parametrize(
    "operation",
    [
        lambda: option_str({"x": 1}, "x"),
        lambda: option_optional_str({"x": 1}, "x"),
        lambda: option_bool({"x": 1}, "x"),
        lambda: option_bool_get({"x": 1}, "x", False),
        lambda: option_optional_bool_get({"x": 1}, "x"),
        lambda: option_int({"x": True}, "x"),
        lambda: option_int_get({"x": "1"}, "x", 0),
        lambda: option_optional_int({"x": True}, "x"),
    ],
)
def test_mapping_option_helpers_reject_wrong_runtime_types(
    operation: Callable[[], object],
) -> None:
    with pytest.raises(TypeError):
        operation()
