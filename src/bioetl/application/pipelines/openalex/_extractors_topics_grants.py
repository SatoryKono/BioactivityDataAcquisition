"""Topic and grant extractors for OpenAlex records."""

from __future__ import annotations

from bioetl.application.pipelines.openalex._extractors_common import (
    _parse_grant_dict,
    _parse_topic_dict,
)
from bioetl.domain.types import JsonDict


def extract_topics(
    topics: list[JsonDict] | None,  # Any: untyped JSON fragment from OpenAlex API
    max_count: int = 10,
) -> list[JsonDict]:  # Any: untyped JSON fragment from OpenAlex API
    """Extract topics with hierarchical classification.

    Args:
        topics: List of topic dicts from the OpenAlex API response, or None.
        max_count: Maximum number of topics to include in the result.

    Returns:
        List of parsed topic dictionaries (up to max_count entries).
    """
    if not topics or not isinstance(topics, list):
        return []

    result: list[JsonDict] = []  # Any: untyped JSON fragment from OpenAlex API
    for topic in topics[:max_count]:
        if not isinstance(topic, dict):
            continue
        parsed = _parse_topic_dict(topic)
        if parsed:
            result.append(parsed)

    return result


def extract_primary_topic(
    primary_topic: (
        JsonDict | None  # Any: untyped API JSON record
    ),  # Any: untyped JSON fragment from OpenAlex API
) -> JsonDict | None:  # Any: untyped JSON fragment from OpenAlex API
    """Extract single most relevant topic for a work.

    Args:
        primary_topic: OpenAlex primary_topic dict from the API response, or None.

    Returns:
        Parsed topic dictionary or None if primary_topic is absent or invalid.
    """
    if not primary_topic or not isinstance(primary_topic, dict):
        return None
    return _parse_topic_dict(primary_topic)


def extract_grants(
    grants: list[JsonDict] | None,  # Any: untyped JSON fragment from OpenAlex API
) -> list[JsonDict]:  # Any: untyped JSON fragment from OpenAlex API
    """Extract grant/funding information from grants array.

    Args:
        grants: List of grant dicts from the OpenAlex API response, or None.

    Returns:
        List of parsed grant dictionaries.
    """
    if not grants or not isinstance(grants, list):
        return []

    result: list[JsonDict] = []  # Any: untyped JSON fragment from OpenAlex API
    for grant in grants:
        if not isinstance(grant, dict):
            continue
        parsed = _parse_grant_dict(grant)
        if parsed:
            result.append(parsed)

    return result


__all__ = ["extract_grants", "extract_primary_topic", "extract_topics"]
