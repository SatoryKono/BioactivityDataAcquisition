"""Tests for normalization identifiers module."""

from __future__ import annotations

from typing import Any, cast

import pytest

from bioetl.domain.normalization.identifiers import (
    normalize_doi,
    normalize_ontology_id,
    normalize_pmc_id,
    normalize_pmid,
    strip_doi_prefix,
)

pytestmark = pytest.mark.unit

LEGACY_HTTP_DOI = "http" + "://doi.org/10.1234/test"


class TestStripDOIPrefix:
    """Test DOI prefix stripping."""

    def test_strip_d_o_i_prefix__strip_doi_prefix__c34a1031(self) -> None:
        """Test stripping various DOI prefixes."""
        assert strip_doi_prefix("https://doi.org/10.1234/test") == "10.1234/test"
        assert strip_doi_prefix(LEGACY_HTTP_DOI) == "10.1234/test"
        assert strip_doi_prefix("doi:10.1234/test") == "10.1234/test"
        assert strip_doi_prefix("DOI:10.1234/test") == "10.1234/test"
        assert strip_doi_prefix("10.1234/test") == "10.1234/test"

    def test_strip_doi_prefix_case_insensitive(self) -> None:
        """Test case-insensitive prefix stripping."""
        assert strip_doi_prefix("HTTPS://DOI.ORG/10.1234/test") == "10.1234/test"
        assert strip_doi_prefix("DoI:10.1234/test") == "10.1234/test"

    def test_strip_doi_prefix_with_spaces(self) -> None:
        """Test prefix stripping with whitespace."""
        assert strip_doi_prefix("  https://doi.org/10.1234/test  ") == "10.1234/test"
        assert strip_doi_prefix(f"\t{LEGACY_HTTP_DOI}\t") == "10.1234/test"


class TestNormalizeDOI:
    """Test DOI normalization."""

    def test_normalize_doi_basic(self) -> None:
        """Test basic DOI normalization."""
        assert normalize_doi("10.1234/test") == "10.1234/test"
        assert normalize_doi("10.1234/TEST") == "10.1234/test"
        assert normalize_doi("HTTPS://DOI.ORG/10.1234/test") == "10.1234/test"

    def test_normalize_doi_with_prefixes(self) -> None:
        """Test DOI normalization with various prefixes."""
        assert normalize_doi("https://doi.org/10.1234/test") == "10.1234/test"
        assert normalize_doi(LEGACY_HTTP_DOI) == "10.1234/test"
        assert normalize_doi("doi:10.1234/test") == "10.1234/test"
        assert normalize_doi("DOI:10.1234/test") == "10.1234/test"

    def test_normalize_doi_whitespace(self) -> None:
        """Test DOI normalization with whitespace."""
        assert normalize_doi("  10.1234/test  ") == "10.1234/test"
        assert normalize_doi("\t10.1234/test\n") == "10.1234/test"

    def test_normalize_doi_none_and_empty(self) -> None:
        """Test None and empty string handling."""
        assert normalize_doi(None) is None
        assert normalize_doi("") is None
        assert normalize_doi("   ") is None

    def test_normalize_doi_invalid(self) -> None:
        """Test invalid DOI handling."""
        assert normalize_doi("   ") is None
        assert normalize_doi("invalid") == "invalid"


class TestNormalizePMID:
    """Test PMID normalization."""

    def test_normalize_pmid_string(self) -> None:
        """Test PMID normalization from string."""
        assert normalize_pmid("1234567") == "1234567"
        assert normalize_pmid("  1234567  ") == "1234567"
        assert normalize_pmid("001234567") == "1234567"
        assert normalize_pmid("PMID:001234567") == "1234567"
        assert normalize_pmid("https://pubmed.ncbi.nlm.nih.gov/1234567/") == "1234567"

    def test_normalize_pmid_integer(self) -> None:
        """Test PMID normalization from integer."""
        assert normalize_pmid(1234567) == "1234567"
        # Test with string that has leading zeros
        assert normalize_pmid("001234567") == "1234567"

    def test_normalize_pmid_invalid(self) -> None:
        """Test invalid PMID handling."""
        assert normalize_pmid("abc123") is None
        assert normalize_pmid("12345678901") is None  # Too long
        assert normalize_pmid("123") == "123"  # Short PMIDs are allowed
        assert normalize_pmid("") is None
        assert normalize_pmid("   ") is None

    def test_normalize_pmid_none(self) -> None:
        """Test None handling."""
        assert normalize_pmid(None) is None

    def test_normalize_pmid_boolean(self) -> None:
        """Test boolean handling."""
        assert normalize_pmid(True) is None
        assert normalize_pmid(False) is None


class TestNormalizePMCID:
    """Test PMC ID normalization."""

    def test_normalize_pmc_id_basic(self) -> None:
        """Test basic PMC ID normalization."""
        assert normalize_pmc_id("PMC1234567") == "PMC1234567"
        assert normalize_pmc_id("pmc1234567") == "PMC1234567"
        assert normalize_pmc_id("1234567") == "PMC1234567"

    def test_normalize_pmc_id_with_spaces(self) -> None:
        """Test PMC ID normalization with whitespace."""
        assert normalize_pmc_id("  PMC1234567  ") == "PMC1234567"
        assert normalize_pmc_id("\t1234567\n") == "PMC1234567"

    def test_normalize_pmc_id_none_and_empty(self) -> None:
        """Test None and empty string handling."""
        assert normalize_pmc_id(None) is None
        assert normalize_pmc_id("") is None
        assert normalize_pmc_id("   ") is None

    def test_normalize_pmc_id_invalid(self) -> None:
        """Test invalid PMC ID handling."""
        assert normalize_pmc_id("invalid") == "PMCinvalid"
        assert normalize_pmc_id("ABC123") == "PMCABC123"


class TestNormalizeOntologyID:
    """Test ontology ID normalization."""

    def test_normalize_ontology_id_go(self) -> None:
        """Test GO ontology ID normalization."""
        assert normalize_ontology_id("GO:0008150") == "GO_0008150"
        assert normalize_ontology_id("go:0008150") == "GO_0008150"
        assert normalize_ontology_id("0008150") == "0008150"  # Unknown format preserved

    def test_normalize_ontology_id_clo(self) -> None:
        """Test CLO ontology ID normalization."""
        assert normalize_ontology_id("CLO:0000045") == "CLO_0000045"
        assert normalize_ontology_id("clo:0000045") == "CLO_0000045"
        assert (
            normalize_ontology_id("cl:0000045") == "CL_0000045"
        )  # CL prefix preserved

    def test_normalize_ontology_id_efo(self) -> None:
        """Test EFO ontology ID normalization."""
        assert normalize_ontology_id("EFO:0000319") == "EFO_0000319"
        assert normalize_ontology_id("efo:0000319") == "EFO_0000319"
        assert normalize_ontology_id("  EFO:0000319  ") == "EFO_0000319"

    def test_normalize_ontology_id_uberon(self) -> None:
        """Test UBERON ontology ID normalization."""
        assert normalize_ontology_id("UBERON:0002107") == "UBERON_0002107"
        assert normalize_ontology_id("uberon:0002107") == "UBERON_0002107"

    def test_normalize_ontology_id_chebi(self) -> None:
        """Test CHEBI ontology ID normalization."""
        assert (
            normalize_ontology_id("CHEBI:12345") == "CHEBI_12345"
        )  # No zero-padding for colon format
        assert normalize_ontology_id("chebi:12345") == "CHEBI_12345"

    def test_normalize_ontology_id_bto(self) -> None:
        """Test BTO ontology ID normalization."""
        assert normalize_ontology_id("BTO:0000089") == "BTO_0000089"
        assert normalize_ontology_id("bto:0000089") == "BTO_0000089"
        assert normalize_ontology_id("bto_0000089") == "BTO_0000089"

    def test_normalize_ontology_id_caloha(self) -> None:
        """Test CALOHA ID normalization."""
        assert normalize_ontology_id("TS-1234") == "TS-1234"
        assert normalize_ontology_id("ts-1234") == "TS-1234"
        assert normalize_ontology_id("CALOHA:1234") == "TS-1234"
        assert normalize_ontology_id("caloha_ts-1234") == "TS-1234"

    def test_normalize_ontology_id_obo_uri(self) -> None:
        """Test OBO URI normalization."""
        assert (
            normalize_ontology_id("https://purl.obolibrary.org/obo/BTO_0000089")
            == "BTO_0000089"
        )
        assert (
            normalize_ontology_id("https://purl.obolibrary.org/obo/BAO_0000190")
            == "BAO_0000190"
        )

    def test_normalize_ontology_id_zero_padding(self) -> None:
        """Test zero-padding for space format IDs."""
        assert (
            normalize_ontology_id("GO:12345") == "GO_12345"
        )  # Colon format no padding
        assert normalize_ontology_id("CL:123") == "CL_123"  # Colon format no padding
        assert (
            normalize_ontology_id("EFO 1") == "EFO_0000001"
        )  # Space format gets padding
        assert (
            normalize_ontology_id("UBERON 7") == "UBERON_0000007"
        )  # Space format gets padding

    def test_normalize_ontology_id_none_and_empty(self) -> None:
        """Test None and empty string handling."""
        assert normalize_ontology_id(cast(Any, None)) is None
        assert normalize_ontology_id("") == ""  # Empty string returns empty string
        assert normalize_ontology_id("   ") is None  # Whitespace-only returns None

    def test_normalize_ontology_id_invalid(self) -> None:
        """Test invalid ontology ID handling."""
        assert normalize_ontology_id("invalid") == "invalid"  # Unknown format preserved
        assert normalize_ontology_id("ABC123") == "ABC123"  # Unknown format preserved
