#!/usr/bin/env python3
"""Operator-facing shortcuts for querying deterministic Neo4j memory paths."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Final, TypedDict

try:
    from scripts.ops.neo4j_memory_sync import JsonValue, Neo4jHttpClient, resolve_neo4j_connection
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.ops.neo4j_memory_sync import JsonValue, Neo4jHttpClient, resolve_neo4j_connection

DEFAULT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_NEIGHBOR_RELATION_TYPES: Final[tuple[str, ...]] = (
    "DEPENDS_ON",
    "TESTED_BY",
    "OBSERVED_BY",
    "RUNS_VIA",
    "VALIDATED_BY",
    "BACKED_BY",
    "GOVERNS",
)


class QueryProfile(TypedDict):
    mode: str
    target_label: str
    title: str


QUERY_PROFILES: Final[dict[str, QueryProfile]] = {
    "owner-contract": {
        "mode": "owner",
        "target_label": "contract_surface",
        "title": "Contract ownership path",
    },
    "owner-doc": {
        "mode": "owner",
        "target_label": "doc_source_surface",
        "title": "Documentation ownership path",
    },
    "owner-doc-artifact": {
        "mode": "owner",
        "target_label": "doc_artifact",
        "title": "Documentation artifact ownership path",
    },
    "owner-pipeline": {
        "mode": "owner",
        "target_label": "pipeline_surface",
        "title": "Pipeline ownership path",
    },
    "owner-alert": {
        "mode": "owner",
        "target_label": "alert_surface",
        "title": "Alert ownership path",
    },
    "neighbors-contract": {
        "mode": "neighbors",
        "target_label": "contract_surface",
        "title": "Contract semantic neighborhood",
    },
    "neighbors-doc": {
        "mode": "neighbors",
        "target_label": "doc_source_surface",
        "title": "Documentation semantic neighborhood",
    },
    "neighbors-doc-artifact": {
        "mode": "neighbors",
        "target_label": "doc_artifact",
        "title": "Documentation artifact semantic neighborhood",
    },
    "neighbors-pipeline": {
        "mode": "neighbors",
        "target_label": "pipeline_surface",
        "title": "Pipeline semantic neighborhood",
    },
    "neighbors-alert": {
        "mode": "neighbors",
        "target_label": "alert_surface",
        "title": "Alert semantic neighborhood",
    },
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query deterministic Neo4j memory with operator-facing ownership shortcuts.",
    )
    parser.add_argument(
        "profile",
        choices=sorted(QUERY_PROFILES),
        help="Shortcut profile to execute.",
    )
    parser.add_argument(
        "name",
        help="Exact surface name, for example `chembl.activity` or `BioETLPipelineRunFailed`.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Project root directory.",
    )
    parser.add_argument(
        "--http-uri",
        type=str,
        help="Explicit Neo4j HTTP endpoint, e.g. http://localhost:7474.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit raw JSON rows instead of a human summary.",
    )
    return parser


def _ownership_statement() -> str:
    return (
        "MATCH (target {name: $name}) "
        "UNWIND labels(target) AS target_label "
        "WITH target, target_label "
        "WHERE target_label = $target_label "
        "OPTIONAL MATCH (owner:directory_surface)-[houses:HOUSES]->(target) "
        "OPTIONAL MATCH (zone:repo_zone)-[:CONTAINS*1..8]->(owner) "
        "RETURN target.name AS target_name, "
        "target_label AS target_label, "
        "owner.name AS owner_directory, "
        "zone.name AS repo_zone, "
        "coalesce(houses.provenance, '') AS provenance "
        "ORDER BY "
        "CASE WHEN owner.name IS NULL THEN 1 ELSE 0 END, "
        "size(split(coalesce(owner.name, ''), '/')) ASC, "
        "owner.name ASC"
    )


def _neighbors_statement() -> str:
    return (
        "MATCH (target {name: $name}) "
        "UNWIND labels(target) AS target_label "
        "WITH target, target_label "
        "WHERE target_label = $target_label "
        "CALL { "
        "  WITH target "
        "  MATCH (target)-[rel]->(neighbor) "
        "  WHERE type(rel) IN $relation_types "
        "  RETURN 'outgoing' AS direction, "
        "         type(rel) AS relation_type, "
        "         neighbor.name AS neighbor_name, "
        "         labels(neighbor) AS neighbor_labels "
        "  UNION ALL "
        "  WITH target "
        "  MATCH (neighbor)-[rel]->(target) "
        "  WHERE type(rel) IN $relation_types "
        "  RETURN 'incoming' AS direction, "
        "         type(rel) AS relation_type, "
        "         neighbor.name AS neighbor_name, "
        "         labels(neighbor) AS neighbor_labels "
        "} "
        "RETURN target.name AS target_name, "
        "target_label AS target_label, "
        "direction, "
        "relation_type, "
        "neighbor_name, "
        "neighbor_labels "
        "ORDER BY direction ASC, relation_type ASC, neighbor_name ASC"
    )


def _run_query(
    root: Path,
    profile: str,
    name: str,
    http_uri: str | None,
) -> list[dict[str, JsonValue]]:
    base_uri, username, password, database = resolve_neo4j_connection(root, http_uri)
    client = Neo4jHttpClient(base_uri, username, password, database)
    profile_config = QUERY_PROFILES[profile]
    params: dict[str, JsonValue] = {
        "name": name,
        "target_label": profile_config["target_label"],
    }
    if profile_config["mode"] == "neighbors":
        params["relation_types"] = list(DEFAULT_NEIGHBOR_RELATION_TYPES)
        statement = _neighbors_statement()
    else:
        statement = _ownership_statement()
    return client.query(
        statement,
        params,
    )


def _format_rows(profile: str, name: str, rows: list[dict[str, JsonValue]]) -> str:
    profile_config = QUERY_PROFILES[profile]
    title = profile_config["title"]
    if not rows:
        empty_suffix = "no ownership path found" if profile_config["mode"] == "owner" else "no semantic neighbors found"
        return f"{title}: {empty_suffix} for `{name}`."

    if profile_config["mode"] == "neighbors":
        lines = [f"{title}: `{name}`"]
        seen: set[tuple[str, str, str, str]] = set()
        for row in rows:
            relation_type = str(row.get("relation_type") or "")
            neighbor_name = str(row.get("neighbor_name") or "")
            direction = str(row.get("direction") or "")
            if not relation_type or not neighbor_name:
                continue
            neighbor_labels = row.get("neighbor_labels")
            if isinstance(neighbor_labels, list):
                label_str = ",".join(str(label) for label in neighbor_labels)
            else:
                label_str = ""
            key = (direction, relation_type, neighbor_name, label_str)
            if key in seen:
                continue
            seen.add(key)
            label_suffix = f" | labels={label_str}" if label_str else ""
            lines.append(
                f"- direction={direction} | relation={relation_type} | neighbor={neighbor_name}{label_suffix}"
            )
        if len(lines) == 1:
            lines.append("- no semantic edges found")
        return "\n".join(lines)

    lines = [f"{title}: `{name}`"]
    seen: set[tuple[str, str, str, str]] = set()
    for row in rows:
        owner = str(row.get("owner_directory") or "")
        if not owner:
            continue
        zone = str(row.get("repo_zone") or "")
        provenance = str(row.get("provenance") or "")
        key = (zone, owner, provenance, "")
        if key in seen:
            continue
        seen.add(key)
        provenance_suffix = f" | provenance={provenance}" if provenance else ""
        lines.append(f"- zone={zone} | owner={owner}{provenance_suffix}")
    if len(lines) == 1:
        lines.append("- no directory ownership edges found")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    rows = _run_query(args.root, args.profile, args.name, args.http_uri)
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(_format_rows(args.profile, args.name, rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
