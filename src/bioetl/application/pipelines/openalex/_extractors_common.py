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
    funder = grant.get("funder")
    funder_name = (
        grant.get("funder_display_name")
        or grant.get("display_name")
        or _get_nested_display_name(funder)
    )
    if not funder_name or not isinstance(funder_name, str):
        return None

    award_id = grant.get("award_id") or grant.get("funder_award_id")
    award_str = str(award_id).strip() if award_id else None
    award_openalex_id = (
        _extract_id_from_url(grant.get("id"))
        if grant.get("funder_award_id") or grant.get("funder_id")
        else None
    )
    funder_id = (
        grant.get("funder_id")
        or grant.get("funder")
        or (grant.get("id") if not award_openalex_id else None)
    )

    return {
        "funder": _extract_id_from_url(funder_id),
        "funder_display_name": funder_name.strip(),
        "award_id": award_str,
        "award_openalex_id": award_openalex_id,
        "award_display_name": grant.get("display_name") if award_openalex_id else None,
        "award_doi": grant.get("doi"),
    }


__all__ = [
    "_extract_id_from_url",
    "_extract_orcid_from_url",
    "_get_nested_display_name",
    "_parse_grant_dict",
    "_parse_topic_dict",
]
