"""Hypothesis strategies for property-based testing.

This module provides reusable Hypothesis strategies for generating test data
across the BioETL test suite. Strategies are designed to generate realistic
but varied data to test edge cases and robustness.

Example usage:
    from hypothesis import given
    from tests.strategies import chembl_activity_strategy, arbitrary_record_strategy

    @given(record=chembl_activity_strategy())
    def test_transformer_handles_chembl_records(record: dict):
        result = transformer.transform(record)
        assert result is not None

    @given(records=st.lists(arbitrary_record_strategy(), max_size=10))
    def test_validator_never_crashes(records: list[dict]):
        result = validator.validate(records)
        assert isinstance(result.valid, bool)
"""

from __future__ import annotations

from typing import Any

from hypothesis import strategies as st

# Generic primitive types for JSON-compatible data
json_primitive = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(),
)

# Recursive JSON-like structure (simplified for depth)
json_value = st.recursive(
    json_primitive,
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
    max_leaves=10,
)


def arbitrary_record_strategy() -> st.SearchStrategy[dict[str, Any]]:
    """Generate arbitrary dictionaries representing raw records.

    Creates random JSON-like dictionaries for fuzz testing transformers,
    validators, and other record-processing components.

    Returns:
        SearchStrategy that generates dict[str, Any] with random keys/values.

    Example:
        >>> from hypothesis import given, settings
        >>> from tests.strategies import arbitrary_record_strategy
        >>>
        >>> @given(record=arbitrary_record_strategy())
        >>> @settings(max_examples=100)
        >>> def test_transformer_robustness(record: dict):
        ...     # Transformer should handle any input without crashing
        ...     try:
        ...         result = transformer.transform(record)
        ...     except ValidationError:
        ...         pass  # Expected for invalid data
        ...     except (TypeError, ValueError) as e:
        ...         pytest.fail(f"Unexpected exception: {e}")
    """
    return st.dictionaries(
        keys=st.text(),
        values=json_value,
        max_size=20,  # Limit size to avoid slow tests
    )


def chembl_activity_strategy() -> st.SearchStrategy[dict[str, Any]]:
    """Generate records that look like ChEMBL activity data.

    Creates dictionaries with structure similar to ChEMBL API responses.
    Required fields (activity_id, molecule_id) are always present,
    while optional fields may contain valid or edge-case values.

    Returns:
        SearchStrategy that generates ChEMBL-like activity records.

    Example:
        >>> from hypothesis import given, settings
        >>> from tests.strategies import chembl_activity_strategy
        >>>
        >>> @given(record=chembl_activity_strategy())
        >>> @settings(max_examples=50)
        >>> def test_activity_transformer(record: dict):
        ...     # Test that transformer handles various activity formats
        ...     result = activity_transformer.transform(record)
        ...     assert "activity_id" in record  # Required field present
        ...
        >>> # Can also generate lists of activities
        >>> @given(records=st.lists(chembl_activity_strategy(), min_size=1, max_size=10))
        >>> def test_batch_processing(records: list[dict]):
        ...     results = transformer.transform_batch(records)
        ...     assert len(results) <= len(records)
    """
    return st.fixed_dictionaries(
        {
            "activity_id": st.one_of(st.integers(), st.text()),
            "molecule_id": st.text(),
        },
        optional={
            "target_id": st.text(),
            "standard_type": st.text(),
            "standard_value": st.one_of(st.floats(), st.text()),
            "standard_units": st.text(),
            "ligand_efficiency": st.one_of(
                st.none(),
                st.dictionaries(st.text(), st.one_of(st.floats(), st.text())),
            ),
        },
    )
