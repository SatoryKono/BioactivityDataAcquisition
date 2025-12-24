"""Hypothesis strategies for property-based testing."""

from __future__ import annotations

from typing import Any

from hypothesis import strategies as st

# Generic primitive types
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
    """Generate arbitrary dictionaries representing raw records."""
    return st.dictionaries(
        keys=st.text(),
        values=json_value,
        max_size=20,  # Limit size to avoid slow tests
    )


def chembl_activity_strategy() -> st.SearchStrategy[dict[str, Any]]:
    """Generate records that look like ChEMBL activities.

    Ensures minimal required fields are present most of the time to test success paths,
    but allows random values to test validation robustness.
    """
    return st.fixed_dictionaries(
        {
            "activity_id": st.one_of(st.integers(), st.text()),
            "molecule_chembl_id": st.text(),
        },
        optional={
            "target_chembl_id": st.text(),
            "standard_type": st.text(),
            "standard_value": st.one_of(st.floats(), st.text()),
            "standard_units": st.text(),
            "ligand_efficiency": st.one_of(
                st.none(),
                st.dictionaries(st.text(), st.one_of(st.floats(), st.text())),
            ),
        },
    )
