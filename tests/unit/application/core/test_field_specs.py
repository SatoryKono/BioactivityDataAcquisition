# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for field_specs module."""

from __future__ import annotations

import pytest

from bioetl.application.core.field_specs import (
    FLOAT,
    INT,
    PMID,
    STR,
    FieldGroup,
    FieldSpec,
    float_fields,
    int_fields,
    map_field,
    map_field_group,
    map_field_groups,
    map_fields,
    normalize_pmid,
    pmid_fields,
    simple_fields,
)

pytestmark = pytest.mark.unit


class TestFieldSpec:
    """Tests for FieldSpec dataclass."""

    def test_simple_spec(self) -> None:
        """Test basic field spec creation."""
        spec = FieldSpec("field_name")
        assert spec.source == "field_name"
        assert spec.target is None
        assert spec.converter is None
        assert spec.required is False
        assert spec.default is None

    def test_spec_with_target(self) -> None:
        """Test field spec with different target name."""
        spec = FieldSpec("source_field", target="target_field")
        assert spec.source == "source_field"
        assert spec.target == "target_field"

    def test_spec_with_converter(self) -> None:
        """Test field spec with converter."""
        spec = FieldSpec("value", converter=FLOAT)
        assert spec.converter is FLOAT

    def test_spec_immutable(self) -> None:
        """Test that FieldSpec is frozen."""
        spec = FieldSpec("field")
        with pytest.raises(AttributeError):
            spec.source = "other"  # type: ignore[misc]


class TestMapField:
    """Tests for map_field function."""

    def test_simple_mapping(self) -> None:
        """Test simple field mapping without conversion."""
        record = {"field": "value"}
        spec = FieldSpec("field")
        target, value = map_field(record, spec)
        assert target == "field"
        assert value == "value"

    def test_mapping_with_target(self) -> None:
        """Test field mapping with different target name."""
        record = {"src": "value"}
        spec = FieldSpec("src", target="dst")
        target, value = map_field(record, spec)
        assert target == "dst"
        assert value == "value"

    def test_mapping_with_int_converter(self) -> None:
        """Test field mapping with INT converter."""
        record = {"count": "42"}
        spec = FieldSpec("count", converter=INT)
        _, value = map_field(record, spec)
        assert value == 42
        assert isinstance(value, int)

    def test_mapping_with_float_converter(self) -> None:
        """Test field mapping with FLOAT converter."""
        record = {"value": "3.14"}
        spec = FieldSpec("value", converter=FLOAT)
        _, value = map_field(record, spec)
        assert value == pytest.approx(3.14)
        assert isinstance(value, float)

    def test_mapping_with_str_converter(self) -> None:
        """Test field mapping with STR converter."""
        record = {"id": 123}
        spec = FieldSpec("id", converter=STR)
        _, value = map_field(record, spec)
        assert value == "123"
        assert isinstance(value, str)

    def test_missing_field_returns_none(self) -> None:
        """Test that missing non-required field returns None."""
        record: dict[str, str] = {}
        spec = FieldSpec("missing")
        _, value = map_field(record, spec)
        assert value is None

    def test_none_value_returns_none(self) -> None:
        """Test that None value is preserved."""
        record = {"field": None}
        spec = FieldSpec("field")
        _, value = map_field(record, spec)
        assert value is None

    def test_required_field_missing_raises(self) -> None:
        """Test that missing required field raises ValueError."""
        record: dict[str, str] = {}
        spec = FieldSpec("required_field", required=True)
        with pytest.raises(ValueError, match=r"Required field.*missing"):
            map_field(record, spec)

    def test_required_field_none_raises(self) -> None:
        """Test that None value for required field raises ValueError."""
        record = {"required_field": None}
        spec = FieldSpec("required_field", required=True)
        with pytest.raises(ValueError, match=r"Required field.*missing"):
            map_field(record, spec)

    def test_default_value_when_missing(self) -> None:
        """Test that default value is used when field is missing."""
        record: dict[str, str] = {}
        spec = FieldSpec("missing", default="default_value")
        _, value = map_field(record, spec)
        assert value == "default_value"

    def test_converter_not_applied_to_none(self) -> None:
        """Test that converter is not applied to None values."""
        record = {"field": None}
        spec = FieldSpec("field", converter=INT)
        _, value = map_field(record, spec)
        assert value is None


class TestMapFields:
    """Tests for map_fields function."""

    def test_multiple_fields(self) -> None:
        """Test mapping multiple fields."""
        record = {
            "activity_id": 123,
            "value": "5.5",
            "type": "IC50",
        }
        specs = (
            FieldSpec("activity_id", converter=STR),
            FieldSpec("value", converter=FLOAT),
            FieldSpec("type"),
        )
        result = map_fields(record, specs)
        assert result == {
            "activity_id": "123",
            "value": pytest.approx(5.5),
            "type": "IC50",
        }

    def test_empty_specs(self) -> None:
        """Test mapping with empty specs."""
        record = {"field": "value"}
        result = map_fields(record, ())
        assert result == {}

    def test_all_missing_fields(self) -> None:
        """Test mapping when all fields are missing."""
        record: dict[str, str] = {}
        specs = (FieldSpec("a"), FieldSpec("b"))
        result = map_fields(record, specs)
        assert result == {"a": None, "b": None}


class TestFieldGroup:
    """Tests for FieldGroup and map_field_group."""

    def test_group_without_prefix(self) -> None:
        """Test field group without prefix."""
        record = {"a": "1", "b": "2"}
        group = FieldGroup(
            name="test_group",
            fields=(FieldSpec("a"), FieldSpec("b")),
        )
        result = map_field_group(record, group)
        assert result == {"a": "1", "b": "2"}

    def test_group_with_prefix(self) -> None:
        """Test field group with prefix."""
        record = {"bei": "1.5", "le": "0.3"}
        group = FieldGroup(
            name="ligand_efficiency",
            prefix="le_",
            fields=(
                FieldSpec("bei", converter=FLOAT),
                FieldSpec("le", converter=FLOAT),
            ),
        )
        result = map_field_group(record, group)
        assert result == {
            "le_bei": pytest.approx(1.5),
            "le_le": pytest.approx(0.3),
        }

    def test_multiple_groups(self) -> None:
        """Test mapping multiple field groups."""
        record = {"id": "123", "value": "5.5", "units": "nM"}
        groups = (
            FieldGroup(
                name="identifiers",
                fields=(FieldSpec("id", converter=STR),),
            ),
            FieldGroup(
                name="values",
                fields=(
                    FieldSpec("value", converter=FLOAT),
                    FieldSpec("units"),
                ),
            ),
        )
        result = map_field_groups(record, groups)
        assert result == {
            "id": "123",
            "value": pytest.approx(5.5),
            "units": "nM",
        }


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_simple_fields(self) -> None:
        """Test simple_fields convenience function."""
        specs = simple_fields("type", "units", "relation")
        assert len(specs) == 3
        assert all(spec.converter is None for spec in specs)
        assert [spec.source for spec in specs] == ["type", "units", "relation"]

    def test_int_fields(self) -> None:
        """Test int_fields convenience function."""
        specs = int_fields("count", "max_phase")
        assert len(specs) == 2
        assert all(spec.converter is INT for spec in specs)

    def test_float_fields(self) -> None:
        """Test float_fields convenience function."""
        specs = float_fields("value", "pchembl")
        assert len(specs) == 2
        assert all(spec.converter is FLOAT for spec in specs)

    def test_combined_specs(self) -> None:
        """Test combining different spec types."""
        record = {
            "type": "IC50",
            "count": "5",
            "value": "3.14",
        }
        specs = (
            *simple_fields("type"),
            *int_fields("count"),
            *float_fields("value"),
        )
        result = map_fields(record, specs)
        assert result == {
            "type": "IC50",
            "count": 5,
            "value": pytest.approx(3.14),
        }


class TestIntegrationWithChemblPatterns:
    """Integration tests simulating ChEMBL transformer patterns."""

    def test_activity_core_identifiers_pattern(self) -> None:
        """Test pattern similar to ActivityTransformer._map_core_identifiers."""
        record = {
            "activity_id": 12345,
            "molecule_id": "CHEMBL123",
            "target_id": "CHEMBL456",
            "record_id": "789",
            "src_id": "1",
        }

        specs = (
            FieldSpec("activity_id", converter=STR, required=True),
            FieldSpec("molecule_id", converter=STR, required=True),
            FieldSpec("target_id"),
            FieldSpec("record_id", converter=INT),
            FieldSpec("src_id", converter=INT),
        )

        result = map_fields(record, specs)

        assert result["activity_id"] == "12345"
        assert result["molecule_id"] == "CHEMBL123"
        assert result["target_id"] == "CHEMBL456"
        assert result["record_id"] == 789
        assert result["src_id"] == 1

    def test_activity_values_pattern(self) -> None:
        """Test pattern similar to ActivityTransformer._map_activity_values."""
        record = {
            "type": "IC50",
            "value": "5.5",
            "units": "nM",
            "relation": "=",
            "standard_value": "5500",
            "pchembl_value": "8.26",
        }

        specs = (
            *simple_fields("type", "units", "relation"),
            *float_fields("value", "standard_value", "pchembl_value"),
        )

        result = map_fields(record, specs)

        assert result["type"] == "IC50"
        assert result["units"] == "nM"
        assert result["value"] == pytest.approx(5.5)
        assert result["pchembl_value"] == pytest.approx(8.26)


class TestNormalizePmid:
    """Tests for normalize_pmid function.

    PubMed IDs should be normalized to string format for
    cross-provider consistency.
    """

    @pytest.mark.parametrize(
        "input_pmid,expected",
        [
            (12345678, "12345678"),
            ("12345678", "12345678"),
            ("  12345678  ", "12345678"),
            (1, "1"),
            ("1", "1"),
            (None, None),
            ("abc", None),  # invalid - non-numeric
            ("123abc", None),  # invalid - mixed
            ("", None),  # invalid - empty
            ("   ", None),  # invalid - whitespace only
            (0, None),  # invalid - zero
            ("0", None),  # invalid - zero string
            (-1, None),  # invalid - negative
            (True, None),  # invalid - boolean
            (False, None),  # invalid - boolean
            (12.5, None),  # invalid - float
            ([], None),  # invalid - list
            ({}, None),  # invalid - dict
        ],
    )
    def test_pmid_conversion(self, input_pmid, expected):
        """Test PMID normalization across various input types."""
        result = normalize_pmid(input_pmid)
        assert result == expected

    def test_leading_zeros_removed(self):
        """Test that leading zeros are removed from PMIDs."""
        assert normalize_pmid("00012345") == "12345"
        assert normalize_pmid("0001") == "1"

    def test_large_pmid(self):
        """Test large valid PMID."""
        assert normalize_pmid(9999999999) == "9999999999"
        assert normalize_pmid("9999999999") == "9999999999"


class TestPmidFields:
    """Tests for pmid_fields convenience function."""

    def test_pmid_fields_creates_specs(self):
        """Test pmid_fields creates correct field specs."""
        specs = pmid_fields("pubmed_id", "pubmed_id1")
        assert len(specs) == 2
        assert all(spec.converter is PMID for spec in specs)
        assert [spec.source for spec in specs] == ["pubmed_id", "pubmed_id1"]

    def test_pmid_field_in_mapping(self):
        """Test PMID field spec in actual mapping."""
        record = {"pubmed_id": 12345678}
        spec = FieldSpec("pubmed_id", converter=PMID)
        _, value = map_field(record, spec)
        assert value == "12345678"
        assert isinstance(value, str)

    def test_pmid_field_string_input(self):
        """Test PMID field spec with string input."""
        record = {"pubmed_id": "  87654321  "}
        spec = FieldSpec("pubmed_id", converter=PMID)
        _, value = map_field(record, spec)
        assert value == "87654321"

    def test_pmid_field_invalid_input(self):
        """Test PMID field spec with invalid input returns None."""
        record = {"pubmed_id": "not-a-number"}
        spec = FieldSpec("pubmed_id", converter=PMID)
        _, value = map_field(record, spec)
        assert value is None

    def test_pmid_field_none_input(self):
        """Test PMID field spec with None input."""
        record = {"pubmed_id": None}
        spec = FieldSpec("pubmed_id", converter=PMID)
        _, value = map_field(record, spec)
        assert value is None

    def test_combined_with_other_specs(self):
        """Test PMID fields combined with other spec types."""
        record = {
            "doc_1": "100",
            "doc_2": "200",
            "pubmed_id1": 12345678,
            "pubmed_id2": "87654321",
            "tid_tani": "0.85",
        }
        specs = (
            *int_fields("doc_1", "doc_2"),
            *pmid_fields("pubmed_id1", "pubmed_id2"),
            *float_fields("tid_tani"),
        )
        result = map_fields(record, specs)
        assert result["doc_1"] == 100
        assert result["doc_2"] == 200
        assert result["pubmed_id1"] == "12345678"
        assert result["pubmed_id2"] == "87654321"
        assert result["tid_tani"] == pytest.approx(0.85)
