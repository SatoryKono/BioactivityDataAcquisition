"""Structured cross-reference extraction helpers for UniProt."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.application.pipelines.uniprot.extractors._crossref_common import (
    filter_xrefs_by_database,
    parse_properties,
    serialize_json_or_none,
)
from bioetl.domain.types import JsonDict

EntryBuilder = Callable[[JsonDict], JsonDict | None]


def extract_xref_ids(xrefs: list[JsonDict] | None, database: str) -> str | None:
    """Extract simple ID lists for a selected xref database."""
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
    builder: EntryBuilder,
) -> str | None:
    """Extract structured xrefs using a typed builder callback."""
    entries = [
        entry
        for xref in filter_xrefs_by_database(xrefs, database)
        if (entry := builder(xref)) is not None
    ]
    return serialize_json_or_none(entries)


def build_pdb_entry(xref: JsonDict) -> JsonDict | None:
    """Build a structured PDB record from UniProt cross-reference."""
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
    """Build a structured InterPro record from UniProt cross-reference."""
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
    """Build a structured Pfam record from UniProt cross-reference."""
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
    """Build a structured Reactome record from UniProt cross-reference."""
    reactome_id = xref.get("id")
    if not reactome_id:
        return None

    props = parse_properties(xref.get("properties", []))
    entry: JsonDict = {"id": str(reactome_id)}  # Any: JSON values are heterogeneous
    pathway_name = props.get("PathwayName")
    if pathway_name:
        entry["pathway_name"] = pathway_name
    return entry
