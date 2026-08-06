"""Pure helper functions for publication-term extraction."""

from __future__ import annotations

from bioetl.application.core.entity_id import compute_publication_term_entity_id
from bioetl.domain.types import BronzeRecord


def _as_nonempty_str(value: object) -> str | None:
    """Return stripped non-empty string content, else None."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def extract_terms_from_publication(
    record: BronzeRecord, publication_id: str
) -> list[BronzeRecord]:
    """Extract and flatten all terms from a publication record.

    MeSH branch validates ``mesh_heading``, ``mesh_qualifier``, and ``mesh_id``
    as non-whitespace strings before record creation; non-string / blank values
    are skipped rather than coerced.
    """
    terms: list[BronzeRecord] = []
    raw_mesh_terms = record.get("mesh_terms")
    mesh_terms: list[object] = (
        raw_mesh_terms if isinstance(raw_mesh_terms, list) else []
    )
    for mesh in mesh_terms:
        if not isinstance(mesh, dict):
            continue
        mesh_heading = _as_nonempty_str(mesh.get("mesh_heading"))
        mesh_qualifier = _as_nonempty_str(mesh.get("mesh_qualifier"))
        mesh_id = _as_nonempty_str(mesh.get("mesh_id"))
        if mesh_heading is not None:
            terms.append(
                create_term_record(
                    publication_id=publication_id,
                    term=mesh_heading,
                    term_type="MESH_HEADING",
                    mesh_id=mesh_id,
                    qualifier=mesh_qualifier,
                )
            )
        if mesh_qualifier is not None:
            terms.append(
                create_term_record(
                    publication_id=publication_id,
                    term=mesh_qualifier,
                    term_type="MESH_QUALIFIER",
                    mesh_id=mesh_id,
                    qualifier=None,
                )
            )
    raw_keywords = record.get("keywords")
    keywords: list[object] = raw_keywords if isinstance(raw_keywords, list) else []
    for keyword in keywords:
        if isinstance(keyword, str):
            stripped = keyword.strip()
            if stripped:
                terms.append(
                    create_term_record(
                        publication_id=publication_id,
                        term=stripped,
                        term_type="KEYWORD",
                        mesh_id=None,
                        qualifier=None,
                    )
                )
    return terms


def create_term_record(
    *,
    publication_id: str,
    term: str,
    term_type: str,
    mesh_id: str | None,
    qualifier: str | None,
) -> BronzeRecord:
    """Create a single publication-term record."""
    normalized_term = term.strip() if term else term
    normalized_mesh_id = _as_nonempty_str(mesh_id) if mesh_id is not None else None
    normalized_qualifier = (
        _as_nonempty_str(qualifier) if qualifier is not None else None
    )
    entity_id = compute_term_entity_id(
        publication_id=publication_id,
        term_type=term_type,
        term=normalized_term or "",
    )
    return {
        "entity_id": entity_id,
        "publication_id": publication_id,
        "term": normalized_term,
        "term_type": term_type,
        "mesh_id": normalized_mesh_id,
        "qualifier": normalized_qualifier,
    }


def compute_term_entity_id(
    *,
    publication_id: str,
    term_type: str,
    term: str,
) -> str:
    """Compute deterministic term entity ID."""
    return compute_publication_term_entity_id(publication_id, term_type, term)


__all__ = [
    "compute_term_entity_id",
    "create_term_record",
    "extract_terms_from_publication",
]
