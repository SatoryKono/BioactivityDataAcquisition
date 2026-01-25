"""Tests for ColumnQualifier Value Object."""

import pytest
from dataclasses import FrozenInstanceError

from bioetl.domain.value_objects.column_qualifier import ColumnQualifier


def test_str_representation():
    """Test string representation follows {provider}.{entity}.{field} format."""
    qualifier = ColumnQualifier(provider="chembl", entity="publication", field="title")
    assert str(qualifier) == "chembl.publication.title"


def test_from_pipeline_valid():
    """Test creation from valid pipeline name."""
    qualifier = ColumnQualifier.from_pipeline("chembl_publication", "title")
    assert qualifier.provider == "chembl"
    assert qualifier.entity == "publication"
    assert qualifier.field == "title"


def test_from_pipeline_invalid_format():
    """Test validation of pipeline name format."""
    with pytest.raises(ValueError, match="Invalid pipeline name format"):
        ColumnQualifier.from_pipeline("chemblpublication", "title")


def test_parse_qualified_name():
    """Test parsing of qualified name string."""
    qualifier = ColumnQualifier.parse("chembl.publication.title")
    assert qualifier.provider == "chembl"
    assert qualifier.entity == "publication"
    assert qualifier.field == "title"


def test_parse_invalid_format():
    """Test parsing of invalid format raises error."""
    with pytest.raises(ValueError, match="Invalid qualified name format"):
        ColumnQualifier.parse("chembl.title")


def test_is_join_key():
    """Test identification of join keys."""
    assert ColumnQualifier("x", "y", "doi").is_join_key
    assert ColumnQualifier("x", "y", "pmid").is_join_key
    assert ColumnQualifier("x", "y", "pmc_id").is_join_key
    assert not ColumnQualifier("x", "y", "title").is_join_key


def test_immutability():
    """Test that object is immutable."""
    qualifier = ColumnQualifier("chembl", "pub", "title")
    with pytest.raises(FrozenInstanceError):
        qualifier.provider = "crossref"


def test_validation_empty_fields():
    """Test that empty fields are rejected."""
    with pytest.raises(ValueError, match="Provider cannot be empty"):
        ColumnQualifier("", "pub", "title")
    with pytest.raises(ValueError, match="Entity cannot be empty"):
        ColumnQualifier("chembl", "", "title")
    with pytest.raises(ValueError, match="Field cannot be empty"):
        ColumnQualifier("chembl", "pub", "")


def test_validation_lowercase():
    """Test that fields are automatically lowercased."""
    qualifier = ColumnQualifier("Chembl", "Pub", "Title")
    assert qualifier.provider == "chembl"
    assert qualifier.entity == "pub"
    assert qualifier.field == "title"
