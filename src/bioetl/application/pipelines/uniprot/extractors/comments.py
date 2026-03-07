"""Comment data extraction for UniProt records."""

from __future__ import annotations

__all__ = ["CommentExtractor", "_extract_texts_from_dict", "_is_comment_of_type"]

from bioetl.application.pipelines.uniprot.extractors._comment_facets import (
    count_isoforms as _count_isoforms,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets import (
    extract_all_comments as _extract_all_comments,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets import (
    extract_all_comments_raw as _extract_all_comments_raw,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets import (
    extract_alternative_products as _extract_alternative_products,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets import (
    extract_biophysicochemical_properties as _extract_biophysicochemical_properties,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets import (
    extract_by_type as _extract_by_type,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets import (
    extract_catalytic_activity as _extract_catalytic_activity,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets import (
    extract_cofactors as _extract_cofactors,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets import (
    extract_isoform_details as _extract_isoform_details,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets import (
    extract_reaction_ec_numbers as _extract_reaction_ec_numbers,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets import (
    extract_reactions as _extract_reactions,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets import (
    extract_subcellular_locations as _extract_subcellular_locations,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets import (
    extract_text_values as _extract_text_values,
)
from bioetl.application.pipelines.uniprot.extractors._comment_helpers import (
    _extract_texts_from_dict,
    _is_comment_of_type,
)
from bioetl.domain.types import JsonDict


class CommentExtractor:
    """Facade for UniProt comment extraction.

    Public API is kept stable while extraction logic lives in focused facet
    functions under ``_comment_facets``.
    """

    @staticmethod
    def extract_text_values(
        comments: list[JsonDict],
        comment_type: str,
    ) -> list[str]:
        """Extract text values from comments by type."""
        return _extract_text_values(comments, comment_type)

    @classmethod
    def extract_by_type(
        cls,
        comments: list[JsonDict] | None,
        comment_type: str,
    ) -> str | None:
        """Extract comments of a specific type as JSON string."""
        return _extract_by_type(comments, comment_type)

    @staticmethod
    def extract_catalytic_activity(comments: list[JsonDict] | None) -> str | None:
        """Extract catalytic activity information."""
        return _extract_catalytic_activity(comments)

    @staticmethod
    def extract_subcellular_locations(comments: list[JsonDict] | None) -> str | None:
        """Extract subcellular location information."""
        return _extract_subcellular_locations(comments)

    @staticmethod
    def extract_alternative_products(comments: list[JsonDict] | None) -> str | None:
        """Extract alternative products (isoforms) information."""
        return _extract_alternative_products(comments)

    @staticmethod
    def count_isoforms(comments: list[JsonDict] | None) -> int | None:
        """Count the number of isoforms."""
        return _count_isoforms(comments)

    @staticmethod
    def extract_cofactors(comments: list[JsonDict] | None) -> str | None:
        """Extract cofactor information from COFACTOR comments."""
        return _extract_cofactors(comments)

    @staticmethod
    def extract_biophysicochemical_properties(
        comments: list[JsonDict] | None,
    ) -> str | None:
        """Extract biophysicochemical properties from comments."""
        return _extract_biophysicochemical_properties(comments)

    @classmethod
    def extract_induction(cls, comments: list[JsonDict] | None) -> str | None:
        """Extract induction information from INDUCTION comments."""
        return _extract_by_type(comments, "INDUCTION")

    @staticmethod
    def extract_isoform_details(
        comments: list[JsonDict] | None,
    ) -> dict[str, str | None]:
        """Extract detailed isoform information from ALTERNATIVE PRODUCTS."""
        return _extract_isoform_details(comments)

    @staticmethod
    def extract_reactions(comments: list[JsonDict] | None) -> str | None:
        """Extract reaction names from CATALYTIC ACTIVITY comments."""
        return _extract_reactions(comments)

    @staticmethod
    def extract_reaction_ec_numbers(comments: list[JsonDict] | None) -> str | None:
        """Extract EC numbers from CATALYTIC ACTIVITY comments."""
        return _extract_reaction_ec_numbers(comments)

    @staticmethod
    def extract_all_comments_raw(comments: list[JsonDict] | None) -> dict[str, object]:
        """Extract all comment-related fields as raw Python values."""
        return _extract_all_comments_raw(comments)

    @staticmethod
    def extract_all_comments(
        comments: list[JsonDict] | None,
    ) -> dict[str, str | int | None]:
        """Extract all comment-related fields in transformer output format."""
        return _extract_all_comments(comments)
