"""Shared schema-backed field assertions for E2E suites (T-09 / #6608)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any


def assert_records_have_required_fields(
    records: Sequence[Mapping[str, Any]],
    required_fields: Iterable[str],
    *,
    entity_label: str,
) -> None:
    """Require non-empty values for every declared field on every record."""
    fields = tuple(required_fields)
    assert fields, f"{entity_label}: required_fields must be non-empty"
    assert records, f"{entity_label}: expected at least one record"

    for index, record in enumerate(records):
        for field in fields:
            assert field in record, (
                f"{entity_label} record[{index}] missing required field {field!r}"
            )
            value = record.get(field)
            assert value is not None, (
                f"{entity_label} record[{index}].{field} must not be None"
            )
            if isinstance(value, str):
                assert value.strip(), (
                    f"{entity_label} record[{index}].{field} must not be blank"
                )


def assert_optional_numeric_in_range(
    records: Sequence[Mapping[str, Any]],
    field: str,
    *,
    minimum: float,
    maximum: float,
    entity_label: str,
) -> None:
    """When present, numeric field values must stay within [minimum, maximum]."""
    for index, record in enumerate(records):
        value = record.get(field)
        if value is None:
            continue
        assert isinstance(value, (int, float)), (
            f"{entity_label} record[{index}].{field} expected numeric, got {type(value)}"
        )
        assert minimum <= float(value) <= maximum, (
            f"{entity_label} record[{index}].{field}={value} outside [{minimum}, {maximum}]"
        )
