"""Structured cross-reference extraction helpers for UniProt."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.application.pipelines.uniprot.extractors._crossref_common import (
    filter_xrefs_by_database,
    parse_properties,
    serialize_json_or_none,
)
from bioetl.domain.types import JsonDict

EntryMapper = Callable[[JsonDict], JsonDict | None]


def extract_xref_ids(xrefs: list[JsonDict] | None, database: str) -> str | None:
    """Extract simple ID lists for a selected xref database.

    Args:
        xrefs: List of UniProt cross-reference dicts from the API response, or None.
        database: Database name string to filter on (e.g. 'PDB', 'InterPro').

    Returns:
        JSON-serialized list of ID strings for the given database, or None if empty.
    """
    ids = [
        str(xref_id)
        for xref in filter_xrefs_by_database(xrefs, database)
        if (xref_id := xref.get("id"))
    ]
    return serialize_json_or_none(ids)


def extract_structured_xrefs(
    xrefs: list[JsonDict] | None,
    *,
    database: str,
    mapper: EntryMapper,
) -> str | None:
    """Extract structured xrefs using a typed mapper callback.

    Args:
        xrefs: List of UniProt cross-reference dicts from the API response, or None.
        database: Database name string to filter on.
        mapper: Callable that converts a single cross-reference dict into a
            structured entry dict, or returns None to skip the entry.

    Returns:
        JSON-serialized list of structured entry dicts, or None if no valid
        entries are produced.
    """
    entries = [
        entry
        for xref in filter_xrefs_by_database(xrefs, database)
        if (entry := mapper(xref)) is not None
    ]
    return serialize_json_or_none(entries)


def build_pdb_entry(xref: JsonDict) -> JsonDict | None:
    """Build a structured PDB record from UniProt cross-reference.

    Args:
        xref: Single UniProt cross-reference dict for the PDB database.

    Returns:
        Dict with PDB id and optional method, resolution, chains fields,
        or None if the cross-reference has no id.
    """
    pdb_id = xref.get("id")
    if not pdb_id:
        return None

    props = parse_properties(xref.get("properties", []))
    entry: JsonDict = {"id": str(pdb_id)}  # Any: JSON values are heterogeneous
    for source_key, target_key in (
        ("Method", "method"),
        ("Resolution", "resolution"),
        ("Chains", "chains"),
    ):
        value = props.get(source_key)
        if value:
            entry[target_key] = value
    return entry


def build_interpro_entry(xref: JsonDict) -> JsonDict | None:
    """Build a structured InterPro record from UniProt cross-reference.

    Args:
        xref: Single UniProt cross-reference dict for the InterPro database.

    Returns:
        Dict with InterPro id and optional name field, or None if the
        cross-reference has no id.
    """
    interpro_id = xref.get("id")
    if not interpro_id:
        return None

    props = parse_properties(xref.get("properties", []))
    entry: JsonDict = {"id": str(interpro_id)}  # Any: JSON values are heterogeneous
    entry_name = props.get("EntryName")
    if entry_name:
        entry["name"] = entry_name
    return entry


def build_pfam_entry(xref: JsonDict) -> JsonDict | None:
    """Build a structured Pfam record from UniProt cross-reference.

    Args:
        xref: Single UniProt cross-reference dict for the Pfam database.

    Returns:
        Dict with Pfam id and optional name and match_status fields, or None
        if the cross-reference has no id.
    """
    pfam_id = xref.get("id")
    if not pfam_id:
        return None

    props = parse_properties(xref.get("properties", []))
    entry: JsonDict = {"id": str(pfam_id)}  # Any: JSON values are heterogeneous
    entry_name = props.get("EntryName")
    if entry_name:
        entry["name"] = entry_name

    match_status = props.get("MatchStatus")
    if match_status:
        entry["match_status"] = match_status

    return entry


def build_reactome_entry(xref: JsonDict) -> JsonDict | None:
    """Build a structured Reactome record from UniProt cross-reference.

    Args:
        xref: Single UniProt cross-reference dict for the Reactome database.

    Returns:
        Dict with Reactome id and optional pathway_name field, or None if the
        cross-reference has no id.
    """
    reactome_id = xref.get("id")
    if not reactome_id:
        return None

    props = parse_properties(xref.get("properties", []))
    entry: JsonDict = {"id": str(reactome_id)}  # Any: JSON values are heterogeneous
    pathway_name = props.get("PathwayName")
    if pathway_name:
        entry["pathway_name"] = pathway_name
    return entry
