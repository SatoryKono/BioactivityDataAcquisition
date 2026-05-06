"""Extract nested publication-sidecar vocabulary from Bronze fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _sorted_payload(values: dict[str, set[str]]) -> dict[str, list[str]]:
    return {key: sorted(value) for key, value in values.items() if value}


def _iter_jsonl_payloads(paths: list[Path]) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                payloads.append(payload)
    return payloads


def _add_if_present(bucket: set[str], value: object | None) -> None:
    if value is not None:
        bucket.add(str(value))


def _collect_openalex_primary_location(
    row: dict[str, object],
    observed: dict[str, set[str]],
) -> None:
    primary = row.get("primary_location") or {}
    if not isinstance(primary, dict):
        return
    source = primary.get("source") or {}
    if isinstance(source, dict):
        _add_if_present(observed["source_type"], source.get("type"))
    _add_if_present(observed["raw_type"], primary.get("raw_type"))
    _add_if_present(observed["version"], primary.get("version"))
    _add_if_present(observed["license"], primary.get("license"))


def _collect_openalex_indexed_in(
    row: dict[str, object],
    observed: dict[str, set[str]],
) -> None:
    for value in row.get("indexed_in") or []:
        observed["indexed_in"].add(str(value))


def _collect_openalex_open_access(
    row: dict[str, object],
    observed: dict[str, set[str]],
) -> None:
    open_access = row.get("open_access") or {}
    if isinstance(open_access, dict):
        _add_if_present(observed["oa_status"], open_access.get("oa_status"))


def _collect_openalex_locations(
    row: dict[str, object],
    observed: dict[str, set[str]],
) -> None:
    for location in row.get("locations") or []:
        if not isinstance(location, dict):
            continue
        _add_if_present(observed["version"], location.get("version"))
        _add_if_present(observed["license"], location.get("license"))
        source = location.get("source") or {}
        if isinstance(source, dict):
            _add_if_present(observed["source_type"], source.get("type"))


def extract_openalex_nested_vocab(paths: list[Path]) -> dict[str, list[str]]:
    observed = {
        "source_type": set(),
        "raw_type": set(),
        "version": set(),
        "indexed_in": set(),
        "license": set(),
        "oa_status": set(),
    }
    for row in _iter_jsonl_payloads(paths):
        _collect_openalex_primary_location(row, observed)
        _collect_openalex_indexed_in(row, observed)
        _collect_openalex_open_access(row, observed)
        _collect_openalex_locations(row, observed)
    return _sorted_payload(observed)


def _collect_semanticscholar_publication_types(
    row: dict[str, object],
    observed: dict[str, set[str]],
) -> None:
    for value in row.get("publicationTypes") or []:
        observed["publication_types"].add(str(value))


def _collect_semanticscholar_citation_context_keys(
    row: dict[str, object],
    observed: dict[str, set[str]],
) -> None:
    for citation in row.get("citations") or []:
        if isinstance(citation, dict):
            observed["citation_context_keys"].update(map(str, citation.keys()))


def _collect_semanticscholar_subject_fields(
    row: dict[str, object],
    observed: dict[str, set[str]],
) -> None:
    for value in row.get("fieldsOfStudy") or []:
        observed["subject_fields"].add(str(value))


def _collect_semanticscholar_author_id_families(
    row: dict[str, object],
    observed: dict[str, set[str]],
) -> None:
    for author in row.get("authors") or []:
        if not isinstance(author, dict):
            continue
        external_ids = author.get("externalIds") or {}
        if isinstance(external_ids, dict):
            observed["author_id_families"].update(map(str, external_ids.keys()))


def extract_semanticscholar_nested_vocab(paths: list[Path]) -> dict[str, list[str]]:
    observed = {
        "publication_types": set(),
        "citation_context_keys": set(),
        "subject_fields": set(),
        "author_id_families": set(),
    }
    for row in _iter_jsonl_payloads(paths):
        _collect_semanticscholar_publication_types(row, observed)
        _collect_semanticscholar_citation_context_keys(row, observed)
        _collect_semanticscholar_subject_fields(row, observed)
        _collect_semanticscholar_author_id_families(row, observed)
    return _sorted_payload(observed)


def _collect_pubmed_publication_types(
    row: dict[str, object],
    observed: dict[str, set[str]],
) -> None:
    for value in row.get("PublicationTypeList") or []:
        observed["publication_types"].add(str(value))


def _collect_pubmed_mesh_keys(
    row: dict[str, object],
    observed: dict[str, set[str]],
) -> None:
    for mesh in row.get("MeshHeadingList") or []:
        if isinstance(mesh, dict):
            observed["mesh_keys"].update(map(str, mesh.keys()))


def _collect_pubmed_affiliation_keys(
    row: dict[str, object],
    observed: dict[str, set[str]],
) -> None:
    for author in row.get("AuthorList") or []:
        if isinstance(author, dict):
            observed["affiliation_keys"].update(map(str, author.keys()))


def extract_pubmed_nested_vocab(paths: list[Path]) -> dict[str, list[str]]:
    observed = {
        "publication_types": set(),
        "mesh_keys": set(),
        "affiliation_keys": set(),
    }
    for row in _iter_jsonl_payloads(paths):
        _collect_pubmed_publication_types(row, observed)
        _collect_pubmed_mesh_keys(row, observed)
        _collect_pubmed_affiliation_keys(row, observed)
    return _sorted_payload(observed)


def extract_publication_nested_vocab(
    *,
    openalex_paths: list[Path],
    semanticscholar_paths: list[Path],
    pubmed_paths: list[Path],
) -> dict[str, dict[str, list[str]]]:
    return {
        "openalex": extract_openalex_nested_vocab(openalex_paths),
        "semanticscholar": extract_semanticscholar_nested_vocab(
            semanticscholar_paths
        ),
        "pubmed": extract_pubmed_nested_vocab(pubmed_paths),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openalex", nargs="+", type=Path, required=True)
    parser.add_argument("--semanticscholar", nargs="+", type=Path, required=True)
    parser.add_argument("--pubmed", nargs="+", type=Path, required=True)
    args = parser.parse_args(argv)

    payload = extract_publication_nested_vocab(
        openalex_paths=list(args.openalex),
        semanticscholar_paths=list(args.semanticscholar),
        pubmed_paths=list(args.pubmed),
    )
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
