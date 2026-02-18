"""Publication legacy→canonical field alias registry.

This module centralizes compatibility aliases used by publication pipelines.
It combines:
1. Declarative transformer renames (`FieldSpec(target=...)`)
2. YAML `field_aliases` used by schema-driven read paths

The resulting mapping is used for compatibility shims while canonical field
names remain the public API for Gold contracts.
"""

from __future__ import annotations

from collections.abc import Sequence

from bioetl.application.core.field_specs import FieldGroup

# Explicit deprecation window for legacy publication aliases.
LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE = "2026-06-30"

# Legacy aliases declared in publication schema YAML (`field_aliases`).
PUBLICATION_SCHEMA_FIELD_ALIASES: dict[str, str] = {
    "year": "publication_year",
    "first_page": "page_first",
    "last_page": "page_last",
    "doc_type": "publication_type",
    "document_chembl_id": "publication_id",
    "doi": "publication_doi",
    "pmid": "publication_pmid",
    "pmc_id": "publication_pmc_id",
}


def build_publication_legacy_to_canonical_map(
    field_groups: Sequence[FieldGroup],
    field_aliases: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build legacy→canonical mapping from FieldSpec targets + YAML aliases.

    Args:
        field_groups: Declarative groups containing `FieldSpec` definitions.
        field_aliases: Optional extra aliases from YAML `field_aliases`.

    Returns:
        Merged mapping where explicit `field_aliases` override FieldSpec-derived
        entries when keys overlap.
    """
    mapping: dict[str, str] = {}

    for group in field_groups:
        for spec in group.fields:
            if spec.target and spec.target != spec.source:
                mapping[spec.source] = spec.target

    if field_aliases:
        mapping.update(field_aliases)

    return mapping
