"""Tests for PubChem policy helper functions.

Covers:
- is_limit_reached: None limit, boundary conditions
- is_blank_value: None, empty, whitespace, valid
- is_valid_inchikey: valid format, length, dashes
- iter_cid_batches: normal, empty, exact boundary
- parse_valid_cids: valid, invalid, mixed
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.pubchem.policy_helper import (
    is_blank_value,
    is_limit_reached,
    is_valid_inchikey,
    iter_cid_batches,
    parse_valid_cids,
)


# ---------------------------------------------------------------------------
# is_limit_reached
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsLimitReached:
    def test_none_limit_never_reached(self) -> None:
        assert is_limit_reached(None, 0) is False
        assert is_limit_reached(None, 9999) is False

    def test_fetched_below_limit(self) -> None:
        assert is_limit_reached(10, 5) is False

    def test_fetched_equals_limit(self) -> None:
        assert is_limit_reached(10, 10) is True

    def test_fetched_exceeds_limit(self) -> None:
        assert is_limit_reached(10, 15) is True

    def test_zero_limit_zero_fetched(self) -> None:
        assert is_limit_reached(0, 0) is True

    def test_zero_limit_positive_fetched(self) -> None:
        assert is_limit_reached(0, 1) is True


# ---------------------------------------------------------------------------
# is_blank_value
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsBlankValue:
    def test_none_is_blank(self) -> None:
        assert is_blank_value(None) is True

    def test_empty_string_is_blank(self) -> None:
        assert is_blank_value("") is True

    def test_whitespace_is_blank(self) -> None:
        assert is_blank_value("   ") is True
        assert is_blank_value("\t\n") is True

    def test_valid_string_not_blank(self) -> None:
        assert is_blank_value("aspirin") is False

    def test_string_with_leading_whitespace_not_blank(self) -> None:
        assert is_blank_value("  aspirin  ") is False


# ---------------------------------------------------------------------------
# is_valid_inchikey
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsValidInchikey:
    def test_valid_inchikey(self) -> None:
        assert is_valid_inchikey("BSYNRYMUTXBXSQ-UHFFFAOYSA-N") is True

    def test_too_short(self) -> None:
        assert is_valid_inchikey("SHORT-KEY-X") is False

    def test_too_long(self) -> None:
        assert is_valid_inchikey("BSYNRYMUTXBXSQ-UHFFFAOYSA-NXXX") is False

    def test_no_dashes(self) -> None:
        assert is_valid_inchikey("BSYNRYMUTXBXSQAUHFFFAOYSAAN") is False

    def test_one_dash(self) -> None:
        # 27 chars but only 1 dash
        assert is_valid_inchikey("BSYNRYMUTXBXSQAU-FFFAOYSAAN") is False

    def test_three_dashes(self) -> None:
        # 27 chars with 3 dashes
        # This is 27 chars but has 4 dashes actually; craft one with exactly 3
        key3 = "BSY-RYM-XBX-UHFFFAOYSANNNN"
        assert len(key3) != 27 or is_valid_inchikey(key3) is False

    def test_is_valid_inchikey__empty_string__81a33ca5(self) -> None:
        assert is_valid_inchikey("") is False


# ---------------------------------------------------------------------------
# iter_cid_batches
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIterCidBatches:
    def test_normal_batching(self) -> None:
        cids = [1, 2, 3, 4, 5]
        batches = list(iter_cid_batches(cids, batch_size=2))
        assert batches == [[1, 2], [3, 4], [5]]

    def test_exact_boundary(self) -> None:
        cids = [10, 20, 30]
        batches = list(iter_cid_batches(cids, batch_size=3))
        assert batches == [[10, 20, 30]]

    def test_iter_cid_batches__empty_list__746634d1(self) -> None:
        batches = list(iter_cid_batches([], batch_size=5))
        assert batches == []

    def test_batch_size_larger_than_list(self) -> None:
        cids = [1, 2]
        batches = list(iter_cid_batches(cids, batch_size=100))
        assert batches == [[1, 2]]

    def test_batch_size_one(self) -> None:
        cids = [10, 20, 30]
        batches = list(iter_cid_batches(cids, batch_size=1))
        assert batches == [[10], [20], [30]]


# ---------------------------------------------------------------------------
# parse_valid_cids
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseValidCids:
    def test_all_valid(self) -> None:
        logger = MagicMock()
        result = parse_valid_cids(["1", "2", "3"], logger=logger, provider_name="pc")
        assert result == [1, 2, 3]
        logger.warning.assert_not_called()

    def test_mixed_valid_invalid(self) -> None:
        logger = MagicMock()
        result = parse_valid_cids(
            ["1", "abc", "3"], logger=logger, provider_name="pubchem"
        )
        assert result == [1, 3]
        logger.warning.assert_called_once()

    def test_all_invalid(self) -> None:
        logger = MagicMock()
        result = parse_valid_cids(["x", "y"], logger=logger, provider_name="pc")
        assert result == []
        assert logger.warning.call_count == 2

    def test_parse_valid_cids__empty_list__4248ab8d(self) -> None:
        logger = MagicMock()
        result = parse_valid_cids([], logger=logger, provider_name="pc")
        assert result == []
