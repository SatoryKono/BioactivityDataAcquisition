# mypy: disable-error-code="misc"
"""Internal PubMed ESearch response models."""

from __future__ import annotations

__all__ = ["PubMedSearchResponse", "PubMedSearchResult"]

from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, ConfigDict, Field

from bioetl.infrastructure.adapters.http.pagination import raise_pagination_truncated

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class PubMedSearchResult(BaseModel):
    """Result from PubMed ESearch endpoint."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    count: int | None = Field(default=None, description="Total count of results")
    ret_max: int | None = Field(
        default=None, alias="retmax", description="Maximum records to return"
    )
    ret_start: int | None = Field(
        default=None, alias="retstart", description="Starting index"
    )
    id_list: list[str] = Field(
        default_factory=list, alias="idlist", description="List of PMIDs"
    )
    web_env: str | None = Field(
        default=None, alias="webenv", description="Web environment ID"
    )
    query_key: str | None = Field(
        default=None, alias="querykey", description="Query key"
    )


class PubMedSearchResponse(BaseModel):
    """Complete PubMed ESearch API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    esearchresult: PubMedSearchResult | None = Field(
        default=None, description="Search result data"
    )


MAX_ESEARCH_PAGES = 10_000


class SearchLogHost(Protocol):
    """Host that can log a truncated ESearch scan."""

    _logger: LoggerPort


def esearch_params(
    email: str,
    api_key: str | None,
    search_term: str,
    *,
    retstart: int,
    retmax: int,
) -> dict[str, str]:
    """Build an ESearch query. Omit ``retstart`` on the first page."""
    params = {
        "db": "pubmed",
        "term": search_term,
        "retmax": str(retmax),
    }
    if retstart > 0:
        params["retstart"] = str(retstart)
    params["usehistory"] = "y"
    params["retmode"] = "json"
    params["email"] = email
    if api_key and "your_" not in api_key:
        params["api_key"] = api_key
    return params


def esearch_page_completes(
    collected: list[str],
    page_ids: list[str],
    max_count: int,
    reported_count: int | None,
) -> bool:
    """Stop when ``count`` is covered, or when the server sent no ``count``."""
    target = esearch_target(max_count, reported_count)
    if target is None:
        return True
    return len(collected) + len(page_ids) >= target


def append_completed_page(
    collected: list[str],
    page_ids: list[str],
    max_count: int,
    reported_count: int | None,
) -> None:
    """Append only the ids still required by ``count`` or ``max_count``."""
    target = esearch_target(max_count, reported_count)
    if target is None:
        collected.extend(page_ids)
        return
    room = target - len(collected)
    if room > 0:
        collected.extend(page_ids[:room])


def esearch_target(max_count: int, reported_count: int | None) -> int | None:
    """Return the id total this call must reach, or None when ``count`` is absent."""
    if reported_count is None:
        return None
    return min(max_count, max(reported_count, 0))


def esearch_result_still_short(
    collected_count: int,
    max_count: int,
    reported_count: int | None,
) -> bool:
    """Return True while ``count`` is known and not yet covered."""
    target = esearch_target(max_count, reported_count)
    return target is not None and collected_count < target


def esearch_stall_reason(
    page_ids: list[str],
    seen_pages: set[tuple[str, ...]],
    collected_ids: set[str],
) -> str | None:
    """Classify a page that cannot move ``retstart`` toward ``count``."""
    if not page_ids:
        return "empty_page"
    if tuple(page_ids) in seen_pages:
        return "repeated_page"
    if collected_ids.intersection(page_ids):
        return "overlapping_page"
    return None


def reject_stalled_esearch_page(
    host: SearchLogHost,
    page_ids: list[str],
    seen_pages: set[tuple[str, ...]],
    collected: list[str],
    *,
    page_count: int,
    retstart: int,
    reported_count: int | None,
    collected_count: int,
    max_count: int,
) -> None:
    """Fail when the next page is empty, repeats, or overlaps collected ids."""
    reason = esearch_stall_reason(page_ids, seen_pages, set(collected))
    if reason is None:
        return
    raise_pubmed_search_truncated(
        host._logger,
        reason=reason,
        page_count=page_count,
        retstart=retstart,
        reported_count=reported_count,
        collected_count=collected_count,
        max_count=max_count,
    )


def reject_esearch_page_cap(
    host: SearchLogHost,
    *,
    page_count: int,
    retstart: int,
    reported_count: int | None,
    collected_count: int,
    max_count: int,
) -> None:
    """Fail when paging hits the hard page ceiling before ``count``."""
    raise_pubmed_search_truncated(
        host._logger,
        reason="max_pages",
        page_count=page_count,
        retstart=retstart,
        reported_count=reported_count,
        collected_count=collected_count,
        max_count=max_count,
    )


def reject_short_esearch_result(
    host: SearchLogHost,
    collected: list[str],
    *,
    max_count: int,
    reported_count: int | None,
    page_count: int,
    retstart: int,
) -> None:
    """Fail when the collected ids are still shorter than ``count``."""
    target = esearch_target(max_count, reported_count)
    if target is None or len(collected) >= target:
        return
    raise_pubmed_search_truncated(
        host._logger,
        reason="short_idlist",
        page_count=page_count,
        retstart=retstart,
        reported_count=reported_count,
        collected_count=len(collected),
        max_count=max_count,
    )


def raise_pubmed_search_truncated(
    logger: LoggerPort,
    *,
    reason: str,
    page_count: int,
    retstart: int,
    reported_count: int | None,
    collected_count: int,
    max_count: int,
) -> None:
    """Log the incomplete ESearch scan and raise ``PaginationTruncatedError``."""
    raise_pagination_truncated(
        logger,
        event="pubmed_search_truncated",
        reason=reason,
        page_count=page_count,
        page_limit=MAX_ESEARCH_PAGES,
        cursor_field="retstart",
        cursor_value=retstart,
        log_context={
            "count": reported_count,
            "collected": collected_count,
            "max_count": max_count,
        },
    )
