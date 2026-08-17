"""Fetch helpers for IDMappingDataSource."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Mapping

    from bioetl.domain.ports import (
        IDMappingPort,
        IDMappingSourceReaderPort,
        LoggerPort,
    )


class _IDMappingFetchState(Protocol):
    """Structural contract for IDMappingDataSource fetch helpers."""

    _client: IDMappingPort
    _id_source_reader: IDMappingSourceReaderPort
    _input_path: str
    _logger: LoggerPort
    _from_db: str
    _to_db: str
    _id_column: str
    _seed_ids: list[str] | None


async def fetch_records(
    state: _IDMappingFetchState,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    filter_ids: list[str] | None = None,
    filter_field: str | None = None,
    offset: int | None = None,
) -> AsyncIterator[JsonDict]:  # Any: record values are heterogeneous
    """Fetch ID mapping records for the requested source IDs."""
    _ = query, filter_field
    warn_unexpected_entity_type(state, entity_type)
    chembl_ids, source = await resolve_chembl_ids(
        state, filter_ids, limit, offset
    )
    if not chembl_ids:
        state._logger.warning("no_ids_to_map", input_path=str(state._input_path))
        return
    state._logger.info(
        "idmapping_fetch_started",
        source=source,
        input_path=str(state._input_path),
        chembl_id_count=len(chembl_ids),
    )
    mapping_results = await state._client.map_ids(
        from_db=state._from_db,
        to_db=state._to_db,
        ids=chembl_ids,
    )
    found_count = 0
    for chembl_id in chembl_ids:
        record, is_mapped = build_mapping_record(chembl_id, mapping_results)
        if is_mapped:
            found_count += 1
        yield record
    state._logger.info(
        "idmapping_fetch_completed",
        total_ids=len(chembl_ids),
        mapped=found_count,
        not_mapped=len(chembl_ids) - found_count,
    )


def warn_unexpected_entity_type(
    state: _IDMappingFetchState,
    entity_type: str,
) -> None:
    """Warn when fetch is called with an unsupported entity type."""
    if entity_type == "idmapping":
        return
    state._logger.warning(
        "unexpected_entity_type",
        expected="idmapping",
        received=entity_type,
    )


async def resolve_chembl_ids(
    state: _IDMappingFetchState,
    filter_ids: list[str] | None,
    limit: int | None,
    offset: int | None = None,
) -> tuple[list[str], str]:
    """Resolve ChEMBL IDs from seed data, direct filters, or configured input."""
    if state._seed_ids:
        chembl_ids = list(state._seed_ids)
        state._logger.info("idmapping_using_seed_ids", count=len(chembl_ids))
        source = "seed"
    elif filter_ids:
        chembl_ids = list(filter_ids)
        state._logger.info("idmapping_using_filter_ids", count=len(chembl_ids))
        source = "filter"
    else:
        chembl_ids = await read_chembl_ids(state)
        source = "csv"
    return apply_offset_and_limit(chembl_ids, offset, limit), source


def apply_limit(ids: list[str], limit: int | None) -> list[str]:
    """Apply an optional limit to the resolved ID list."""
    if limit is None:
        return ids
    return ids[:limit]


def apply_offset_and_limit(
    ids: list[str],
    offset: int | None,
    limit: int | None,
) -> list[str]:
    """Apply offset first, then limit, so later pages do not repeat earlier IDs."""
    start = max(offset or 0, 0)
    return apply_limit(ids[start:], limit)


def build_mapping_record(
    chembl_id: str,
    mapping_results: Mapping[
        str, JsonDict | None
    ],  # Any: mapping payload values vary by provider
) -> tuple[JsonDict, bool]:
    """Build an output record and mapping flag for one ChEMBL ID."""
    entry_data = mapping_results.get(chembl_id)
    if entry_data is not None and isinstance(entry_data, dict):
        result: JsonDict = {"target_id": chembl_id}
        result.update(entry_data)
        return result, True
    return {
        "target_id": chembl_id,
        "uniprot_accession": None,
    }, False


async def read_chembl_ids(state: _IDMappingFetchState) -> list[str]:
    """Read source ChEMBL IDs through the injected source reader."""
    chembl_ids: list[str] = await state._id_source_reader.read_ids(
        source_path=state._input_path,
        id_column=state._id_column,
    )
    return chembl_ids


def format_repr(state: _IDMappingFetchState) -> str:
    """Format the debug representation for IDMappingDataSource."""
    return (
        f"IDMappingDataSource("
        f"input_path='{state._input_path}', "
        f"from_db='{state._from_db}', "
        f"to_db='{state._to_db}')"
    )
