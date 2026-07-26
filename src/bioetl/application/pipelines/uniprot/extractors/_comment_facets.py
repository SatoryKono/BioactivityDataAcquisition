"""Focused extraction facets for UniProt comment payloads."""

from __future__ import annotations

from bioetl.application.pipelines.uniprot.extractors._comment_facets_all import (
    extract_all_comments as extract_all_comments,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_all import (
    extract_all_comments_raw as extract_all_comments_raw,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors import (
    __all__ as _COMMENT_EXTRACTOR_EXPORTS,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors import (
    count_isoforms as count_isoforms,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors import (
    extract_alternative_products as extract_alternative_products,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors import (
    extract_biophysicochemical_properties as extract_biophysicochemical_properties,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors import (
    extract_by_type as extract_by_type,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors import (
    extract_catalytic_activity as extract_catalytic_activity,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors import (
    extract_cofactors as extract_cofactors,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors import (
    extract_isoform_details as extract_isoform_details,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors import (
    extract_reaction_ec_numbers as extract_reaction_ec_numbers,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors import (
    extract_reactions as extract_reactions,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors import (
    extract_subcellular_locations as extract_subcellular_locations,
)
from bioetl.application.pipelines.uniprot.extractors._comment_facets_extractors import (
    extract_text_values as extract_text_values,
)

__all__ = [
    "extract_all_comments",
    "extract_all_comments_raw",
    *_COMMENT_EXTRACTOR_EXPORTS,
]
