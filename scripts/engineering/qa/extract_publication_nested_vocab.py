"""Extract nested publication-sidecar vocabulary from Bronze fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _sorted_payload(values: dict[str, set[str]]) -> dict[str, list[str]]:
    return {key: sorted(value) for key, value in values.items() if value}


def extract_openalex_nested_vocab(paths: list[Path]) -> dict[str, list[str]]:
    observed = {
        "source_type": set(),
        "raw_type": set(),
        "version": set(),
        "indexed_in": set(),
        "license": set(),
        "oa_status": set(),
    }
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            primary = row.get("primary_location") or {}
            source = primary.get("source") or {}
            if isinstance(source, dict) and source.get("type") is not None:
                observed["source_type"].add(str(source["type"]))
            if primary.get("raw_type") is not None:
                observed["raw_type"].add(str(primary["raw_type"]))
            if primary.get("version") is not None:
                observed["version"].add(str(primary["version"]))
            if primary.get("license") is not None:
                observed["license"].add(str(primary["license"]))
            for value in row.get("indexed_in") or []:
                observed["indexed_in"].add(str(value))
            oa = row.get("open_access") or {}
            if isinstance(oa, dict) and oa.get("oa_status") is not None:
                observed["oa_status"].add(str(oa["oa_status"]))
            for location in row.get("locations") or []:
                if not isinstance(location, dict):
                    continue
                if location.get("version") is not None:
                    observed["version"].add(str(location["version"]))
                if location.get("license") is not None:
                    observed["license"].add(str(location["license"]))
                source = location.get("source") or {}
                if isinstance(source, dict) and source.get("type") is not None:
                    observed["source_type"].add(str(source["type"]))
    return _sorted_payload(observed)


def extract_semanticscholar_nested_vocab(paths: list[Path]) -> dict[str, list[str]]:
    observed = {
        "publication_types": set(),
        "citation_context_keys": set(),
        "subject_fields": set(),
        "author_id_families": set(),
    }
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            for value in row.get("publicationTypes") or []:
                observed["publication_types"].add(str(value))
            for citation in row.get("citations") or []:
                if isinstance(citation, dict):
                    observed["citation_context_keys"].update(map(str, citation.keys()))
            for value in row.get("fieldsOfStudy") or []:
                observed["subject_fields"].add(str(value))
            for author in row.get("authors") or []:
                if not isinstance(author, dict):
                    continue
                external_ids = author.get("externalIds") or {}
                if isinstance(external_ids, dict):
                    observed["author_id_families"].update(map(str, external_ids.keys()))
    return _sorted_payload(observed)


def extract_pubmed_nested_vocab(paths: list[Path]) -> dict[str, list[str]]:
    observed = {
        "publication_types": set(),
        "mesh_keys": set(),
        "affiliation_keys": set(),
    }
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            for value in row.get("PublicationTypeList") or []:
                observed["publication_types"].add(str(value))
            for mesh in row.get("MeshHeadingList") or []:
                if isinstance(mesh, dict):
                    observed["mesh_keys"].update(map(str, mesh.keys()))
            for author in row.get("AuthorList") or []:
                if isinstance(author, dict):
                    observed["affiliation_keys"].update(map(str, author.keys()))
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
