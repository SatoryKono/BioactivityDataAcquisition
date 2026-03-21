"""Private async flow helpers for BaseTitleFallbackHandler."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import JsonDict


async def iter_missing_doi_fallback_records(
    *,
    dois: list[str],
    found_dois: set[str],
    fallback_mapping: dict[str, str],
    normalize_fn: Callable[[str], str | None],
    limit: int | None,
    fetched: int,
    get_fallback_title: Callable[[str, str | None, dict[str, str]], str | None],
    truncate_title: Callable[[str, int], str],
    search_by_title: Callable[[str], Awaitable[JsonDict | None]],
    get_result_identifier: Callable[[JsonDict], tuple[str, str]],
    process_found_result: Callable[[JsonDict, str], JsonDict],
    logger: LoggerPort,
    event_no_fallback_title: str,
    event_fallback_attempt: str,
    event_fallback_success: str,
    event_fallback_not_found: str,
) -> AsyncIterator[JsonDict]:
    """Yield title-fallback records for unresolved primary IDs."""
    for doi in dois:
        if limit and fetched >= limit:
            return

        normalized_doi = (normalize_fn(doi) or "").lower()
        if normalized_doi in found_dois:
            continue

        title = get_fallback_title(doi, normalized_doi, fallback_mapping)
        if not title:
            logger.debug(event_no_fallback_title, doi=doi)
            continue

        logger.info(
            event_fallback_attempt,
            doi=doi,
            title=truncate_title(title, 50),
        )

        result = await search_by_title(title)
        if result:
            id_field, id_value = get_result_identifier(result)
            logger.info(
                event_fallback_success,
                original_doi=doi,
                title=title[:50],
                **{id_field: id_value},
            )
            yield process_found_result(result, doi)
            fetched += 1
        else:
            logger.warning(
                event_fallback_not_found,
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
        if limit and fetched >= limit:
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
