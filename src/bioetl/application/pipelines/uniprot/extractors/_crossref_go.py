"""GO-specific extraction helpers for UniProt cross-references."""

from __future__ import annotations

from bioetl.application.pipelines.uniprot.extractors._crossref_common import (
    filter_xrefs_by_database,
    parse_properties,
    serialize_json_or_none,
)
from bioetl.domain.types import JsonDict

GO_ASPECTS = frozenset(("F", "P", "C"))


def parse_go_term_value(go_term_value: object) -> tuple[str | None, str | None]:
    """Parse GO term value (for example, ``F:ATP binding``).

    Args:
        go_term_value: Raw GoTerm property value from a UniProt GO cross-reference.
            Expected format is ``'<aspect>:<term>'`` (e.g. ``'F:ATP binding'``).

    Returns:
        Tuple of (aspect, term) strings, or (None, None) if the value is invalid
        or the aspect character is not one of the valid GO aspects (F, P, C).
    """
    if not isinstance(go_term_value, str) or ":" not in go_term_value:
        return None, None

    parts = go_term_value.split(":", 1)
    if len(parts) != 2:
        return None, None

    aspect_candidate = parts[0].strip()
    aspect = aspect_candidate if aspect_candidate in GO_ASPECTS else None
    term_candidate = parts[1].strip()
    term = term_candidate if term_candidate else None
    return aspect, term


def extract_go_terms(xrefs: list[JsonDict] | None) -> str | None:
    """Extract GO terms with aspect and evidence metadata.

    Args:
        xrefs: List of UniProt cross-reference dicts from the API response, or None.

    Returns:
        JSON-serialized list of GO term dicts (id, term, aspect, evidence),
        or None if no GO cross-references are present.
    """
    go_terms: list[JsonDict] = []  # Any: JSON values are heterogeneous
    for xref in filter_xrefs_by_database(xrefs, "GO"):
        go_id = xref.get("id")
        if not go_id:
            continue

        props = parse_properties(xref.get("properties", []))
        aspect, term = parse_go_term_value(props.get("GoTerm", ""))
        go_terms.append(
            {
                "id": go_id,
                "term": term,
                "aspect": aspect,
                "evidence": props.get("GoEvidenceType"),
            }
        )

    return serialize_json_or_none(go_terms)


def extract_go_by_aspect(xrefs: list[JsonDict] | None, aspect: str) -> str | None:
    """Extract GO terms filtered by aspect (F/P/C).

    Args:
        xrefs: List of UniProt cross-reference dicts from the API response, or None.
        aspect: GO aspect character to filter on. Must be one of 'F' (molecular
            function), 'P' (biological process), or 'C' (cellular component).

    Returns:
        JSON-serialized list of GO term dicts (id, term, evidence) for the given
        aspect, or None if no matching terms are found or aspect is invalid.
    """
    if aspect not in GO_ASPECTS:
        return None

    go_terms: list[JsonDict] = []  # Any: JSON values are heterogeneous
    for xref in filter_xrefs_by_database(xrefs, "GO"):
        go_id = xref.get("id")
        if not go_id:
            continue

        props = parse_properties(xref.get("properties", []))
        parsed_aspect, term = parse_go_term_value(props.get("GoTerm", ""))
        if parsed_aspect != aspect:
            continue

        go_terms.append(
            {
                "id": go_id,
                "term": term,
                "evidence": props.get("GoEvidenceType"),
            }
        )

    return serialize_json_or_none(go_terms)
