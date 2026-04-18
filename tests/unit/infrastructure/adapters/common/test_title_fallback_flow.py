"""Unit tests for extracted title-fallback flow helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from tests.async_utils import collect_async_iterator

from bioetl.infrastructure.adapters.common._title_fallback_flow import (
    get_fallback_title,
    iter_missing_doi_fallback_records,
    iter_title_only_fallback_records,
    truncate_title,
)


def _normalize_doi_lower(doi: str) -> str:
    return doi.lower()


def _result_identifier(result: dict[str, Any]) -> tuple[str, str]:
    return ("found_id", str(result["id"]))


def _process_found_title_fallback(result: dict[str, Any], doi: str) -> dict[str, Any]:
    return {
        **result,
        "_lookup_method": "title_fallback",
        "_original_id": doi,
    }


def _process_title_only_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        **result,
        "_lookup_method": "title_only",
    }


def _identity_found_result(result: dict[str, Any], doi: str) -> dict[str, Any]:
    del doi
    return result


@pytest.mark.unit
def test_get_fallback_title_uses_normalized_key_when_original_missing() -> None:
    """Normalized identifier fallback should work when original key is absent."""
    title = get_fallback_title(
        "DOI:10.1000/ABC",
        "doi:10.1000/abc",
        {"doi:10.1000/abc": "Normalized Title"},
    )

    assert title == "Normalized Title"


@pytest.mark.unit
def test_truncate_title_shortens_only_when_needed() -> None:
    """Title truncation should preserve short titles and shorten long ones."""
    assert truncate_title("Short") == "Short"
    assert truncate_title("x" * 55, 10) == "xxxxxxxxxx..."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_iter_missing_doi_fallback_records_yields_processed_records_and_respects_limit() -> (
    None
):
    """Missing-DOI flow should yield processed records and stop at limit."""
    logger = MagicMock()

    async def search_by_title(title: str) -> dict[str, Any] | None:
        return {"id": title.lower(), "title": title}

    records = await collect_async_iterator(
        iter_missing_doi_fallback_records(
            dois=["DOI-1", "DOI-2"],
            found_dois=set(),
            fallback_mapping={
                "doi-1": "Alpha Title",
                "doi-2": "Beta Title",
            },
            normalize_fn=_normalize_doi_lower,
            limit=1,
            fetched=0,
            get_fallback_title=get_fallback_title,
            truncate_title=truncate_title,
            search_by_title=search_by_title,
            get_result_identifier=_result_identifier,
            process_found_result=_process_found_title_fallback,
            logger=logger,
            event_no_fallback_title="no_fallback_title",
            event_fallback_attempt="title_fallback_attempt",
            event_fallback_success="title_fallback_success",
            event_fallback_not_found="title_fallback_not_found",
        )
    )

    assert records == [
        {
            "id": "alpha title",
            "title": "Alpha Title",
            "_lookup_method": "title_fallback",
            "_original_id": "DOI-1",
        }
    ]
    assert logger.info.call_args_list[0].args[0] == "title_fallback_attempt"
    assert logger.info.call_args_list[1].args[0] == "title_fallback_success"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_iter_missing_doi_fallback_records_logs_missing_title_and_not_found() -> (
    None
):
    """Missing-title and not-found branches should be explicit and testable."""
    logger = MagicMock()

    async def search_by_title(title: str) -> dict[str, Any] | None:
        return None

    records = await collect_async_iterator(
        iter_missing_doi_fallback_records(
            dois=["DOI-1", "DOI-2", "DOI-3"],
            found_dois={"doi-1"},
            fallback_mapping={"DOI-2": "Known Title"},
            normalize_fn=_normalize_doi_lower,
            limit=None,
            fetched=0,
            get_fallback_title=get_fallback_title,
            truncate_title=truncate_title,
            search_by_title=search_by_title,
            get_result_identifier=_result_identifier,
            process_found_result=_identity_found_result,
            logger=logger,
            event_no_fallback_title="no_fallback_title",
            event_fallback_attempt="title_fallback_attempt",
            event_fallback_success="title_fallback_success",
            event_fallback_not_found="title_fallback_not_found",
        )
    )

    assert records == []
    assert logger.info.call_args_list[0].args[0] == "title_fallback_attempt"
    assert logger.warning.call_args.args[0] == "title_fallback_not_found"
    assert logger.debug.call_args.args[0] == "no_fallback_title"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_iter_title_only_fallback_records_supports_marker_and_empty_entry_lookup() -> (
    None
):
    """Title-only flow should support marker keys and legacy empty-string fallback."""
    logger = MagicMock()

    async def search_by_title(title: str) -> dict[str, Any] | None:
        return {"id": title.lower(), "title": title}

    records = await collect_async_iterator(
        iter_title_only_fallback_records(
            entries=["__title_only_1__", ""],
            fallback_mapping={
                "__title_only_1__": "Marker Title",
                "": "Legacy Empty Title",
            },
            limit=None,
            fetched=0,
            truncate_title=truncate_title,
            search_by_title=search_by_title,
            get_result_identifier=_result_identifier,
            process_title_only_result=_process_title_only_result,
            logger=logger,
            event_title_only_attempt="title_only_attempt",
            event_title_only_success="title_only_success",
            event_title_only_not_found="title_only_not_found",
        )
    )

    assert records == [
        {
            "id": "marker title",
            "title": "Marker Title",
            "_lookup_method": "title_only",
        },
        {
            "id": "legacy empty title",
            "title": "Legacy Empty Title",
            "_lookup_method": "title_only",
        },
    ]
    info_events = [call.args[0] for call in logger.info.call_args_list]
    assert info_events == [
        "title_only_attempt",
        "title_only_success",
        "title_only_attempt",
        "title_only_success",
    ]
