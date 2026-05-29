"""Auto-generated registry from configs/entities schema sections.

DO NOT EDIT MANUALLY. Run: python -m scripts.schema generate-artifacts
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CanonicalSchemaRegistryEntry:
    """Entry in the canonical schema registry."""

    provider: str
    entity: str
    yaml_path: str
    column_groups: tuple[str, ...]


_RAW_CANONICAL_SCHEMA_REGISTRY: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("chembl", "activity", "chembl/activity.yaml", ("system", "business", "dq")),
    ("chembl", "assay", "chembl/assay.yaml", ("system", "business", "dq")),
    (
        "chembl",
        "assay_parameters",
        "chembl/assay_parameters.yaml",
        ("system", "business", "dq"),
    ),
    ("chembl", "cell_line", "chembl/cell_line.yaml", ("system", "business", "dq")),
    (
        "chembl",
        "compound_record",
        "chembl/compound_record.yaml",
        ("system", "business", "dq"),
    ),
    ("chembl", "molecule", "chembl/molecule.yaml", ("system", "business", "dq")),
    (
        "chembl",
        "protein_class",
        "chembl/protein_class.yaml",
        ("system", "business", "dq"),
    ),
    (
        "chembl",
        "publication",
        "chembl/publication.yaml",
        (
            "system",
            "identifiers",
            "title",
            "abstract",
            "authors",
            "journal",
            "year",
            "pagination",
            "doc_type",
            "citations",
            "provider_ids",
            "dq",
        ),
    ),
    (
        "chembl",
        "publication_similarity",
        "chembl/publication_similarity.yaml",
        ("system", "business", "dq"),
    ),
    (
        "chembl",
        "publication_term",
        "chembl/publication_term.yaml",
        ("system", "business", "dq"),
    ),
    (
        "chembl",
        "subcellular_fraction",
        "chembl/subcellular_fraction.yaml",
        ("system", "business", "dq"),
    ),
    ("chembl", "target", "chembl/target.yaml", ("system", "business", "dq")),
    (
        "chembl",
        "target_component",
        "chembl/target_component.yaml",
        ("system", "business", "dq"),
    ),
    ("chembl", "tissue", "chembl/tissue.yaml", ("system", "identifiers", "business")),
    ("composite", "activity", "composite/activity.yaml", ()),
    ("composite", "assay", "composite/assay.yaml", ()),
    ("composite", "molecule", "composite/molecule.yaml", ()),
    ("composite", "publication", "composite/publication.yaml", ()),
    ("composite", "target", "composite/target.yaml", ()),
    (
        "crossref",
        "publication",
        "crossref/publication.yaml",
        (
            "system",
            "identifiers",
            "title",
            "authors",
            "journal",
            "issn",
            "year",
            "dates",
            "pagination",
            "citations",
            "subjects",
            "language",
            "publisher",
            "doc_type",
            "content_domain",
            "license",
            "dq",
        ),
    ),
    (
        "openalex",
        "publication",
        "openalex/publication.yaml",
        (
            "system",
            "identifiers",
            "title",
            "abstract",
            "authors",
            "affiliations",
            "institutions",
            "journal",
            "year",
            "dates",
            "pagination",
            "citations",
            "open_access",
            "subjects",
            "publisher",
            "funding",
            "doc_type",
            "quality",
            "language",
            "dq",
        ),
    ),
    ("pubchem", "compound", "pubchem/compound.yaml", ("system", "business", "dq")),
    (
        "pubmed",
        "publication",
        "pubmed/publication.yaml",
        (
            "system",
            "identifiers",
            "title",
            "abstract",
            "authors",
            "affiliations",
            "journal",
            "year",
            "dates",
            "pagination",
            "citations",
            "subjects",
            "funding",
            "chemicals",
            "doc_type",
            "language",
            "misc",
            "dq",
        ),
    ),
    (
        "semanticscholar",
        "publication",
        "semanticscholar/publication.yaml",
        (
            "system",
            "identifiers",
            "title",
            "abstract",
            "authors",
            "affiliations",
            "journal",
            "year",
            "dates",
            "pagination",
            "citations",
            "subjects",
            "doc_type",
            "open_access",
            "dq",
        ),
    ),
    ("uniprot", "idmapping", "uniprot/idmapping.yaml", ("system", "business", "dq")),
    ("uniprot", "protein", "uniprot/protein.yaml", ("system", "business", "dq")),
)

CANONICAL_SCHEMA_REGISTRY: tuple[CanonicalSchemaRegistryEntry, ...] = tuple(
    CanonicalSchemaRegistryEntry(
        provider=provider,
        entity=entity,
        yaml_path=yaml_path,
        column_groups=column_groups,
    )
    for provider, entity, yaml_path, column_groups in _RAW_CANONICAL_SCHEMA_REGISTRY
)

__all__ = ["CANONICAL_SCHEMA_REGISTRY", "CanonicalSchemaRegistryEntry"]
