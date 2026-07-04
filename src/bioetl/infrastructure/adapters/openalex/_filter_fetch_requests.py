"""Internal request-shape helpers for OpenAlex filter fetch flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class _OpenAlexRequestHost(Protocol):
    """Minimal host contract required by OpenAlex request builders."""

    @staticmethod
    def _is_supported_entity_type(entity_type: str) -> bool: ...

    def _validate_entity_type(self, entity_type: str) -> None: ...


@dataclass(frozen=True, slots=True)
class _FilteredFetchRequest:
    """Normalized request for one filtered OpenAlex fetch path."""

    entity_type: str
    filter_ids: list[str]
    filter_field: str
    limit: int | None = None


@dataclass(frozen=True, slots=True)
class _FallbackFetchRequest:
    """Normalized request for DOI-first fetch with title fallback."""

    entity_type: str
    filter_ids: list[str]
    filter_field: str
    fallback_mapping: dict[str, str]
    limit: int | None = None


@dataclass(frozen=True, slots=True)
class _FetchRequest:
    """Normalized request for the public OpenAlex fetch entrypoint."""

    entity_type: str
    limit: int | None = None
    query: str | None = None
    filter_ids: list[str] | None = None
    filter_field: str | None = None


def create_filtered_fetch_request(
    host: _OpenAlexRequestHost,
    *,
    entity_type: str,
    filter_ids: list[str],
    filter_field: str,
    limit: int | None,
) -> _FilteredFetchRequest:
    """Normalize and validate filtered fetch inputs."""
    host._validate_entity_type(entity_type)
    return _FilteredFetchRequest(
        entity_type=entity_type,
        filter_ids=filter_ids,
        filter_field=filter_field,
        limit=limit,
    )


def create_fallback_fetch_request(
    host: _OpenAlexRequestHost,
    *,
    entity_type: str,
    filter_ids: list[str],
    filter_field: str,
    fallback_mapping: dict[str, str],
    limit: int | None,
) -> _FallbackFetchRequest:
    """Normalize and validate fallback fetch inputs."""
    if not host._is_supported_entity_type(entity_type):
        raise ValueError(
            f"OpenAlexAdapter supports 'work'/'publication', got: {entity_type}"
        )
    return _FallbackFetchRequest(
        entity_type=entity_type,
        filter_ids=filter_ids,
        filter_field=filter_field,
        fallback_mapping=fallback_mapping,
        limit=limit,
    )


def create_fetch_request(
    *,
    entity_type: str,
    limit: int | None,
    query: str | None,
    filter_ids: list[str] | None,
    filter_field: str | None,
) -> _FetchRequest:
    """Normalize public fetch inputs before dispatch."""
    return _FetchRequest(
        entity_type=entity_type,
        limit=limit,
        query=query,
        filter_ids=filter_ids,
        filter_field=filter_field,
    )
