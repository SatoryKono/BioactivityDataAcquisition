# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for the non-ChEMBL observed-value inventory report generator."""

from __future__ import annotations

import pytest

from scripts.engineering.qa import report_non_chembl_observed_value_inventory as report


pytestmark = pytest.mark.unit


def test_build_inventory_payload_covers_expected_non_chembl_sections() -> None:
    payload = report.build_inventory_payload()
    sections = payload["sections"]

    assert payload["source"] == (
        "tracked_non_chembl_bronze_fixtures_and_vcr_derived_edge_samples"
    )
    assert "publication_nested_vocab" in sections
    assert "crossref_publication_types" in sections
    assert "uniprot_semantic_payloads" in sections
    assert "uniprot_idmapping" in sections
    assert "pubchem_property_vocab" in sections

    publication_vocab = sections["publication_nested_vocab"]
    assert "posted-content" in sections["crossref_publication_types"]
    assert "journal" in publication_vocab["openalex"]["source_type"]
    assert "Clinical Trial" in publication_vocab["pubmed"]["publication_types"]
    assert "JournalArticle" in publication_vocab["semanticscholar"]["publication_types"]

    uniprot = sections["uniprot_semantic_payloads"]
    assert "PATHWAY" in uniprot["comment_types"]
    assert "Technical term" in uniprot["keyword_categories"]

    pubchem = sections["pubchem_property_vocab"]
    assert "IUPAC Name" in pubchem["label"]
    assert "Connectivity" in pubchem["name"]


def test_committed_artifacts_match_generator_output() -> None:
    if not report.DEFAULT_JSON_OUT.is_file() or not report.DEFAULT_MD_OUT.is_file():
        pytest.skip(
            "generated non-ChEMBL inventory artifacts are not present in this "
            "checkout (gitignored docs/reports/generated outputs)"
        )
    assert report.main(["--check"]) == 0
