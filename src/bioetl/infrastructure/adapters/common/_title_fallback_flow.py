"""Private async flow helpers for BaseTitleFallbackHandler."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import cast

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import JsonDict


def get_fallback_title(
    doi: str, normalized_doi: str | None, fallback_mapping: dict[str, str]
) -> str | None:
    """Return fallback title from the original or normalized identifier."""
    if normalized_doi:
        return fallback_mapping.get(doi) or fallback_mapping.get(normalized_doi)
    return fallback_mapping.get(doi)


def truncate_title(title: str, max_len: int = 50) -> str:
    """Truncate a title for logging output."""
    return title[:max_len] + "..." if len(title) > max_len else title


@dataclass(frozen=True, slots=True)
class MissingDoiTitleFallbackRequest:
    """Typed input for unresolved DOI title-fallback iteration."""

    dois: list[str]
    found_dois: set[str]
    fallback_mapping: dict[str, str]
    normalize_fn: Callable[[str], str | None]
    limit: int | None
    fetched: int
    get_fallback_title: Callable[[str, str | None, dict[str, str]], str | None]
    truncate_title: Callable[[str, int], str]
    search_by_title: Callable[[str], Awaitable[JsonDict | None]]
    get_result_identifier: Callable[[JsonDict], tuple[str, str]]
    process_found_result: Callable[[JsonDict, str], JsonDict]
    logger: LoggerPort
    event_no_fallback_title: str
    event_fallback_attempt: str
    event_fallback_success: str
    event_fallback_not_found: str


def _coerce_missing_doi_title_fallback_request(
    request: MissingDoiTitleFallbackRequest | None = None,
    /,
    **kwargs: object,
) -> MissingDoiTitleFallbackRequest:
    """Normalize compact and legacy missing-DOI fallback inputs."""
    if request is not None:
        if kwargs:
            unexpected = ", ".join(sorted(kwargs))
            raise TypeError(
                "iter_missing_doi_fallback_records received unexpected keyword "
                f"arguments with request object: {unexpected}"
            )
        return request

    expected_keys = {
        "dois",
        "found_dois",
        "fallback_mapping",
        "normalize_fn",
        "limit",
        "fetched",
        "get_fallback_title",
        "truncate_title",
        "search_by_title",
        "get_result_identifier",
        "process_found_result",
        "logger",
        "event_no_fallback_title",
        "event_fallback_attempt",
        "event_fallback_success",
        "event_fallback_not_found",
    }
    unexpected_keys = sorted(kwargs.keys() - expected_keys)
    if unexpected_keys:
        unexpected_args = ", ".join(unexpected_keys)
        raise TypeError(
            "iter_missing_doi_fallback_records received unexpected keyword "
            f"arguments: {unexpected_args}"
        )

    return MissingDoiTitleFallbackRequest(
        dois=cast(list[str], kwargs.pop("dois")),
        found_dois=cast(set[str], kwargs.pop("found_dois")),
        fallback_mapping=cast(dict[str, str], kwargs.pop("fallback_mapping")),
        normalize_fn=cast(Callable[[str], str | None], kwargs.pop("normalize_fn")),
        limit=cast(int | None, kwargs.pop("limit")),
        fetched=cast(int, kwargs.pop("fetched")),
        get_fallback_title=cast(
            Callable[[str, str | None, dict[str, str]], str | None],
            kwargs.pop("get_fallback_title"),
        ),
        truncate_title=cast(Callable[[str, int], str], kwargs.pop("truncate_title")),
        search_by_title=cast(
            Callable[[str], Awaitable[JsonDict | None]],
            kwargs.pop("search_by_title"),
        ),
        get_result_identifier=cast(
            Callable[[JsonDict], tuple[str, str]],
            kwargs.pop("get_result_identifier"),
        ),
        process_found_result=cast(
            Callable[[JsonDict, str], JsonDict],
            kwargs.pop("process_found_result"),
        ),
        logger=cast(LoggerPort, kwargs.pop("logger")),
        event_no_fallback_title=cast(str, kwargs.pop("event_no_fallback_title")),
        event_fallback_attempt=cast(str, kwargs.pop("event_fallback_attempt")),
        event_fallback_success=cast(str, kwargs.pop("event_fallback_success")),
        event_fallback_not_found=cast(str, kwargs.pop("event_fallback_not_found")),
    )


async def iter_missing_doi_fallback_records(
    request: MissingDoiTitleFallbackRequest | None = None,
    /,
    **kwargs: object,
) -> AsyncIterator[JsonDict]:
    """Yield title-fallback records for unresolved primary IDs."""
    resolved = _coerce_missing_doi_title_fallback_request(request, **kwargs)

    fetched = resolved.fetched
    for doi in resolved.dois:
        # Distinguish limit=None (unlimited) from limit=0 (emit nothing).
        if resolved.limit is not None and fetched >= resolved.limit:
            return

        normalized_doi = (resolved.normalize_fn(doi) or "").lower()
        if normalized_doi in resolved.found_dois:
            continue

        title = resolved.get_fallback_title(
            doi,
            normalized_doi,
            resolved.fallback_mapping,
        )
        if not title:
            resolved.logger.debug(resolved.event_no_fallback_title, doi=doi)
            continue

        resolved.logger.info(
            resolved.event_fallback_attempt,
            doi=doi,
            title=resolved.truncate_title(title, 50),
        )

        result = await resolved.search_by_title(title)
        if result:
            id_field, id_value = resolved.get_result_identifier(result)
            resolved.logger.info(
                resolved.event_fallback_success,
                original_doi=doi,
                title=title[:50],
                **{id_field: id_value},
            )
            yield resolved.process_found_result(result, doi)
            fetched += 1
        else:
            resolved.logger.warning(
                resolved.event_fallback_not_found,
                doi=doi,
                title=title[:50],
            )


async def iter_title_only_fallback_records(
    *,
    entries: list[str],
    fallback_mapping: dict[str, str],
    limit: int | None,
    fetched: int,
    truncate_title: Callable[[str, int], str],
    search_by_title: Callable[[str], Awaitable[JsonDict | None]],
    get_result_identifier: Callable[[JsonDict], tuple[str, str]],
    process_title_only_result: Callable[[JsonDict], JsonDict],
    logger: LoggerPort,
    event_title_only_attempt: str,
    event_title_only_success: str,
    event_title_only_not_found: str,
) -> AsyncIterator[JsonDict]:
    """Yield title-only fallback records for marker or empty-title entries."""
    for entry in entries:
        # Distinguish limit=None (unlimited) from limit=0 (emit nothing).
        if limit is not None and fetched >= limit:
            return

        title = fallback_mapping.get(entry, fallback_mapping.get(""))
        if not title:
            continue

        logger.info(
            event_title_only_attempt,
            title=truncate_title(title, 50),
            marker=entry if entry.startswith("__title_only_") else None,
        )

        result = await search_by_title(title)
        if result:
            id_field, id_value = get_result_identifier(result)
            logger.info(
                event_title_only_success,
                title=title[:50],
                **{id_field: id_value},
            )
            yield process_title_only_result(result)
            fetched += 1
        else:
            logger.debug(
                event_title_only_not_found,
                title=title[:50],
            )
