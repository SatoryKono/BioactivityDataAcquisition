"""Filter-condition validation helpers for aggregation configs."""

from __future__ import annotations

import re

_FILTER_FIELD_RE = re.compile(
    r"^[A-Za-z_]\w*$"
)  # NOSONAR - requires non-digit first char, \w+ alone is insufficient


def _require_filter_field(field: str) -> None:
    if not _FILTER_FIELD_RE.fullmatch(field):
        raise ValueError(
            f"aggregation filter_condition has invalid field name: {field!r}"
        )


def _validate_null_filter(text: str, upper: str, token: str) -> bool:
    if token not in upper:
        return False
    token_index = upper.find(token)
    field = text[:token_index].strip()
    _require_filter_field(field)
    if text[token_index + len(token) :].strip():
        raise ValueError(
            "aggregation filter_condition null check must not contain trailing text"
        )
    return True


def _is_quoted_literal(value: str) -> bool:
    quote = _matching_quote(value)
    if quote is None:
        return False
    return _quoted_body_is_valid(value[1:-1], quote)


def _matching_quote(value: str) -> str | None:
    if len(value) < 2:
        return None
    if value[0] not in {"'", '"'}:
        return None
    if value[-1] != value[0]:
        return None
    return value[0]


def _quoted_body_is_valid(body: str, quote: str) -> bool:
    escaped = False
    for character in body:
        if character == quote and not escaped:
            return False
        escaped = character == "\\" and not escaped
    return not escaped


def _rhs_contains_nested_operators(rhs: str) -> bool:
    upper_rhs = f" {rhs.upper()} "
    if any(token in upper_rhs for token in (" == ", " != ", " AND ", " OR ")):
        return True
    return any(token in rhs.upper() for token in (" IS NULL", " IS NOT NULL"))


def _reject_nested_rhs_operators(rhs: str) -> None:
    """Reject unquoted RHS values that embed extra operators/keywords."""
    if _is_quoted_literal(rhs):
        return
    if _rhs_contains_nested_operators(rhs):
        raise ValueError(
            "aggregation filter_condition comparison value must not "
            "contain additional operators or boolean keywords"
        )


def _try_comparison_operator(text: str, operator: str) -> bool:
    if operator not in text:
        return False
    left, right = text.split(operator, 1)
    _require_filter_field(left.strip())
    rhs = right.strip()
    if not rhs:
        raise ValueError("aggregation filter_condition comparison requires a value")
    _reject_nested_rhs_operators(rhs)
    return True


def _validate_comparison_filter(text: str) -> bool:
    if _try_comparison_operator(text, " == "):
        return True
    return _try_comparison_operator(text, " != ")


def _validate_known_filter_forms(text: str, upper: str) -> bool:
    if _validate_null_filter(text, upper, " IS NOT NULL"):
        return True
    if _validate_null_filter(text, upper, " IS NULL"):
        return True
    return _validate_comparison_filter(text)


def _validate_aggregation_filter_condition(condition: str) -> None:
    """Fail closed on empty or unsupported aggregation filter expressions.

    Supported grammar (aligned with application aggregator parser):
    - ``field IS NULL`` / ``field IS NOT NULL``
    - ``field == value`` / ``field != value`` (value may be quoted)
    """
    text = condition.strip()
    if not text:
        raise ValueError("aggregation filter_condition cannot be empty")
    if _validate_known_filter_forms(text, text.upper()):
        return
    raise ValueError(
        "aggregation filter_condition uses unsupported syntax; "
        "expected IS NULL / IS NOT NULL / == / != forms, "
        f"got {condition!r}"
    )
