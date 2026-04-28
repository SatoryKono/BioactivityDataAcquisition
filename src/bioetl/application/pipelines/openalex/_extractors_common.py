"""Shared helper functions for OpenAlex field extractors."""

from __future__ import annotations

import re

from bioetl.domain.types import JsonDict

# ORCID format: NNNN-NNNN-NNNN-NNNN (last char can be X for checksum)
_ORCID_PATTERN = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")


def _extract_id_from_url(url: str | None) -> str | None:
    """Extract ID from OpenAlex URL or return raw value if already bare ID."""
    if not url or not isinstance(url, str):
        return None
    return url.rstrip("/").split("/")[-1] if "/" in url else url


def _get_nested_display_name(obj: object) -> str | None:
    """Get ``display_name`` from a nested mapping-like object."""
    if isinstance(obj, dict):
        return obj.get("display_name")
    return None


def _extract_orcid_from_url(url: str | None) -> str:
    """Extract and validate ORCID from URL or raw ORCID string."""
    if not url or not isinstance(url, str):
        return ""

    orcid = url.strip().rstrip("/")
    if "/" in orcid:
        orcid = orcid.split("/")[-1]

    if _ORCID_PATTERN.match(orcid):
        return orcid
    return ""


def _parse_topic_dict(
    topic: JsonDict,  # Any: untyped JSON fragment from OpenAlex API
) -> JsonDict | None:  # Any: untyped JSON fragment from OpenAlex API
    """Parse a single topic dict into normalized format."""
    display_name = topic.get("display_name")
    if not display_name or not isinstance(display_name, str):
        return None

    score = topic.get("score")
    score_val = float(score) if isinstance(score, (int, float)) else 0.0

    return {
        "id": _extract_id_from_url(topic.get("id")),
        "display_name": display_name.strip(),
        "score": score_val,
        "subfield": _get_nested_display_name(topic.get("subfield") or {}),
        "field": _get_nested_display_name(topic.get("field") or {}),
        "domain": _get_nested_display_name(topic.get("domain") or {}),
    }


def _parse_grant_dict(
    grant: JsonDict,  # Any: untyped JSON fragment from OpenAlex API
) -> JsonDict | None:  # Any: untyped JSON fragment from OpenAlex API
    """Parse OpenAlex legacy grants, current awards, or current funders."""
    funder_name = _resolve_funder_name(grant)
    if funder_name is None:
        return None

    award_id = grant.get("award_id") or grant.get("funder_award_id")
    award_str = str(award_id).strip() if award_id else None
    award_openalex_id = _resolve_award_openalex_id(grant)
    funder_id_str = _resolve_funder_id(grant, award_openalex_id=award_openalex_id)

    return {
        "funder": _extract_id_from_url(funder_id_str),
        "funder_display_name": funder_name,
        "award_id": award_str,
        "award_openalex_id": award_openalex_id,
        "award_display_name": grant.get("display_name") if award_openalex_id else None,
        "award_doi": grant.get("doi"),
    }


def _resolve_funder_name(grant: JsonDict) -> str | None:
    """Return the best available funder display name."""
    candidate = (
        grant.get("funder_display_name")
        or grant.get("display_name")
        or _get_nested_display_name(grant.get("funder"))
    )
    if not isinstance(candidate, str):
        return None
    stripped = candidate.strip()
    return stripped or None


def _resolve_award_openalex_id(grant: JsonDict) -> str | None:
    """Return the OpenAlex award identifier for current award/funder shapes."""
    if not (grant.get("funder_award_id") or grant.get("funder_id")):
        return None
    return _extract_id_from_url(grant.get("id"))


def _resolve_funder_id(
    grant: JsonDict,
    *,
    award_openalex_id: str | None,
) -> str | None:
    """Return the best available funder identifier as a raw OpenAlex URL/ID string."""
    funder_id = (
        grant.get("funder_id")
        or grant.get("funder")
        or (grant.get("id") if award_openalex_id is None else None)
    )
    if isinstance(funder_id, dict):
        funder_id = funder_id.get("id")
    return funder_id if isinstance(funder_id, str) else None


__all__ = [
    "_extract_id_from_url",
    "_extract_orcid_from_url",
    "_get_nested_display_name",
    "_parse_grant_dict",
    "_parse_topic_dict",
]
