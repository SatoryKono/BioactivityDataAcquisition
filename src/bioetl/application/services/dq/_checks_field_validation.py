"""Field-level DQ validation checks using FieldValidation config.

Applies FieldValidation rules from DQ config to individual values.
Supports all validation types defined in domain.config.FieldValidation.

Used by DQ analyzers to validate field values against configured rules.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any


def validate_field_value(
    value: Any,
    validation_type: str,
    *,
    nullable: bool = True,
    pattern: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    allowed: tuple[str, ...] = (),
    element_type: str | None = None,
    element_pattern: str | None = None,
    min_items: int | None = None,
) -> bool:
    """Validate a single value against a validation rule.

    Args:
        value: The value to validate.
        validation_type: Type of validation to apply.
        nullable: Whether None/NaN values are allowed.
        pattern: Regex pattern for pattern validation.
        min_value: Minimum value for range validation.
        max_value: Maximum value for range validation.
        allowed: Allowed values for enum validation.
        element_type: Element type for json_array (string, integer, object).
        element_pattern: Regex pattern for json_array string elements.
        min_items: Minimum number of items for json_array.

    Returns:
        True if validation passes, False otherwise.
    """
    # Handle null/None/NaN values
    if _is_null(value):
        if nullable:
            return True
        # For "required" type, null is always a failure
        return False

    handler = _VALIDATION_HANDLERS.get(validation_type)
    if handler is None:
        return True

    return handler(
        value,
        pattern=pattern,
        min_value=min_value,
        max_value=max_value,
        allowed=allowed,
        element_type=element_type,
        element_pattern=element_pattern,
        min_items=min_items,
    )


def _is_null(value: Any) -> bool:
    """Check if a value is null/None/NaN."""
    if value is None:
        return True
    try:
        import math

        if isinstance(value, float) and math.isnan(value):
            return True
    except (TypeError, ValueError):
        pass
    # pandas NA check
    try:
        import pandas as pd

        if pd.isna(value):
            return True
    except (ImportError, TypeError, ValueError):
        pass
    return False


def _validate_required(value: Any, **_kwargs: Any) -> bool:
    """Validate that field is present and non-null (null already handled)."""
    return True  # If we got here, value is not null


def _validate_range(value: Any, **kwargs: Any) -> bool:
    """Validate numeric range."""
    min_value = kwargs.get("min_value")
    max_value = kwargs.get("max_value")
    try:
        num = float(value)
    except (TypeError, ValueError):
        return False
    if min_value is not None and num < min_value:
        return False
    if max_value is not None and num > max_value:
        return False
    return True


def _validate_pattern(value: Any, **kwargs: Any) -> bool:
    """Validate regex pattern match."""
    pattern = kwargs.get("pattern")
    if not pattern:
        return True
    try:
        return bool(re.match(pattern, str(value)))
    except re.error:
        return False


def _validate_enum(value: Any, **kwargs: Any) -> bool:
    """Validate value is in allowed set."""
    allowed = kwargs.get("allowed", ())
    if not allowed:
        return True
    return str(value) in allowed


def _validate_non_empty(value: Any, **_kwargs: Any) -> bool:
    """Validate that string is not empty after strip."""
    return len(str(value).strip()) > 0


def _validate_json_array(value: Any, **kwargs: Any) -> bool:
    """Validate that value parses as JSON array with optional constraints."""
    try:
        parsed = json.loads(str(value))
    except (json.JSONDecodeError, TypeError, ValueError):
        return False

    if not isinstance(parsed, list):
        return False

    element_type = kwargs.get("element_type")
    element_pattern = kwargs.get("element_pattern")
    min_items = kwargs.get("min_items")

    if min_items is not None and len(parsed) < min_items:
        return False

    if element_type:
        type_map = {"string": str, "integer": int, "object": dict}
        expected = type_map.get(element_type)
        if expected:
            for elem in parsed:
                if not isinstance(elem, expected):
                    return False

    if element_pattern:
        try:
            compiled = re.compile(element_pattern)
            for elem in parsed:
                if isinstance(elem, str) and not compiled.match(elem):
                    return False
        except re.error:
            return False

    return True


def _validate_json_object(value: Any, **_kwargs: Any) -> bool:
    """Validate that value parses as JSON object."""
    try:
        parsed = json.loads(str(value))
    except (json.JSONDecodeError, TypeError, ValueError):
        return False
    return isinstance(parsed, dict)


def _validate_url(value: Any, **_kwargs: Any) -> bool:
    """Validate that value is a valid URL (http/https)."""
    return bool(re.match(r"^https?://.+", str(value)))


def _validate_boolean_strict(value: Any, **_kwargs: Any) -> bool:
    """Validate that value is strictly bool (True/False)."""
    return isinstance(value, bool)


def _validate_date_iso(value: Any, **_kwargs: Any) -> bool:
    """Validate ISO date format YYYY-MM-DD."""
    s = str(value)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return False
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


_VALIDATION_HANDLERS: dict[str, Any] = {
    "required": _validate_required,
    "range": _validate_range,
    "pattern": _validate_pattern,
    "enum": _validate_enum,
    "non_empty": _validate_non_empty,
    "json_array": _validate_json_array,
    "json_object": _validate_json_object,
    "url": _validate_url,
    "boolean_strict": _validate_boolean_strict,
    "date_iso": _validate_date_iso,
}


__all__ = ["validate_field_value"]
