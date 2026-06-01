"""Tests for ColumnQualifier value object."""

import pytest
from bioetl.domain.value_objects.column_qualifier import ColumnQualifier


pytestmark = pytest.mark.unit

class TestColumnQualifier:
    """Tests for ColumnQualifier."""

    def test_str_representation(self) -> None:
        """String representation is provider.entity.field."""
        q = ColumnQualifier("chembl", "publication", "title")
        assert str(q) == "chembl.publication.title"

    def test_prefix_property(self) -> None:
        """Prefix is provider.entity without field."""
        q = ColumnQualifier("crossref", "publication", "abstract")
        assert q.prefix == "crossref.publication"

    def test_from_pipeline_valid(self) -> None:
        """Parse valid pipeline name."""
        q = ColumnQualifier.from_pipeline("chembl_publication", "title")
        assert q.provider == "chembl"
        assert q.entity == "publication"
        assert q.field == "title"

    def test_from_pipeline_invalid_format(self) -> None:
        """Reject pipeline without underscore."""
        with pytest.raises(ValueError, match="must be in format"):
            ColumnQualifier.from_pipeline("chemblpublication", "title")

    def test_parse_qualified_name(self) -> None:
        """Parse qualified name back to object."""
        q = ColumnQualifier.parse("chembl.publication.title")
        assert q.provider == "chembl"
        assert q.entity == "publication"
        assert q.field == "title"

    def test_parse_invalid_format(self) -> None:
        """Reject name without 3 parts."""
        with pytest.raises(ValueError, match="exactly 3 parts"):
            ColumnQualifier.parse("chembl.title")

    def test_is_join_key_true(self) -> None:
        """DOI is a join key."""
        q = ColumnQualifier("chembl", "publication", "doi")
        assert q.is_join_key is True

    def test_is_join_key_false(self) -> None:
        """Title is not a join key."""
        q = ColumnQualifier("chembl", "publication", "title")
        assert q.is_join_key is False

    def test_is_join_key_case_insensitive(self) -> None:
        """Join key check is case-insensitive."""
        q = ColumnQualifier("chembl", "publication", "DOI")
        assert q.is_join_key is True

    def test_column_qualifier__immutability__d00b0839(self) -> None:
        """ColumnQualifier is immutable."""
        q = ColumnQualifier("chembl", "publication", "title")
        with pytest.raises(AttributeError):
            q.provider = "crossref"  # type: ignore[misc]

    def test_normalization_lowercase(self) -> None:
        """Fields are normalized to lowercase."""
        q = ColumnQualifier("ChEMBL", "Publication", "TITLE")
        assert q.provider == "chembl"
        assert q.entity == "publication"
        assert q.field == "title"

    def test_normalization_strips_whitespace(self) -> None:
        """Fields are stripped of whitespace."""
        q = ColumnQualifier("  chembl  ", "  publication  ", "  title  ")
        assert q.provider == "chembl"
        assert q.entity == "publication"
        assert q.field == "title"

    def test_column_qualifier__provider_raises__731aead8(self) -> None:
        """Empty provider raises ValueError."""
        with pytest.raises(ValueError, match="provider cannot be empty"):
            ColumnQualifier("", "publication", "title")

    def test_empty_entity_raises(self) -> None:
        """Empty entity raises ValueError."""
        with pytest.raises(ValueError, match="entity cannot be empty"):
            ColumnQualifier("chembl", "", "title")

    def test_empty_field_raises(self) -> None:
        """Empty field raises ValueError."""
        with pytest.raises(ValueError, match="field cannot be empty"):
            ColumnQualifier("chembl", "publication", "")

    def test_is_qualified_true(self) -> None:
        """Detect qualified column name."""
        assert ColumnQualifier.is_qualified("chembl.publication.title") is True

    def test_is_qualified_false_two_parts(self) -> None:
        """Reject column with 2 parts."""
        assert ColumnQualifier.is_qualified("chembl.title") is False

    def test_is_qualified_false_no_dots(self) -> None:
        """Reject column without dots."""
        assert ColumnQualifier.is_qualified("title") is False

    def test_is_qualified_false_empty_parts(self) -> None:
        """Reject column with empty parts."""
        assert ColumnQualifier.is_qualified("chembl..title") is False
