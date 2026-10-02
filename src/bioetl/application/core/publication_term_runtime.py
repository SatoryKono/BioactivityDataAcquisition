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


def publication_pubmed_id(record: BronzeRecord) -> str | None:
    """Return a non-empty PubMed ID string from a ChEMBL publication record."""
    value = record.get("pubmed_id")
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return str(value) if value > 0 else None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _heading_as_mapping(heading: object) -> dict[str, object] | None:
    """Normalize a PubMed MeSH heading object to a string-key mapping."""
    if isinstance(heading, dict):
        return heading
    descriptor_name = getattr(heading, "descriptor_name", None)
    descriptor_ui = getattr(heading, "descriptor_ui", None)
    qualifiers = getattr(heading, "qualifiers", None)
    if descriptor_name is None and descriptor_ui is None:
        return None
    return {
        "descriptor_name": descriptor_name,
        "descriptor_ui": descriptor_ui,
        "qualifiers": qualifiers,
    }


def _qualifier_name(qualifier: object) -> str | None:
    """Extract a MeSH qualifier display name from a string or mapping."""
    if isinstance(qualifier, str):
        return _as_nonempty_str(qualifier)
    if isinstance(qualifier, dict):
        for key in ("name", "qualifier_name", "descriptor_name"):
            parsed = _as_nonempty_str(qualifier.get(key))
            if parsed is not None:
                return parsed
    name = getattr(qualifier, "name", None)
    return _as_nonempty_str(name) if isinstance(name, str) else None


def mesh_terms_from_pubmed_headings(
    mesh_headings: object,
    keywords: object = None,
) -> tuple[list[dict[str, str | None]], list[str]]:
    """Map PubMed MeSH headings/keywords onto ChEMBL ``mesh_terms`` shape.

    One heading dict carries the first qualifier so ``extract_terms_from_publication``
    emits both ``MESH_HEADING`` and ``MESH_QUALIFIER``. Extra qualifiers are
    qualifier-only dicts so the heading ``entity_id`` stays unique.
    """
    mesh_terms: list[dict[str, str | None]] = []
    if isinstance(mesh_headings, list):
        for heading in mesh_headings:
            mapping = _heading_as_mapping(heading)
            if mapping is None:
                continue
            heading_name = _as_nonempty_str(mapping.get("descriptor_name"))
            mesh_id = _as_nonempty_str(mapping.get("descriptor_ui"))
            if heading_name is None:
                continue
            qualifier_names = _qualifier_names(mapping.get("qualifiers"))
            mesh_terms.append(
                {
                    "mesh_heading": heading_name,
                    "mesh_id": mesh_id,
                    "mesh_qualifier": qualifier_names[0] if qualifier_names else None,
                }
            )
            for extra in qualifier_names[1:]:
                mesh_terms.append(
                    {
                        "mesh_heading": None,
                        "mesh_id": mesh_id,
                        "mesh_qualifier": extra,
                    }
                )
    return mesh_terms, _keyword_terms(keywords)


def _qualifier_names(qualifiers: object) -> list[str]:
    """Preserve the order of nonempty qualifier names."""
    if not isinstance(qualifiers, list):
        return []
    return [name for item in qualifiers if (name := _qualifier_name(item)) is not None]


def _keyword_terms(keywords: object) -> list[str]:
    """Keep only nonempty string keywords in source order."""
    if not isinstance(keywords, list):
        return []
    return [term for item in keywords if (term := _as_nonempty_str(item)) is not None]


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
    "mesh_terms_from_pubmed_headings",
    "publication_pubmed_id",
]
