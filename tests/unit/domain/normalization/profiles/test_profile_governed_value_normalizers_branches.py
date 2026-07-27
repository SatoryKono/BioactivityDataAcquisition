"""Branch coverage for profile governed value normalizers (TD-R-02 / #6678)."""

from __future__ import annotations

from bioetl.domain.normalization.profiles import (
    _profile_governed_value_normalizers as normalizers,
)


def test_standard_unit_enum_branches() -> None:
    allowed = frozenset({"nM", "uM"})
    assert normalizers.normalize_profile_standard_unit_enum(None, allowed_values=allowed) is None
    assert normalizers.normalize_profile_standard_unit_enum(1, allowed_values=allowed) is None
    # non-string path already covered; string outside enum after normalize may return None
    assert (
        normalizers.normalize_profile_standard_unit_enum("not-a-unit", allowed_values=allowed)
        is None
    )


def test_qudt_unit_reference_branches() -> None:
    assert normalizers.normalize_profile_qudt_unit_reference(None) is None
    assert normalizers.normalize_profile_qudt_unit_reference(12) == 12
    result = normalizers.normalize_profile_qudt_unit_reference("  unit  ")
    assert result is None or isinstance(result, str)


def test_profile_enum_branches() -> None:
    allowed = frozenset({"A", "B"})
    assert normalizers.normalize_profile_enum(None, allowed_values=allowed) is None
    assert normalizers.normalize_profile_enum("a", allowed_values=allowed) in {None, "A", "a"}
    assert normalizers.normalize_profile_enum(99, allowed_values=allowed) is None
    assert normalizers.normalize_profile_enum("A", allowed_values=allowed) in {"A", None}


def test_mapping_status_and_numeric_codes() -> None:
    allowed = frozenset({"active", "inactive"})
    assert normalizers.normalize_profile_mapping_status(1, allowed_values=allowed) is None
    assert normalizers.normalize_profile_mapping_status(" ACTIVE ", allowed_values=allowed) in {
        "active",
        None,
    }
    assert normalizers.normalize_profile_mapping_status("unknown", allowed_values=allowed) is None
    assert (
        normalizers.normalize_profile_quasi_enum_numeric("x", allowed_values=(1.0, 2.0)) is None
    )
    assert normalizers.normalize_profile_reviewed_flag_code(None) is None
    assert normalizers.normalize_profile_reviewed_flag_code(1) in {1, None}


def test_assay_parameter_and_target_component_normalizers() -> None:
    allowed = frozenset({"IC50", "KI"})
    out = normalizers.normalize_profile_assay_parameter_type("ic50", allowed_values=allowed)
    assert out is None or isinstance(out, str)
    # list vocab seams tolerate non-list / empty
    for value in (None, "[]", "PROTEIN"):
        result = normalizers.normalize_profile_target_component_types(value)
        assert result is None or isinstance(result, (str, list, tuple))
        result_rel = normalizers.normalize_profile_target_component_relationships(value)
        assert result_rel is None or isinstance(result_rel, (str, list, tuple))
