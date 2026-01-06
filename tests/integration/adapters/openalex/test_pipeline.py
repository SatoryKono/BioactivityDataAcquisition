"""Integration tests for OpenAlex Publication Pipeline.

Tests transformer extractors and data transformation logic.
Full pipeline tests with VCR cassettes are in test_adapter.py.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
class TestOpenAlexPublicationTransformerIntegration:
    """Integration tests for OpenAlex transformer extractors.

    Tests field extraction and transformation logic without HTTP dependencies.
    For HTTP integration tests, see test_adapter.py which uses VCR cassettes.
    """

    @pytest.mark.asyncio
    async def test_transformer_abstract_reconstruction(self) -> None:
        """Test abstract reconstruction from inverted index."""
        from bioetl.application.pipelines.openalex.extractors import (
            reconstruct_abstract,
        )

        inverted_index = {
            "This": [0],
            "is": [1],
            "a": [2],
            "test": [3],
            "abstract": [4],
        }

        result = reconstruct_abstract(inverted_index)
        assert result == "This is a test abstract"

    @pytest.mark.asyncio
    async def test_transformer_author_extraction(self) -> None:
        """Test author extraction from authorships."""
        from bioetl.application.pipelines.openalex.extractors import extract_authors

        authorships = [
            {"author": {"display_name": "John Doe"}},
            {"author": {"display_name": "Jane Smith"}},
            {"author": {}},  # Missing display_name
        ]

        authors = extract_authors(authorships)
        assert len(authors) == 2
        assert "John Doe" in authors
        assert "Jane Smith" in authors

    @pytest.mark.asyncio
    async def test_transformer_doi_normalization(self) -> None:
        """Test DOI normalization from various URL formats."""
        from bioetl.application.pipelines.openalex.extractors import extract_doi

        # HTTPS URL
        assert (
            extract_doi("https://doi.org/10.1038/nature12373") == "10.1038/nature12373"
        )
        # HTTP URL
        assert (
            extract_doi("http://doi.org/10.1038/nature12373") == "10.1038/nature12373"
        )
        # doi: prefix
        assert extract_doi("doi:10.1038/nature12373") == "10.1038/nature12373"
        # Bare DOI
        assert extract_doi("10.1038/nature12373") == "10.1038/nature12373"
        # None
        assert extract_doi(None) is None

    @pytest.mark.asyncio
    async def test_transformer_openalex_id_extraction(self) -> None:
        """Test OpenAlex ID extraction from URL."""
        from bioetl.application.pipelines.openalex.extractors import extract_openalex_id

        # Full URL
        assert extract_openalex_id("https://openalex.org/W2148763428") == "W2148763428"
        # Bare ID
        assert extract_openalex_id("W2148763428") == "W2148763428"
        # None
        assert extract_openalex_id(None) is None

    @pytest.mark.asyncio
    async def test_transformer_concepts_extraction(self) -> None:
        """Test concepts extraction with max count."""
        from bioetl.application.pipelines.openalex.extractors import extract_concepts

        concepts = [
            {"display_name": "Biology", "score": 0.9},
            {"display_name": "Chemistry", "score": 0.8},
            {"display_name": "Physics", "score": 0.7},
            {"display_name": "Math", "score": 0.6},
        ]

        # Default max_count=10
        result = extract_concepts(concepts)
        assert len(result) == 4

        # With max_count=2
        result = extract_concepts(concepts, max_count=2)
        assert len(result) == 2
        assert "Biology" in result
        assert "Chemistry" in result

    @pytest.mark.asyncio
    async def test_transformer_journal_info_extraction(self) -> None:
        """Test journal info extraction from primary_location."""
        from bioetl.application.pipelines.openalex.extractors import (
            extract_journal_info,
        )

        primary_location = {
            "source": {
                "display_name": "Nature",
                "issn_l": "0028-0836",
                "host_organization_name": "Springer Nature",
            }
        }

        result = extract_journal_info(primary_location)
        assert result["journal_name"] == "Nature"
        assert result["issn"] == "0028-0836"
        assert result["publisher"] == "Springer Nature"

    @pytest.mark.asyncio
    async def test_transformer_open_access_extraction(self) -> None:
        """Test Open Access info extraction."""
        from bioetl.application.pipelines.openalex.extractors import (
            extract_open_access_info,
        )

        open_access = {
            "is_oa": True,
            "oa_status": "gold",
        }

        result = extract_open_access_info(open_access)
        assert result["is_oa"] is True
        assert result["oa_status"] == "gold"

        # Empty case
        result = extract_open_access_info({})
        assert result["is_oa"] is None
        assert result["oa_status"] is None
