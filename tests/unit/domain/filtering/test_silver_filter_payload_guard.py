"""Unit tests for the structural-only Silver filter payload guard.

ADR-050 moved semantic and business filters out of ``silver_filters``. The
guard that enforces it (``validate_structural_silver_filter_payload``) and its
key collector had no direct test, so a semantic key could return to the Silver
layer without any failing test.
"""

from __future__ import annotations

import pytest

from bioetl.domain.filtering.silver_config import (
    FORBIDDEN_SILVER_SEMANTIC_FILTER_KEYS,
    forbidden_semantic_silver_filter_keys,
    validate_structural_silver_filter_payload,
)


@pytest.mark.unit
class TestForbiddenSemanticSilverFilterKeys:
    """Detection of semantic keys inside a Silver filter payload."""

    def test_forbidden_semantic_silver_filter_keys__structural_payload__returns_empty_tuple(
        self,
    ) -> None:
        payload = {"required_fields": ["id"], "exclude_if_present": ["flag"]}

        assert forbidden_semantic_silver_filter_keys(payload) == ()

    def test_forbidden_semantic_silver_filter_keys__semantic_payload__returns_sorted_keys(
        self,
    ) -> None:
        payload = {"list_contains": {"x": [1]}, "columns": ["id"]}

        assert forbidden_semantic_silver_filter_keys(payload) == (
            "columns",
            "list_contains",
        )

    def test_forbidden_semantic_silver_filter_keys__semantic_payload__covers_every_forbidden_key(
        self,
    ) -> None:
        payload = {key: [] for key in FORBIDDEN_SILVER_SEMANTIC_FILTER_KEYS}

        assert set(forbidden_semantic_silver_filter_keys(payload)) == set(
            FORBIDDEN_SILVER_SEMANTIC_FILTER_KEYS
        )


@pytest.mark.unit
class TestValidateStructuralSilverFilterPayload:
    """Rejection of semantic keys under ``silver_filters``."""

    def test_validate_structural_silver_filter_payload__structural_payload__returns_none(
        self,
    ) -> None:
        result = validate_structural_silver_filter_payload(
            {"required_fields": ["id"], "exclude_if_present": ["flag"]}
        )

        assert result is None

    def test_validate_structural_silver_filter_payload__semantic_column_key__raises_value_error(
        self,
    ) -> None:
        with pytest.raises(ValueError, match=r"silver_filters\.columns"):
            validate_structural_silver_filter_payload({"columns": ["id"]})

    def test_validate_structural_silver_filter_payload__multiple_semantic_keys__reports_all_keys(
        self,
    ) -> None:
        with pytest.raises(ValueError) as failure:
            validate_structural_silver_filter_payload(
                {"ranges": [], "columns": ["id"], "list_lengths": []}
            )

        message = str(failure.value)
        assert "silver_filters.columns" in message
        assert "silver_filters.list_lengths" in message
        assert "silver_filters.ranges" in message

    def test_validate_structural_silver_filter_payload__custom_path__reports_custom_path(
        self,
    ) -> None:
        with pytest.raises(ValueError, match=r"payload\.columns"):
            validate_structural_silver_filter_payload(
                {"columns": ["id"]}, path="payload"
            )

    def test_validate_structural_silver_filter_payload__semantic_key__explains_target_location(
        self,
    ) -> None:
        with pytest.raises(ValueError, match="gold_filters"):
            validate_structural_silver_filter_payload({"columns": ["id"]})
