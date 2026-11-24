"""Unit tests for the Gold SCD2 envelope type guard of target migration.

``validate_scd_types`` is the only place that rejects malformed temporal
bounds, non-boolean current flags and non-positive SCD versions before a
target row is migrated. It had no direct test, so a type regression (for
example accepting ``_version=True`` because ``bool`` is an ``int``) would pass
the whole suite unnoticed.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.infrastructure.storage.target_migration_row_ops import validate_scd_types


def _scd_row(**overrides: object) -> dict[str, object]:
    """Build a complete Gold SCD2 envelope with optional overrides."""
    row: dict[str, object] = {
        "_valid_from": "2026-01-01T00:00:00+00:00",
        "_valid_to": None,
        "_is_current": True,
        "_version": 1,
    }
    row.update(overrides)
    return row


@pytest.mark.unit
class TestValidateScdTypesAccepts:
    """Accepted SCD2 envelope shapes."""

    def test_validate_scd_types__complete_envelope__returns_none(self) -> None:
        assert validate_scd_types(_scd_row()) is None

    def test_validate_scd_types__utc_text_bounds__returns_none(self) -> None:
        result = validate_scd_types(
            _scd_row(
                _valid_from="2026-01-01T00:00:00Z",
                _valid_to="2026-06-30T23:59:59Z",
            )
        )

        assert result is None

    def test_validate_scd_types__datetime_bounds__returns_none(self) -> None:
        result = validate_scd_types(
            _scd_row(
                _valid_from=datetime(2026, 1, 1, tzinfo=UTC),
                _valid_to=datetime(2026, 6, 30, tzinfo=UTC),
            )
        )

        assert result is None

    def test_validate_scd_types__naive_iso_text_bound__returns_none(self) -> None:
        assert validate_scd_types(_scd_row(_valid_from="2026-01-01T00:00:00")) is None

    def test_validate_scd_types__historical_non_current_row__returns_none(self) -> None:
        result = validate_scd_types(
            _scd_row(
                _valid_from="2025-01-01T00:00:00+00:00",
                _valid_to="2025-12-31T23:59:59+00:00",
                _is_current=False,
                _version=7,
            )
        )

        assert result is None


@pytest.mark.unit
class TestValidateScdTypesRejectsTemporalBounds:
    """Malformed temporal bounds."""

    def test_validate_scd_types__non_iso_valid_from__rejects_row(self) -> None:
        with pytest.raises(
            ValueError,
            match="Gold SCD _valid_from requires datetime or valid ISO8601 text",
        ):
            validate_scd_types(_scd_row(_valid_from="01/01/2026"))

    def test_validate_scd_types__impossible_calendar_valid_from__rejects_row(
        self,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="Gold SCD _valid_from requires datetime or valid ISO8601 text",
        ):
            validate_scd_types(_scd_row(_valid_from="2026-13-45T00:00:00"))

    def test_validate_scd_types__non_iso_valid_to__rejects_row(self) -> None:
        with pytest.raises(
            ValueError,
            match="Gold SCD _valid_to requires nullable datetime or valid ISO8601 text",
        ):
            validate_scd_types(_scd_row(_valid_to="never"))

    def test_validate_scd_types__date_only_valid_to__rejects_row(self) -> None:
        with pytest.raises(
            ValueError,
            match="Gold SCD _valid_to requires nullable datetime or valid ISO8601 text",
        ):
            validate_scd_types(_scd_row(_valid_to="2026-06-30"))


@pytest.mark.unit
class TestValidateScdTypesRejectsCurrentFlag:
    """The current flag must stay a real boolean."""

    def test_validate_scd_types__integer_current_flag__rejects_row(self) -> None:
        with pytest.raises(
            ValueError, match="Gold SCD _is_current must retain its boolean type"
        ):
            validate_scd_types(_scd_row(_is_current=1))

    def test_validate_scd_types__string_current_flag__rejects_row(self) -> None:
        with pytest.raises(
            ValueError, match="Gold SCD _is_current must retain its boolean type"
        ):
            validate_scd_types(_scd_row(_is_current="true"))

    def test_validate_scd_types__none_current_flag__rejects_row(self) -> None:
        with pytest.raises(
            ValueError, match="Gold SCD _is_current must retain its boolean type"
        ):
            validate_scd_types(_scd_row(_is_current=None))


@pytest.mark.unit
class TestValidateScdTypesRejectsVersion:
    """The SCD version must stay a positive integer."""

    def test_validate_scd_types__zero_version__rejects_row(self) -> None:
        with pytest.raises(
            ValueError, match="Gold SCD _version must retain its positive integer type"
        ):
            validate_scd_types(_scd_row(_version=0))

    def test_validate_scd_types__negative_version__rejects_row(self) -> None:
        with pytest.raises(
            ValueError, match="Gold SCD _version must retain its positive integer type"
        ):
            validate_scd_types(_scd_row(_version=-1))

    def test_validate_scd_types__boolean_version__rejects_row(self) -> None:
        with pytest.raises(
            ValueError, match="Gold SCD _version must retain its positive integer type"
        ):
            validate_scd_types(_scd_row(_version=True))

    def test_validate_scd_types__string_version__rejects_row(self) -> None:
        with pytest.raises(
            ValueError, match="Gold SCD _version must retain its positive integer type"
        ):
            validate_scd_types(_scd_row(_version="1"))

    def test_validate_scd_types__float_version__rejects_row(self) -> None:
        with pytest.raises(
            ValueError, match="Gold SCD _version must retain its positive integer type"
        ):
            validate_scd_types(_scd_row(_version=1.0))
