"""Tests for activity-related Value Objects.

Tests for ConfidenceScore, RelationOperator, ActivityValue.
"""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects import (
    ActivityValue,
    ConfidenceScore,
    RelationOperator,
)

pytestmark = pytest.mark.unit


class TestRelationOperator:
    """Tests for RelationOperator enum."""

    def test_equal_operator(self) -> None:
        """Test equality operator."""
        assert RelationOperator.EQUAL.value == "="
        assert RelationOperator.EQUAL.is_exact() is True
        assert RelationOperator.EQUAL.is_upper_bound() is False
        assert RelationOperator.EQUAL.is_lower_bound() is False

    def test_less_than_operator(self) -> None:
        """Test less than operator."""
        assert RelationOperator.LESS_THAN.value == "<"
        assert RelationOperator.LESS_THAN.is_exact() is False
        assert RelationOperator.LESS_THAN.is_upper_bound() is True
        assert RelationOperator.LESS_THAN.is_lower_bound() is False

    def test_greater_than_operator(self) -> None:
        """Test greater than operator."""
        assert RelationOperator.GREATER_THAN.value == ">"
        assert RelationOperator.GREATER_THAN.is_exact() is False
        assert RelationOperator.GREATER_THAN.is_upper_bound() is False
        assert RelationOperator.GREATER_THAN.is_lower_bound() is True

    def test_less_than_or_equal_operator(self) -> None:
        """Test less than or equal operator."""
        assert RelationOperator.LESS_THAN_OR_EQUAL.value == "<="
        assert RelationOperator.LESS_THAN_OR_EQUAL.is_upper_bound() is True

    def test_greater_than_or_equal_operator(self) -> None:
        """Test greater than or equal operator."""
        assert RelationOperator.GREATER_THAN_OR_EQUAL.value == ">="
        assert RelationOperator.GREATER_THAN_OR_EQUAL.is_lower_bound() is True

    def test_approximately_operator(self) -> None:
        """Test approximately operator."""
        assert RelationOperator.APPROXIMATELY.value == "~"
        assert RelationOperator.APPROXIMATELY.is_exact() is False

    def test_from_string_equal(self) -> None:
        """Test parsing equality operators."""
        assert RelationOperator.from_string("=") == RelationOperator.EQUAL
        assert RelationOperator.from_string("==") == RelationOperator.EQUAL

    def test_from_string_less_than(self) -> None:
        """Test parsing less than operators."""
        assert RelationOperator.from_string("<") == RelationOperator.LESS_THAN
        assert RelationOperator.from_string("<=") == RelationOperator.LESS_THAN_OR_EQUAL
        assert RelationOperator.from_string("=<") == RelationOperator.LESS_THAN_OR_EQUAL

    def test_from_string_greater_than(self) -> None:
        """Test parsing greater than operators."""
        assert RelationOperator.from_string(">") == RelationOperator.GREATER_THAN
        assert (
            RelationOperator.from_string(">=") == RelationOperator.GREATER_THAN_OR_EQUAL
        )
        assert (
            RelationOperator.from_string("=>") == RelationOperator.GREATER_THAN_OR_EQUAL
        )

    def test_from_string_approximately(self) -> None:
        """Test parsing approximately operators."""
        assert RelationOperator.from_string("~") == RelationOperator.APPROXIMATELY
        assert RelationOperator.from_string("≈") == RelationOperator.APPROXIMATELY
        assert RelationOperator.from_string("approx") == RelationOperator.APPROXIMATELY

    def test_from_string_none(self) -> None:
        """Test None input returns None."""
        assert RelationOperator.from_string(None) is None

    def test_from_string_empty(self) -> None:
        """Test empty string returns None."""
        assert RelationOperator.from_string("") is None
        assert RelationOperator.from_string("   ") is None

    def test_from_string_invalid(self) -> None:
        """Test invalid string raises ValueError."""
        with pytest.raises(ValueError, match="Unknown relation operator"):
            RelationOperator.from_string("!=")

    def test_from_string_strips_whitespace(self) -> None:
        """Test whitespace is stripped."""
        assert RelationOperator.from_string("  =  ") == RelationOperator.EQUAL


class TestConfidenceScore:
    """Tests for ConfidenceScore Value Object."""

    def test_valid_score_min(self) -> None:
        """Test minimum valid score."""
        score = ConfidenceScore(0)
        assert score.value == 0

    def test_valid_score_max(self) -> None:
        """Test maximum valid score."""
        score = ConfidenceScore(9)
        assert score.value == 9

    def test_valid_score_mid(self) -> None:
        """Test middle score."""
        score = ConfidenceScore(5)
        assert score.value == 5

    def test_high_confidence_property(self) -> None:
        """Test is_high_confidence property."""
        assert ConfidenceScore(9).is_high_confidence is True
        assert ConfidenceScore(8).is_high_confidence is True
        assert ConfidenceScore(7).is_high_confidence is True
        assert ConfidenceScore(6).is_high_confidence is False
        assert ConfidenceScore(0).is_high_confidence is False

    def test_molecular_target_property(self) -> None:
        """Test is_molecular_target property."""
        assert ConfidenceScore(9).is_molecular_target is True
        assert ConfidenceScore(3).is_molecular_target is True
        assert ConfidenceScore(2).is_molecular_target is False
        assert ConfidenceScore(1).is_molecular_target is False
        assert ConfidenceScore(0).is_molecular_target is False

    def test_description_property(self) -> None:
        """Test description property returns appropriate text."""
        assert ConfidenceScore(9).description == "Direct single protein target"
        assert ConfidenceScore(1).description == "Phenotypic (no molecular target)"
        assert ConfidenceScore(0).description == "No target assigned"

    def test_negative_score_raises(self) -> None:
        """Test negative score raises ValueError."""
        with pytest.raises(ValueError, match="must be 0-9"):
            ConfidenceScore(-1)

    def test_score_above_9_raises(self) -> None:
        """Test score above 9 raises ValueError."""
        with pytest.raises(ValueError, match="must be 0-9"):
            ConfidenceScore(10)

    def test_non_integer_raises(self) -> None:
        """Test non-integer raises TypeError."""
        with pytest.raises(TypeError, match="must be int"):
            ConfidenceScore(5.5)  # type: ignore[arg-type]

    def test_from_value_int(self) -> None:
        """Test from_value with integer."""
        score = ConfidenceScore.from_value(7)
        assert score is not None
        assert score.value == 7

    def test_from_value_string(self) -> None:
        """Test from_value with string."""
        score = ConfidenceScore.from_value("5")
        assert score is not None
        assert score.value == 5

    def test_from_value_none(self) -> None:
        """Test from_value with None returns None."""
        assert ConfidenceScore.from_value(None) is None

    def test_from_value_invalid_string(self) -> None:
        """Test from_value with invalid string raises ValueError."""
        with pytest.raises(ValueError):
            ConfidenceScore.from_value("abc")

    def test_confidence_score__immutability__c898f4f3(self) -> None:
        """Test ConfidenceScore is immutable (frozen dataclass)."""
        score = ConfidenceScore(5)
        with pytest.raises(Exception):  # FrozenInstanceError
            score.value = 7  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        """Test equality is based on value."""
        score1 = ConfidenceScore(7)
        score2 = ConfidenceScore(7)
        assert score1 == score2
        assert score1 is not score2

    def test_confidence_score__inequality__448a1bc3(self) -> None:
        """Test inequality for different values."""
        score1 = ConfidenceScore(5)
        score2 = ConfidenceScore(7)
        assert score1 != score2

    def test_confidence_score__hash_consistency__15797939(self) -> None:
        """Test hash is consistent with equality."""
        score1 = ConfidenceScore(7)
        score2 = ConfidenceScore(7)
        assert hash(score1) == hash(score2)

    def test_ordering(self) -> None:
        """Test comparison operators for ordering."""
        low = ConfidenceScore(3)
        high = ConfidenceScore(8)
        assert low < high
        assert high > low  # type: ignore[operator]

    def test_confidence_score__can_be_used_in_set__85055f37(self) -> None:
        """Test ConfidenceScore can be used in set."""
        scores = {ConfidenceScore(5), ConfidenceScore(5), ConfidenceScore(7)}
        assert len(scores) == 2

    def test_str(self) -> None:
        """Test string conversion."""
        assert str(ConfidenceScore(7)) == "7"


class TestActivityValue:
    """Tests for ActivityValue Value Object."""

    def test_creation_basic(self) -> None:
        """Test basic creation."""
        av = ActivityValue(value=100.0, unit="nM")
        assert av.value == pytest.approx(100.0)
        assert av.unit == "nM"
        assert av.relation == RelationOperator.EQUAL

    def test_creation_with_relation(self) -> None:
        """Test creation with custom relation."""
        av = ActivityValue(
            value=10.0, unit="μM", relation=RelationOperator.GREATER_THAN
        )
        assert av.value == pytest.approx(10.0)
        assert av.unit == "μM"
        assert av.relation == RelationOperator.GREATER_THAN

    def test_zero_value_valid(self) -> None:
        """Test zero value is valid."""
        av = ActivityValue(value=0.0, unit="nM")
        assert av.value == pytest.approx(0.0)

    def test_negative_value_raises(self) -> None:
        """Test negative value raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            ActivityValue(value=-1.0, unit="nM")

    def test_empty_unit_raises(self) -> None:
        """Test empty unit raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ActivityValue(value=100.0, unit="")

    def test_is_exact_property(self) -> None:
        """Test is_exact property."""
        exact = ActivityValue(value=100.0, unit="nM", relation=RelationOperator.EQUAL)
        bound = ActivityValue(
            value=100.0, unit="nM", relation=RelationOperator.GREATER_THAN
        )
        assert exact.is_exact is True
        assert bound.is_exact is False

    def test_is_bounded_property(self) -> None:
        """Test is_bounded property."""
        exact = ActivityValue(value=100.0, unit="nM", relation=RelationOperator.EQUAL)
        bound = ActivityValue(
            value=100.0, unit="nM", relation=RelationOperator.LESS_THAN
        )
        assert exact.is_bounded is False
        assert bound.is_bounded is True

    def test_from_raw_complete(self) -> None:
        """Test from_raw with all values."""
        av = ActivityValue.from_raw(value=50.0, unit="μM", relation=">")
        assert av is not None
        assert av.value == pytest.approx(50.0)
        assert av.unit == "μM"
        assert av.relation == RelationOperator.GREATER_THAN

    def test_from_raw_no_relation(self) -> None:
        """Test from_raw without relation defaults to EQUAL."""
        av = ActivityValue.from_raw(value=100.0, unit="nM", relation=None)
        assert av is not None
        assert av.relation == RelationOperator.EQUAL

    def test_from_raw_none_value(self) -> None:
        """Test from_raw with None value returns None."""
        assert ActivityValue.from_raw(value=None, unit="nM") is None

    def test_from_raw_none_unit(self) -> None:
        """Test from_raw with None unit returns None."""
        assert ActivityValue.from_raw(value=100.0, unit=None) is None

    def test_to_concentration(self) -> None:
        """Test conversion to Concentration."""
        av = ActivityValue(value=100.0, unit="nM")
        conc = av.to_concentration()
        assert conc.value == pytest.approx(100.0)
        from bioetl.domain.value_objects import ConcentrationUnit

        assert conc.unit == ConcentrationUnit.NANOMOLAR

    def test_to_concentration_invalid_unit(self) -> None:
        """Test conversion with invalid unit raises ValueError."""
        av = ActivityValue(value=100.0, unit="kg")
        with pytest.raises(ValueError, match="Unknown concentration unit"):
            av.to_concentration()

    def test_activity_value__immutability__11919306(self) -> None:
        """Test ActivityValue is immutable (frozen dataclass)."""
        av = ActivityValue(value=100.0, unit="nM")
        with pytest.raises(Exception):  # FrozenInstanceError
            av.value = 200.0  # type: ignore[misc]

    def test_equality_by_all_fields(self) -> None:
        """Test equality considers all fields."""
        av1 = ActivityValue(value=100.0, unit="nM", relation=RelationOperator.EQUAL)
        av2 = ActivityValue(value=100.0, unit="nM", relation=RelationOperator.EQUAL)
        av3 = ActivityValue(value=100.0, unit="nM", relation=RelationOperator.LESS_THAN)
        assert av1 == av2
        assert av1 != av3

    def test_activity_value__hash_consistency__49aaab7a(self) -> None:
        """Test hash is consistent with equality."""
        av1 = ActivityValue(value=100.0, unit="nM")
        av2 = ActivityValue(value=100.0, unit="nM")
        assert hash(av1) == hash(av2)

    def test_activity_value__str__92e5323e(self) -> None:
        """Test string representation."""
        av = ActivityValue(
            value=100.0, unit="nM", relation=RelationOperator.GREATER_THAN
        )
        assert str(av) == "> 100.0 nM"

    def test_activity_value__can_be_used_in_set__9a376f90(self) -> None:
        """Test ActivityValue can be used in set."""
        values = {
            ActivityValue(value=100.0, unit="nM"),
            ActivityValue(value=100.0, unit="nM"),
            ActivityValue(value=50.0, unit="nM"),
        }
        assert len(values) == 2
