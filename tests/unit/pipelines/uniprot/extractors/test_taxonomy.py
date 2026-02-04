"""Unit tests for TaxonomyExtractor."""

from __future__ import annotations

import pytest

from bioetl.application.pipelines.uniprot.extractors import TaxonomyExtractor


class TestExtractSuperkingdom:
    """Tests for extract_superkingdom method."""

    def test_valid_eukaryota(self) -> None:
        """Extract superkingdom from valid eukaryotic lineage."""
        lineage = [
            "Eukaryota",
            "Metazoa",
            "Chordata",
            "Mammalia",
            "Primates",
            "Hominidae",
            "Homo",
        ]
        assert TaxonomyExtractor.extract_superkingdom(lineage) == "Eukaryota"

    def test_valid_bacteria(self) -> None:
        """Extract superkingdom from bacterial lineage."""
        lineage = ["Bacteria", "Proteobacteria", "Gammaproteobacteria"]
        assert TaxonomyExtractor.extract_superkingdom(lineage) == "Bacteria"

    def test_valid_archaea(self) -> None:
        """Extract superkingdom from archaeal lineage."""
        lineage = ["Archaea", "Euryarchaeota", "Methanobacteria"]
        assert TaxonomyExtractor.extract_superkingdom(lineage) == "Archaea"

    def test_valid_viruses(self) -> None:
        """Extract superkingdom from viral lineage."""
        lineage = ["Viruses", "Riboviria", "Orthornavirae"]
        assert TaxonomyExtractor.extract_superkingdom(lineage) == "Viruses"

    def test_empty_list(self) -> None:
        """Return None for empty lineage list."""
        assert TaxonomyExtractor.extract_superkingdom([]) is None

    def test_none_input(self) -> None:
        """Return None for None input."""
        assert TaxonomyExtractor.extract_superkingdom(None) is None

    def test_invalid_type_string(self) -> None:
        """Return None for string input."""
        assert TaxonomyExtractor.extract_superkingdom("not a list") is None

    def test_invalid_type_dict(self) -> None:
        """Return None for dict input."""
        assert TaxonomyExtractor.extract_superkingdom({"lineage": []}) is None

    def test_whitespace_trimmed(self) -> None:
        """Trim whitespace from superkingdom value."""
        lineage = ["  Eukaryota  ", "Metazoa"]
        assert TaxonomyExtractor.extract_superkingdom(lineage) == "Eukaryota"

    def test_empty_string_element(self) -> None:
        """Return None if superkingdom is empty string."""
        lineage = ["", "Metazoa"]
        assert TaxonomyExtractor.extract_superkingdom(lineage) is None

    def test_non_string_element(self) -> None:
        """Return None if superkingdom is not a string."""
        lineage = [123, "Metazoa"]
        assert TaxonomyExtractor.extract_superkingdom(lineage) is None


class TestExtractPhylum:
    """Tests for extract_phylum method."""

    def test_valid_phylum(self) -> None:
        """Extract phylum from valid lineage."""
        lineage = ["Eukaryota", "Chordata", "Mammalia"]
        assert TaxonomyExtractor.extract_phylum(lineage) == "Chordata"

    def test_short_list_single_element(self) -> None:
        """Return None for single-element list."""
        lineage = ["Eukaryota"]
        assert TaxonomyExtractor.extract_phylum(lineage) is None

    def test_empty_list(self) -> None:
        """Return None for empty list."""
        assert TaxonomyExtractor.extract_phylum([]) is None

    def test_none_input(self) -> None:
        """Return None for None input."""
        assert TaxonomyExtractor.extract_phylum(None) is None

    def test_whitespace_trimmed(self) -> None:
        """Trim whitespace from phylum value."""
        lineage = ["Eukaryota", "  Chordata  ", "Mammalia"]
        assert TaxonomyExtractor.extract_phylum(lineage) == "Chordata"

    def test_empty_string_phylum(self) -> None:
        """Return None if phylum is empty string."""
        lineage = ["Eukaryota", "", "Mammalia"]
        assert TaxonomyExtractor.extract_phylum(lineage) is None

    def test_non_string_phylum(self) -> None:
        """Return None if phylum is not a string."""
        lineage = ["Eukaryota", 42, "Mammalia"]
        assert TaxonomyExtractor.extract_phylum(lineage) is None


class TestExtractGenus:
    """Tests for extract_genus method."""

    def test_valid_genus(self) -> None:
        """Extract genus (second-to-last) from valid lineage."""
        lineage = [
            "Eukaryota",
            "Metazoa",
            "Chordata",
            "Mammalia",
            "Primates",
            "Hominidae",
            "Homo",
        ]
        assert TaxonomyExtractor.extract_genus(lineage) == "Hominidae"

    def test_two_elements(self) -> None:
        """Extract genus from two-element list."""
        lineage = ["Eukaryota", "Species"]
        assert TaxonomyExtractor.extract_genus(lineage) == "Eukaryota"

    def test_short_list_single_element(self) -> None:
        """Return None for single-element list."""
        lineage = ["Eukaryota"]
        assert TaxonomyExtractor.extract_genus(lineage) is None

    def test_empty_list(self) -> None:
        """Return None for empty list."""
        assert TaxonomyExtractor.extract_genus([]) is None

    def test_none_input(self) -> None:
        """Return None for None input."""
        assert TaxonomyExtractor.extract_genus(None) is None

    def test_whitespace_trimmed(self) -> None:
        """Trim whitespace from genus value."""
        lineage = ["Eukaryota", "  Hominidae  ", "Homo"]
        assert TaxonomyExtractor.extract_genus(lineage) == "Hominidae"

    def test_empty_string_genus(self) -> None:
        """Return None if genus is empty string."""
        lineage = ["Eukaryota", "", "Homo"]
        assert TaxonomyExtractor.extract_genus(lineage) is None


class TestExtractAll:
    """Tests for extract_all method."""

    def test_valid_full_lineage(self) -> None:
        """Extract all components from valid lineage."""
        lineage = [
            "Eukaryota",
            "Chordata",
            "Mammalia",
            "Primates",
            "Hominidae",
            "Homo",
        ]
        result = TaxonomyExtractor.extract_all(lineage)
        assert result["superkingdom"] == "Eukaryota"
        assert result["phylum"] == "Chordata"
        assert result["genus"] == "Hominidae"

    def test_none_input(self) -> None:
        """Return dict with None values for None input."""
        result = TaxonomyExtractor.extract_all(None)
        assert result == {"superkingdom": None, "phylum": None, "genus": None}

    def test_empty_list(self) -> None:
        """Return dict with None values for empty list."""
        result = TaxonomyExtractor.extract_all([])
        assert result == {"superkingdom": None, "phylum": None, "genus": None}

    def test_single_element(self) -> None:
        """Handle single-element list correctly."""
        lineage = ["Bacteria"]
        result = TaxonomyExtractor.extract_all(lineage)
        assert result["superkingdom"] == "Bacteria"
        assert result["phylum"] is None
        assert result["genus"] is None

    def test_two_elements(self) -> None:
        """Handle two-element list correctly."""
        lineage = ["Eukaryota", "Chordata"]
        result = TaxonomyExtractor.extract_all(lineage)
        assert result["superkingdom"] == "Eukaryota"
        assert result["phylum"] == "Chordata"
        assert result["genus"] == "Eukaryota"  # len-2 = index 0

    def test_invalid_type(self) -> None:
        """Return dict with None values for invalid type."""
        result = TaxonomyExtractor.extract_all("not a list")
        assert result == {"superkingdom": None, "phylum": None, "genus": None}

    def test_dict_keys(self) -> None:
        """Verify returned dict has correct keys."""
        result = TaxonomyExtractor.extract_all(None)
        assert set(result.keys()) == {"superkingdom", "phylum", "genus"}
