"""Unit tests for composite_publication column ordering and names.

Verifies that the composite publication pipeline produces the expected
output columns in the correct order, based on the YAML configuration.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.domain.composite.config import ColumnGroupConfig


@pytest.fixture
def publication_config() -> dict:
    """Load real publication composite config."""
    config_path = Path("configs/composites/publication.yaml")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def column_groups(publication_config: dict) -> list[ColumnGroupConfig]:
    """Extract ColumnGroupConfig objects from publication config."""
    groups_data = publication_config["composite"]["merge"]["column_groups"]
    return [
        ColumnGroupConfig(
            name=g["name"],
            fields=tuple(g.get("fields", [])),
            pattern=g.get("pattern"),
            provider_order=tuple(g.get("provider_order", [])),
        )
        for g in groups_data
    ]


@pytest.fixture
def orderer(column_groups: list[ColumnGroupConfig]) -> ColumnOrderService:
    """Create ColumnOrderService with real publication groups."""
    logger = MagicMock()
    return ColumnOrderService(logger, column_groups=column_groups)


class TestCompositePublicationColumns:
    """Tests for composite_publication output columns."""

    def test_column_groups_count(self, column_groups: list[ColumnGroupConfig]) -> None:
        """Verify the number of semantic groups in the configuration."""
        assert len(column_groups) == 11

    def test_expected_group_names(self, column_groups: list[ColumnGroupConfig]) -> None:
        """Verify that all expected groups are present."""
        expected_names = {
            "system",
            "provider_ids",
            "journal",
            "pagination",
            "authors",
            "affiliations",
            "date",
            "subjects",
            "biomedical",
            "citations",
            "doc_type",
        }
        actual_names = {g.name for g in column_groups}
        assert actual_names == expected_names

    def test_total_base_fields_coverage(
        self, column_groups: list[ColumnGroupConfig]
    ) -> None:
        """Verify the total number of base fields covered by groups."""
        all_fields = []
        for g in column_groups:
            all_fields.extend(g.fields)

        # We expect around 100 base fields based on manual count
        assert len(all_fields) >= 90
        assert len(set(all_fields)) == len(all_fields), "Duplicate fields across groups"

    def test_persisted_system_columns_at_start(
        self, orderer: ColumnOrderService
    ) -> None:
        """Persisted system columns must be first; occurrence fields are not prioritized."""
        columns = [
            "chembl.publication.title",
            "entity_id",
            "_run_id",
            "doi",
        ]
        ordered = orderer.order_column_names(columns)

        assert ordered[0] == "entity_id"
        assert ordered[1] == "doi"
        assert ordered[-1] == "_run_id"

    def test_qualified_columns_ordering(self, orderer: ColumnOrderService) -> None:
        """Verify ordering of qualified columns for the same field."""
        # For 'title' in 'journal' group, provider_order is:
        # [pubmed, semanticscholar, chembl, crossref, openalex]
        columns = [
            "crossref.publication.title",
            "chembl.publication.title",
            "pubmed.publication.title",
            "semanticscholar.publication.title",
            "openalex.publication.title",
        ]
        ordered = orderer.order_column_names(columns)

        expected = [
            "pubmed.publication.title",
            "semanticscholar.publication.title",
            "chembl.publication.title",
            "crossref.publication.title",
            "openalex.publication.title",
        ]
        assert ordered == expected

    def test_inter_group_ordering(self, orderer: ColumnOrderService) -> None:
        """Verify that columns from different groups are ordered correctly."""
        columns = [
            "pubmed.publication.chemicals",  # biomedical
            "chembl.publication.title",  # journal
            "pubmed.publication.pmid",  # provider_ids
            "entity_id",  # system
        ]
        ordered = orderer.order_column_names(columns)

        # Order: system -> provider_ids -> journal -> biomedical
        assert ordered == [
            "entity_id",
            "pubmed.publication.pmid",
            "chembl.publication.title",
            "pubmed.publication.chemicals",
        ]

    def test_dq_fields_at_very_end(self, orderer: ColumnOrderService) -> None:
        """DQ fields must be the absolute last columns."""
        columns = [
            "_dq_error",
            "entity_id",
            "title",
            "_dq_warn",
        ]
        ordered = orderer.order_column_names(columns)

        assert ordered[-2] == "_dq_error"
        assert ordered[-1] == "_dq_warn"

    def test_full_schema_names_verification(self, orderer: ColumnOrderService) -> None:
        """Verify names of key columns in the final output."""
        # Simulate a realistic set of output columns
        columns = [
            "entity_id",
            "content_hash",
            "chembl.publication.publication_id",
            "pubmed.publication.pmid",
            "doi",
            "chembl.publication.title",
            "pubmed.publication.abstract",
            "pubmed.publication.authors_with_affiliations",
            "semanticscholar.publication.influential_citation_count",
            "openalex.publication.is_retracted",
            "pubmed.publication.chemicals",
            "_dq_error",
            "_dq_warn",
        ]

        ordered = orderer.order_column_names(columns)

        # Verify specific names exist in the output
        assert "chembl.publication.publication_id" in ordered
        assert "pubmed.publication.pmid" in ordered
        assert "pubmed.publication.authors_with_affiliations" in ordered
        assert "semanticscholar.publication.influential_citation_count" in ordered
        assert "pubmed.publication.chemicals" in ordered

        # Verify ordering of these keys
        # system -> provider_ids -> journal -> authors -> biomedical -> citations -> doc_type -> DQ
        # 1. entity_id, content_hash (system)
        # 2. chembl.publication.publication_id, pubmed.publication.pmid, doi
        #    (provider_ids / journal - wait, doi is in journal)
        # 3. chembl.publication.title, pubmed.publication.abstract (journal)
        # 4. pubmed.publication.authors_with_affiliations (authors)
        # 5. pubmed.publication.chemicals (biomedical)
        # 6. semanticscholar.publication.influential_citation_count (citations)
        # 7. openalex.publication.is_retracted (doc_type)
        # 8. _dq_error, _dq_warn

        system_indices = [ordered.index("entity_id"), ordered.index("content_hash")]
        id_indices = [
            ordered.index("chembl.publication.publication_id"),
            ordered.index("pubmed.publication.pmid"),
        ]
        journal_indices = [
            ordered.index("doi"),
            ordered.index("chembl.publication.title"),
            ordered.index("pubmed.publication.abstract"),
        ]
        authors_indices = [
            ordered.index("pubmed.publication.authors_with_affiliations")
        ]
        biomedical_indices = [ordered.index("pubmed.publication.chemicals")]
        citations_indices = [
            ordered.index("semanticscholar.publication.influential_citation_count")
        ]
        doc_type_indices = [ordered.index("openalex.publication.is_retracted")]
        dq_indices = [ordered.index("_dq_error"), ordered.index("_dq_warn")]

        assert max(system_indices) < min(id_indices)
        assert max(id_indices) < min(journal_indices)
        assert max(journal_indices) < min(authors_indices)
        assert max(authors_indices) < min(biomedical_indices)
        assert max(biomedical_indices) < min(citations_indices)
        assert max(citations_indices) < min(doc_type_indices)
        assert max(doc_type_indices) < min(dq_indices)
