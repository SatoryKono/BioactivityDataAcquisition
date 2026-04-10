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
    "duplication-cluster": {
        "mode": "duplication_cluster",
        "target_label": "duplication_cluster",
        "title": "Duplication cluster",
    },
    "promotion-candidates": {
        "mode": "promotion_candidates",
        "target_label": "duplication_cluster",
        "title": "Promotion candidates",
    },
    "dead-code-candidates": {
        "mode": "dead_code_candidates",
        "target_label": "retirement_candidate",
        "title": "Dead code candidates",
    },
    "current-cycle-code": {
        "mode": "current_cycle_code",
        "target_label": "development_cycle_surface",
        "title": "Current-cycle code surfaces",
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
        help=(
            "Exact surface name, duplication cluster name, or family name. "
            "Examples: `chembl.activity`, `BioETLPipelineRunFailed`, "
            "`adapter_layer`, `composite_layer:method_surface:d1c4b44398a1`, `all`."
        ),
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


def _duplication_cluster_statement() -> str:
    return (
        "MATCH (cluster:duplication_cluster {name: $name}) "
        "OPTIONAL MATCH (cluster)-[:CAN_PROMOTE_TO]->(target) "
        "OPTIONAL MATCH (cluster)-[:CONTAINS]->(member) "
        "OPTIONAL MATCH (cluster)-[:COVERED_BY_TEST]->(test) "
        "RETURN cluster.name AS cluster_name, "
        "cluster.family_name AS family_name, "
        "cluster.surface_kind AS surface_kind, "
        "cluster.duplicate_count AS duplicate_count, "
        "cluster.promotion_score AS promotion_score, "
        "target.name AS promotion_target, "
        "labels(target) AS promotion_target_labels, "
        "collect(DISTINCT CASE "
        "  WHEN member.name IS NULL THEN NULL "
        "  ELSE {name: member.name, labels: labels(member)} "
        "END) AS members, "
        "collect(DISTINCT test.name) AS tests"
    )


def _promotion_candidates_statement() -> str:
    return (
        "MATCH (cluster:duplication_cluster) "
        "WHERE $name = 'all' OR cluster.family_name = $name "
        "OPTIONAL MATCH (cluster)-[:CAN_PROMOTE_TO]->(target) "
        "OPTIONAL MATCH (cluster)-[:CONTAINS]->(member) "
        "OPTIONAL MATCH (cluster)-[:COVERED_BY_TEST]->(test) "
        "RETURN cluster.name AS cluster_name, "
        "cluster.family_name AS family_name, "
        "cluster.surface_kind AS surface_kind, "
        "cluster.duplicate_count AS duplicate_count, "
        "cluster.promotion_score AS promotion_score, "
        "target.name AS promotion_target, "
        "labels(target) AS promotion_target_labels, "
        "count(DISTINCT member) AS member_count, "
        "count(DISTINCT test) AS test_count "
        "ORDER BY cluster.promotion_score DESC, cluster.duplicate_count DESC, cluster.name ASC"
    )


def _dead_code_candidates_statement() -> str:
    return (
        "MATCH (candidate:retirement_candidate) "
        "WHERE $name = 'all' OR candidate.family_name = $name OR candidate.target_name = $name "
        "OPTIONAL MATCH (candidate)-[:CANDIDATE_FOR_REMOVAL]->(target) "
        "OPTIONAL MATCH (candidate)-[:BLOCKED_FROM_DELETION_BY]->(cycle) "
        "RETURN candidate.name AS candidate_name, "
        "candidate.family_name AS family_name, "
        "candidate.target_label AS target_label, "
        "candidate.target_name AS target_name, "
        "candidate.deletion_score AS deletion_score, "
        "candidate.deletion_confidence AS deletion_confidence, "
        "candidate.recent_age_days AS recent_age_days, "
        "candidate.only_test_referenced AS only_test_referenced, "
        "candidate.deprecation_markers AS deprecation_markers, "
        "candidate.runtime_anchor_count AS runtime_anchor_count, "
        "candidate.config_anchor_count AS config_anchor_count, "
        "candidate.doc_anchor_count AS doc_anchor_count, "
        "candidate.test_anchor_count AS test_anchor_count, "
        "target.name AS removal_target, "
        "labels(target) AS removal_target_labels, "
        "cycle.name AS blocked_by_cycle "
        "ORDER BY candidate.deletion_score DESC, candidate.target_name ASC"
    )


def _current_cycle_code_statement() -> str:
    return (
        "MATCH (cycle:development_cycle_surface) "
        "WHERE $name = 'all' OR cycle.family_name = $name OR cycle.target_name = $name "
        "OPTIONAL MATCH (target)-[:OWNED_BY_CYCLE]->(cycle) "
        "RETURN cycle.name AS cycle_name, "
        "cycle.family_name AS family_name, "
        "cycle.target_label AS target_label, "
        "cycle.target_name AS target_name, "
        "cycle.cycle_status AS cycle_status, "
        "cycle.cycle_score AS cycle_score, "
        "cycle.recent_age_days AS recent_age_days, "
        "cycle.wip_markers AS wip_markers, "
        "cycle.runtime_anchor_count AS runtime_anchor_count, "
        "cycle.config_anchor_count AS config_anchor_count, "
        "cycle.doc_anchor_count AS doc_anchor_count, "
        "cycle.test_anchor_count AS test_anchor_count, "
        "labels(target) AS target_labels "
        "ORDER BY cycle.cycle_score DESC, cycle.target_name ASC"
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
    elif profile_config["mode"] == "duplication_cluster":
        statement = _duplication_cluster_statement()
    elif profile_config["mode"] == "promotion_candidates":
        statement = _promotion_candidates_statement()
    elif profile_config["mode"] == "dead_code_candidates":
        statement = _dead_code_candidates_statement()
    elif profile_config["mode"] == "current_cycle_code":
        statement = _current_cycle_code_statement()
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
        empty_suffix = {
            "owner": "no ownership path found",
            "neighbors": "no semantic neighbors found",
            "duplication_cluster": "no duplication cluster found",
            "promotion_candidates": "no promotion candidates found",
            "dead_code_candidates": "no dead code candidates found",
            "current_cycle_code": "no current-cycle code surfaces found",
        }[profile_config["mode"]]
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

    if profile_config["mode"] == "duplication_cluster":
        row = rows[0]
        family_name = str(row.get("family_name") or "")
        surface_kind = str(row.get("surface_kind") or "")
        duplicate_count = str(row.get("duplicate_count") or "")
        promotion_score = str(row.get("promotion_score") or "")
        promotion_target = str(row.get("promotion_target") or "")
        target_labels = row.get("promotion_target_labels")
        members = row.get("members")
        tests = row.get("tests")
        lines = [f"{title}: `{name}`"]
        lines.append(
            f"- family={family_name} | surface_kind={surface_kind} | duplicates={duplicate_count} | promotion_score={promotion_score}"
        )
        if promotion_target:
            if isinstance(target_labels, list):
                label_str = ",".join(str(label) for label in target_labels)
            else:
                label_str = ""
            label_suffix = f" | labels={label_str}" if label_str else ""
            lines.append(f"- promotion_target={promotion_target}{label_suffix}")
        if isinstance(members, list):
            normalized_members = []
            for member in members:
                if not isinstance(member, dict):
                    continue
                member_name = str(member.get("name") or "")
                if not member_name:
                    continue
                labels = member.get("labels")
                if isinstance(labels, list):
                    label_str = ",".join(str(label) for label in labels)
                else:
                    label_str = ""
                label_suffix = f" | labels={label_str}" if label_str else ""
                normalized_members.append(f"- member={member_name}{label_suffix}")
            lines.extend(sorted(normalized_members))
        if isinstance(tests, list):
            normalized_tests = sorted(
                {
                    f"- covered_by_test={str(test_name)}"
                    for test_name in tests
                    if test_name is not None and str(test_name)
                }
            )
            lines.extend(normalized_tests)
        return "\n".join(lines)

    if profile_config["mode"] == "promotion_candidates":
        lines = [f"{title}: `{name}`"]
        seen: set[str] = set()
        for row in rows:
            cluster_name = str(row.get("cluster_name") or "")
            if not cluster_name or cluster_name in seen:
                continue
            seen.add(cluster_name)
            family_name = str(row.get("family_name") or "")
            surface_kind = str(row.get("surface_kind") or "")
            duplicate_count = str(row.get("duplicate_count") or "")
            promotion_score = str(row.get("promotion_score") or "")
            promotion_target = str(row.get("promotion_target") or "")
            member_count = str(row.get("member_count") or "")
            test_count = str(row.get("test_count") or "")
            lines.append(
                f"- cluster={cluster_name} | family={family_name} | surface_kind={surface_kind} | "
                f"duplicates={duplicate_count} | members={member_count} | tests={test_count} | "
                f"promotion_score={promotion_score} | target={promotion_target}"
            )
        if len(lines) == 1:
            lines.append("- no promotion candidates found")
        return "\n".join(lines)

    if profile_config["mode"] == "dead_code_candidates":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            target_name = str(row.get("target_name") or "")
            if not target_name:
                continue
            family_name = str(row.get("family_name") or "")
            target_label = str(row.get("target_label") or "")
            deletion_score = str(row.get("deletion_score") or "")
            deletion_confidence = str(row.get("deletion_confidence") or "")
            recent_age_days = str(row.get("recent_age_days") or "")
            only_test_referenced = str(row.get("only_test_referenced") or "")
            runtime_anchor_count = str(row.get("runtime_anchor_count") or "")
            config_anchor_count = str(row.get("config_anchor_count") or "")
            doc_anchor_count = str(row.get("doc_anchor_count") or "")
            test_anchor_count = str(row.get("test_anchor_count") or "")
            blocked_by_cycle = str(row.get("blocked_by_cycle") or "")
            deprecation_markers = row.get("deprecation_markers")
            if isinstance(deprecation_markers, list):
                marker_str = ",".join(str(marker) for marker in deprecation_markers)
            else:
                marker_str = ""
            blocked_suffix = f" | blocked_by={blocked_by_cycle}" if blocked_by_cycle else ""
            marker_suffix = f" | deprecation_markers={marker_str}" if marker_str else ""
            lines.append(
                f"- target={target_name} | label={target_label} | family={family_name} | deletion_score={deletion_score} "
                f"| confidence={deletion_confidence} | recent_age_days={recent_age_days} | only_test_referenced={only_test_referenced} "
                f"| runtime={runtime_anchor_count} | config={config_anchor_count} | docs={doc_anchor_count} | tests={test_anchor_count}"
                f"{marker_suffix}{blocked_suffix}"
            )
        if len(lines) == 1:
            lines.append("- no dead code candidates found")
        return "\n".join(lines)

    if profile_config["mode"] == "current_cycle_code":
        lines = [f"{title}: `{name}`"]
        for row in rows:
            target_name = str(row.get("target_name") or "")
            if not target_name:
                continue
            family_name = str(row.get("family_name") or "")
            target_label = str(row.get("target_label") or "")
            cycle_status = str(row.get("cycle_status") or "")
            cycle_score = str(row.get("cycle_score") or "")
            recent_age_days = str(row.get("recent_age_days") or "")
            runtime_anchor_count = str(row.get("runtime_anchor_count") or "")
            config_anchor_count = str(row.get("config_anchor_count") or "")
            doc_anchor_count = str(row.get("doc_anchor_count") or "")
            test_anchor_count = str(row.get("test_anchor_count") or "")
            wip_markers = row.get("wip_markers")
            if isinstance(wip_markers, list):
                marker_str = ",".join(str(marker) for marker in wip_markers)
            else:
                marker_str = ""
            marker_suffix = f" | wip_markers={marker_str}" if marker_str else ""
            lines.append(
                f"- target={target_name} | label={target_label} | family={family_name} | cycle_status={cycle_status} "
                f"| cycle_score={cycle_score} | recent_age_days={recent_age_days} | runtime={runtime_anchor_count} "
                f"| config={config_anchor_count} | docs={doc_anchor_count} | tests={test_anchor_count}{marker_suffix}"
            )
        if len(lines) == 1:
            lines.append("- no current-cycle code surfaces found")
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
