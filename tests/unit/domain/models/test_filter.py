"""Tests for ExtractionParams frozen dataclass.

Part of ADR-028 §3: Extraction-Level Filtering.
"""

from __future__ import annotations

import pytest

from bioetl.domain.models.filter import ExtractionParams


@pytest.mark.unit
class TestExtractionParams:
    """Tests for ExtractionParams value object."""

    def test_to_query_dict_returns_mutable_copy(self) -> None:
        """GIVEN ExtractionParams with params WHEN to_query_dict THEN returns mutable dict copy."""
        original = {"standard_type__in": "IC50,Ki", "standard_units": "nM"}
        ep = ExtractionParams(params=original)
        result = ep.to_query_dict()

        assert result == original
        assert isinstance(result, dict)
        # Mutating the result must not affect the original
        result["new_key"] = "new_value"
        assert "new_key" not in ep.params

    def test_to_query_string_sorted_deterministic(self) -> None:
        """GIVEN params with multiple keys WHEN to_query_string THEN keys are sorted."""
        ep = ExtractionParams(
            params={
                "z_param": "last",
                "a_param": "first",
                "m_param": "middle",
            }
        )
        result = ep.to_query_string()

        assert result == "a_param=first&m_param=middle&z_param=last"

    def test_is_empty_true_for_empty_params(self) -> None:
        """GIVEN empty params WHEN is_empty THEN returns True."""
        ep = ExtractionParams(params={})

        assert ep.is_empty is True

    def test_is_empty_false_for_non_empty(self) -> None:
        """GIVEN non-empty params WHEN is_empty THEN returns False."""
        ep = ExtractionParams(params={"key": "value"})

        assert ep.is_empty is False

    def test_empty_factory_method(self) -> None:
        """GIVEN ExtractionParams.empty() WHEN called THEN returns empty instance."""
        ep = ExtractionParams.empty()

        assert ep.is_empty is True
        assert ep.to_query_dict() == {}
        assert ep.to_query_string() == ""

    def test_extraction_params__frozen_immutability__4a0c0e3d(self) -> None:
        """GIVEN frozen ExtractionParams WHEN mutating params THEN raises error."""
        ep = ExtractionParams(params={"key": "value"})

        with pytest.raises(AttributeError):
            ep.params = {}  # type: ignore[misc]

    def test_to_query_string_with_bool_values(self) -> None:
        """GIVEN params with bool values WHEN to_query_string THEN serializes correctly."""
        ep = ExtractionParams(
            params={
                "pchembl_value__isnull": False,
                "target_organism__isnull": True,
            }
        )
        result = ep.to_query_string()

        assert result == "pchembl_value__isnull=False&target_organism__isnull=True"

    def test_to_query_dict_with_mixed_value_types(self) -> None:
        """GIVEN params with str, int, bool values WHEN to_query_dict THEN preserves types."""
        ep = ExtractionParams(
            params={
                "standard_type__in": "IC50,Ki",
                "limit": 1000,
                "pchembl_value__isnull": False,
            }
        )
        result = ep.to_query_dict()

        assert result["standard_type__in"] == "IC50,Ki"
        assert result["limit"] == 1000
        assert result["pchembl_value__isnull"] is False

    def test_to_query_string_empty(self) -> None:
        """GIVEN empty params WHEN to_query_string THEN returns empty string."""
        ep = ExtractionParams(params={})

        assert ep.to_query_string() == ""

    def test_extraction_params__equality__b95388e9(self) -> None:
        """GIVEN two ExtractionParams with same params WHEN compared THEN equal."""
        ep1 = ExtractionParams(params={"key": "value"})
        ep2 = ExtractionParams(params={"key": "value"})

        assert ep1 == ep2
