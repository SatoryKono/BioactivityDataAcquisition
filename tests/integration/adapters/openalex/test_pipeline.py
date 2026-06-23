"""Integration tests for OpenAlex Publication Pipeline.

Tests transformer extractors and data transformation logic.
Full pipeline tests with VCR cassettes are in test_adapter.py.
"""

from __future__ import annotations

import asyncio
import pytest


def _legacy_http_url(path: str) -> str:
    return "http" + "://" + path


@pytest.mark.integration
class TestOpenAlexPublicationTransformerIntegration:
    """Integration tests for OpenAlex transformer extractors.

    Tests field extraction and transformation logic without HTTP dependencies.
    For HTTP integration tests, see test_adapter.py which uses VCR cassettes.
    """

    @pytest.mark.asyncio
    async def test_transformer_abstract_reconstruction(self) -> None:
        """Test abstract reconstruction from inverted index."""
        await asyncio.sleep(0)
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
        await asyncio.sleep(0)
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
        await asyncio.sleep(0)
        from bioetl.application.pipelines.openalex.extractors import extract_doi

        # HTTPS URL
        assert (
            extract_doi("https://doi.org/10.1038/nature12373") == "10.1038/nature12373"
        )
        # HTTP URL
        assert (
            extract_doi(_legacy_http_url("doi.org/10.1038/nature12373"))
            == "10.1038/nature12373"
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
        await asyncio.sleep(0)
        from bioetl.application.pipelines.openalex.extractors import extract_openalex_id

        # Full URL
        assert extract_openalex_id("https://openalex.org/W2148763428") == "W2148763428"
        # Bare ID
        assert extract_openalex_id("W2148763428") == "W2148763428"
        # None
        assert extract_openalex_id(None) is None

    @pytest.mark.asyncio
    async def test_transformer_journal_info_extraction(self) -> None:
        """Test journal info extraction from primary_location."""
        await asyncio.sleep(0)
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
        assert result["journal"] == "Nature"
        assert result["issn"] == "0028-0836"
        assert result["publisher"] == "Springer Nature"

    @pytest.mark.asyncio
    async def test_transformer_open_access_extraction(self) -> None:
        """Test Open Access info extraction."""
        await asyncio.sleep(0)
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

    @pytest.mark.asyncio
    async def test_transformer_author_orcids_extraction(self) -> None:
        """Test ORCID extraction from authorships."""
        await asyncio.sleep(0)
        from bioetl.application.pipelines.openalex.extractors import (
            extract_author_orcids,
        )

        authorships = [
            {"author": {"orcid": "https://orcid.org/0000-0001-2345-6789"}},
            {"author": {"orcid": None}},
            {"author": {"orcid": "https://orcid.org/0000-0002-3456-789X"}},
        ]

        result = extract_author_orcids(authorships)
        assert len(result) == 3
        assert result == ["0000-0001-2345-6789", "", "0000-0002-3456-789X"]

    @pytest.mark.asyncio
    async def test_transformer_author_openalex_ids_extraction(self) -> None:
        """Test OpenAlex author ID extraction from authorships."""
        await asyncio.sleep(0)
        from bioetl.application.pipelines.openalex.extractors import extract_author_ids

        authorships = [
            {"author": {"id": "https://openalex.org/A1234567890"}},
            {"author": {"id": None}},
            {"author": {"id": "https://openalex.org/A9876543210"}},
        ]

        result = extract_author_ids(authorships)
        assert len(result) == 3
        assert result == ["A1234567890", "", "A9876543210"]

    @pytest.mark.asyncio
    async def test_transformer_institution_ids_extraction(self) -> None:
        """Test institution ID extraction from authorships."""
        await asyncio.sleep(0)
        from bioetl.application.pipelines.openalex.extractors import (
            extract_institution_ids,
        )

        authorships = [
            {
                "institutions": [
                    {"id": "https://openalex.org/I1234567890"},
                    {"id": "https://openalex.org/I1111111111"},
                ]
            },
            {"institutions": [{"id": "https://openalex.org/I1234567890"}]},  # Duplicate
        ]

        result = extract_institution_ids(authorships)
        # Should be unique and sorted
        assert result == ["I1111111111", "I1234567890"]

    @pytest.mark.asyncio
    async def test_transformer_institution_country_codes_extraction(self) -> None:
        """Test institution country code extraction from authorships."""
        await asyncio.sleep(0)
        from bioetl.application.pipelines.openalex.extractors import (
            extract_institution_country_codes,
        )

        authorships = [
            {"institutions": [{"country_code": "US"}, {"country_code": "GB"}]},
            {"institutions": [{"country_code": "US"}]},  # Duplicate
            {"institutions": [{"country_code": "de"}]},  # Lowercase
        ]

        result = extract_institution_country_codes(authorships)
        # Should be unique, sorted, and uppercased
        assert result == ["DE", "GB", "US"]
