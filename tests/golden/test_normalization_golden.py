"""
Golden tests for normalization determinism.
"""

from bioetl.domain.transform.impl.normalize import normalize_scalar
from bioetl.domain.transform.impl.serializer import serialize_list


def test_golden_complex_serialization():
    """
    Test serialization of a complex structure against a fixed golden string.
    Ensures stable sorting and formatting.
    """
    data = [
        {
            "b_field": "Value B",
            "a_field": 123,
            "c_field": None,  # Should be skipped
            "d_ignored": [1, 2],  # Nested list skipped
        },
        {"a_field": 456, "b_field": "Value B2"},
    ]

    # serialize_list -> serialize_dict (keys sorted)
    # Item 1: a_field:123|b_field:Value B
    # Item 2: a_field:456|b_field:Value B2
    # Joined by |

    expected = "a_field:123|b_field:Value B|a_field:456|b_field:Value B2"

    assert serialize_list(data) == expected


def test_golden_normalization_scalars():
    """
    Golden values for scalar normalization.
    """
    # ID mode
    assert normalize_scalar("  chembl123  ", mode="id") == "CHEMBL123"

    # Default mode (lower)
    assert normalize_scalar("  Value  ") == "value"

    # Float rounding
    assert normalize_scalar(3.14159265) == 3.142
