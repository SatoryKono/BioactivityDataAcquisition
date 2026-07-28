#!/usr/bin/env python3
"""Validate semantic governance policy for reviewed ETL semantic residuals."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REVIEW_REGISTRY = (
    REPO_ROOT / "configs" / "field_registry" / "semantic_audit_review_registry.yaml"
)
DEFAULT_PAIR_MATRIX = (
    REPO_ROOT
    / "reports"
    / "semantic_pipeline_audit"
    / "semantic_pair_matrix_2026-07-01.csv"
)
DEFAULT_CLUSTER_REGISTRY = (
    REPO_ROOT
    / "reports"
    / "semantic_pipeline_audit"
    / "semantic_cluster_registry_2026-07-01.json"
)
DEFAULT_GENERIC_OWNERSHIP = (
    REPO_ROOT / "configs" / "field_registry" / "generic_field_ownership.yaml"
)
DEFAULT_ASSAY_METADATA_REGISTRY = (
    REPO_ROOT / "configs" / "field_registry" / "assay_metadata_semantic_registry.yaml"
)
DEFAULT_PARTIAL_IDENTIFIER_REGISTRY = (
    REPO_ROOT / "configs" / "field_registry" / "partial_identifier_owner_roles.yaml"
)
ALLOWED_WEAK_DECISIONS = frozenset(
    {"promotable_candidate", "source_owned_same_name", "permanent_weak_inventory"}
)


@dataclass(frozen=True, slots=True)
class GovernanceFinding:
    """One semantic governance policy finding."""

    kind: str
    subject: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "subject": self.subject, "message": self.message}


def _load_yaml(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    if root is not None:
        from scripts.engineering.common.repo_paths import resolve_output_path

        path = resolve_output_path(path, root=root)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Expected YAML mapping in {path}")


def _load_json(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    if root is not None:
        from scripts.engineering.common.repo_paths import resolve_output_path

        path = resolve_output_path(path, root=root)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Expected JSON mapping in {path}")


def _load_rows(path: Path, *, root: Path | None = None) -> tuple[dict[str, str], ...]:
    if root is not None:
        from scripts.engineering.common.repo_paths import resolve_output_path

        path = resolve_output_path(path, root=root)
    with path.open(encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle))


def _cluster_lookup(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    clusters = payload.get("clusters", [])
    if not isinstance(clusters, list):
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        cluster_id = cluster.get("cluster_id")
        if isinstance(cluster_id, str):
            lookup[cluster_id] = cluster
    return lookup


def _cluster_counts(rows: tuple[dict[str, str], ...], status: str) -> Counter[str]:
    return Counter(
        row["Cluster ID"] for row in rows if row.get("Semantic Status") == status
    )


def _non_empty_str(mapping: dict[str, Any], key: str) -> bool:
    value = mapping.get(key)
    return isinstance(value, str) and bool(value.strip())


def _dedicated_authority_findings(
    review_payload: dict[str, Any],
    *,
    assay_payload: dict[str, Any],
    partial_payload: dict[str, Any],
) -> list[GovernanceFinding]:
    """Ensure review inventory cannot drift from dedicated authority registries."""
    findings: list[GovernanceFinding] = []
    review_partial = {
        str(entry.get("cluster_id")): entry
        for entry in review_payload.get("partial_cluster_policies", [])
        if isinstance(entry, dict) and entry.get("cluster_id")
    }
    review_weak = {
        str(entry.get("cluster_id")): entry
        for entry in review_payload.get("weak_cluster_decisions", [])
        if isinstance(entry, dict) and entry.get("cluster_id")
    }
    required_keys = {
        "owner",
        "business_owner_role",
        "composite_role",
        "lineage_role",
        "promotion_policy",
        "authority_scope",
        "rationale",
    }
    projected_role_keys = {
        "owner",
        "business_owner_role",
        "composite_role",
        "lineage_role",
        "promotion_policy",
    }
    for section, payload, review_lookup in (
        ("assay_metadata", assay_payload.get("fields"), review_weak),
        ("partial_identifier", partial_payload.get("clusters"), review_partial),
    ):
        if not isinstance(payload, list):
            findings.append(
                GovernanceFinding(
                    kind="invalid_dedicated_authority_registry",
                    subject=section,
                    message=f"{section} authority registry must define a list",
                )
            )
            continue
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            cluster_id = str(entry.get("cluster_id") or "<unknown>")
            review_entry = review_lookup.get(cluster_id)
            if review_entry is None:
                findings.append(
                    GovernanceFinding(
                        kind="missing_dedicated_authority_projection",
                        subject=cluster_id,
                        message=f"{cluster_id} is missing from semantic review policy",
                    )
                )
                continue
            for key in required_keys:
                if not _non_empty_str(entry, key):
                    findings.append(
                        GovernanceFinding(
                            kind="missing_dedicated_authority_metadata",
                            subject=cluster_id,
                            message=f"{cluster_id} dedicated authority is missing {key}",
                        )
                    )
                elif key in projected_role_keys and review_entry.get(key) != entry.get(
                    key
                ):
                    findings.append(
                        GovernanceFinding(
                            kind="dedicated_authority_drift",
                            subject=cluster_id,
                            message=f"{cluster_id} review projection differs for {key}",
                        )
                    )
    return findings


def _required_evidence_findings(
    payload: dict[str, Any],
) -> list[GovernanceFinding]:
    findings: list[GovernanceFinding] = []
    requirements = payload.get("promotion_requirements")
    if not isinstance(requirements, dict):
        return [
            GovernanceFinding(
                kind="missing_promotion_requirements",
                subject="promotion_requirements",
                message="semantic audit review registry must define promotion_requirements",
            )
        ]

    expected = {
        "PARTIAL": {
            "business_owner_identity",
            "composite_role",
            "join_semantics",
            "lineage_role",
            "normalization_parity",
            "dq_parity",
            "gold_contract_compatibility",
        },
        "WEAK": {
            "canonical_owner",
            "ontology_meaning",
            "join_usage_proof",
            "lineage_role",
            "normalization_parity",
            "dq_parity",
            "gold_contract_compatibility",
        },
        "CONFLICTING": {
            "explicit_owner_registry",
            "non_aliasability_rationale",
        },
    }
    for status, required in expected.items():
        entry = requirements.get(status)
        if not isinstance(entry, dict):
            findings.append(
                GovernanceFinding(
                    kind="missing_status_promotion_requirements",
                    subject=status,
                    message=f"promotion_requirements must define {status}",
                )
            )
            continue
        evidence = entry.get("required_evidence")
        outcomes = entry.get("allowed_outcomes")
        if not isinstance(evidence, list) or not required <= {
            str(item) for item in evidence if isinstance(item, str)
        }:
            findings.append(
                GovernanceFinding(
                    kind="incomplete_required_evidence",
                    subject=status,
                    message=f"{status} required_evidence is incomplete",
                )
            )
        if not isinstance(outcomes, list) or not outcomes:
            findings.append(
                GovernanceFinding(
                    kind="missing_allowed_outcomes",
                    subject=status,
                    message=f"{status} promotion requirements must define allowed_outcomes",
                )
            )
        if not _non_empty_str(entry, "enforcement_owner"):
            findings.append(
                GovernanceFinding(
                    kind="missing_enforcement_owner",
                    subject=status,
                    message=f"{status} promotion requirements must define enforcement_owner",
                )
            )
    return findings


def _partial_policy_findings(
    payload: dict[str, Any],
    *,
    rows: tuple[dict[str, str], ...],
    cluster_lookup: dict[str, dict[str, Any]],
) -> list[GovernanceFinding]:
    findings: list[GovernanceFinding] = []
    expected = set(_cluster_counts(rows, "PARTIAL"))
    entries = payload.get("partial_cluster_policies", [])
    if not isinstance(entries, list):
        return [
            GovernanceFinding(
                kind="missing_partial_cluster_policies",
                subject="partial_cluster_policies",
                message="semantic audit review registry must define partial_cluster_policies",
            )
        ]
    actual: set[str] = set()
    required_keys = {
        "cluster_id",
        "canonical_field",
        "owner",
        "business_owner_role",
        "composite_role",
        "lineage_role",
        "promotion_policy",
        "rationale",
    }
    for entry in entries:
        if not isinstance(entry, dict):
            findings.append(
                GovernanceFinding(
                    kind="invalid_partial_cluster_policy",
                    subject="partial_cluster_policies",
                    message="partial cluster policy entries must be mappings",
                )
            )
            continue
        cluster_id = str(entry.get("cluster_id") or "<unknown>")
        actual.add(cluster_id)
        for key in required_keys:
            if not _non_empty_str(entry, key):
                findings.append(
                    GovernanceFinding(
                        kind="missing_partial_cluster_policy_metadata",
                        subject=cluster_id,
                        message=f"partial cluster policy for {cluster_id} is missing {key}",
                    )
                )
        cluster = cluster_lookup.get(cluster_id)
        if cluster is None:
            findings.append(
                GovernanceFinding(
                    kind="stale_partial_cluster_policy",
                    subject=cluster_id,
                    message=f"partial cluster policy for {cluster_id} does not match a current cluster",
                )
            )
            continue
        canonical_field = entry.get("canonical_field")
        if canonical_field != cluster.get("canonical_field"):
            findings.append(
                GovernanceFinding(
                    kind="canonical_field_mismatch",
                    subject=cluster_id,
                    message=(
                        f"partial cluster policy for {cluster_id} declares canonical_field "
                        f"{canonical_field!r} but cluster registry reports "
                        f"{cluster.get('canonical_field')!r}"
                    ),
                )
            )
    for missing in sorted(expected - actual):
        findings.append(
            GovernanceFinding(
                kind="missing_partial_cluster_policy",
                subject=missing,
                message=f"PARTIAL cluster {missing} is missing ownership policy metadata",
            )
        )
    for stale in sorted(actual - expected):
        findings.append(
            GovernanceFinding(
                kind="stale_partial_cluster_policy",
                subject=stale,
                message=f"partial cluster policy {stale} does not map to a current PARTIAL cluster",
            )
        )
    return findings


def _string_id_set(policy: dict[str, Any], key: str) -> set[str]:
    """Extract a set of string cluster ids from a policy list field."""
    return {
        str(cluster_id)
        for cluster_id in policy.get(key, [])
        if isinstance(cluster_id, str)
    }


def _weak_policy_sets(
    policy: dict[str, Any],
) -> tuple[set[str], set[str], set[str], tuple[str, ...]]:
    """Return tracked, role-governed, explicit-contract sets and required metadata."""
    tracked = _string_id_set(policy, "tracked_cluster_ids")
    role_governed = _string_id_set(policy, "role_governed_cluster_ids")
    explicit_contract = _string_id_set(policy, "explicit_contract_cluster_ids")
    required_tracked_metadata = tuple(
        str(key)
        for key in policy.get("required_tracked_decision_metadata", [])
        if isinstance(key, str)
    )
    return tracked, role_governed, explicit_contract, required_tracked_metadata


def _weak_policy_stale_findings(
    *,
    counts: dict[str, int],
    tracked_clusters: set[str],
    role_governed_clusters: set[str],
    explicit_contract_clusters: set[str],
) -> list[GovernanceFinding]:
    """Findings for policy ids that do not align with current WEAK clusters."""
    findings: list[GovernanceFinding] = []
    for stale in sorted(tracked_clusters - set(counts)):
        findings.append(
            GovernanceFinding(
                kind="stale_tracked_weak_cluster_policy",
                subject=stale,
                message=(
                    f"weak_cluster_policy tracks {stale} but it is not a current WEAK cluster"
                ),
            )
        )
    for stale in sorted(role_governed_clusters - tracked_clusters):
        findings.append(
            GovernanceFinding(
                kind="untracked_role_governed_weak_cluster",
                subject=stale,
                message=(
                    f"weak_cluster_policy marks {stale} as role-governed but does not "
                    "include it in tracked_cluster_ids"
                ),
            )
        )
    for stale in sorted(explicit_contract_clusters - tracked_clusters):
        findings.append(
            GovernanceFinding(
                kind="untracked_explicit_contract_weak_cluster",
                subject=stale,
                message=(
                    f"weak_cluster_policy marks {stale} as explicit-contract but does not "
                    "include it in tracked_cluster_ids"
                ),
            )
        )
    return findings


def _weak_decision_entry_findings(
    entry: dict[str, Any],
    *,
    tracked_clusters: set[str],
    role_governed_clusters: set[str],
    explicit_contract_clusters: set[str],
    required_tracked_metadata: tuple[str, ...],
) -> list[GovernanceFinding]:
    """Validate one weak_cluster_decisions entry."""
    findings: list[GovernanceFinding] = []
    cluster_id = str(entry.get("cluster_id") or "<unknown>")
    for key in ("cluster_id", "field_name", "decision", "owner", "rationale"):
        if not _non_empty_str(entry, key):
            findings.append(
                GovernanceFinding(
                    kind="missing_weak_cluster_decision_metadata",
                    subject=cluster_id,
                    message=f"weak cluster decision for {cluster_id} is missing {key}",
                )
            )
    decision = entry.get("decision")
    if isinstance(decision, str) and decision not in ALLOWED_WEAK_DECISIONS:
        findings.append(
            GovernanceFinding(
                kind="invalid_weak_cluster_decision_value",
                subject=cluster_id,
                message=(
                    f"weak cluster decision for {cluster_id} uses unsupported "
                    f"decision {decision!r}"
                ),
            )
        )
    if cluster_id in tracked_clusters:
        for key in required_tracked_metadata:
            if not _non_empty_str(entry, key):
                findings.append(
                    GovernanceFinding(
                        kind="missing_tracked_weak_cluster_metadata",
                        subject=cluster_id,
                        message=(
                            f"tracked weak cluster decision for {cluster_id} is missing {key}"
                        ),
                    )
                )
    semantic_scope = str(entry.get("semantic_scope") or "")
    if cluster_id in role_governed_clusters and not semantic_scope.startswith(
        "role_governed_"
    ):
        findings.append(
            GovernanceFinding(
                kind="invalid_role_governed_weak_scope",
                subject=cluster_id,
                message=(
                    f"role-governed weak cluster {cluster_id} must use a "
                    f"role_governed_* semantic_scope, got {semantic_scope!r}"
                ),
            )
        )
    if (
        cluster_id in explicit_contract_clusters
        and semantic_scope != "explicit_source_owned_assay_contract"
    ):
        findings.append(
            GovernanceFinding(
                kind="invalid_explicit_contract_weak_scope",
                subject=cluster_id,
                message=(
                    f"explicit-contract weak cluster {cluster_id} must use "
                    "'explicit_source_owned_assay_contract' semantic_scope"
                ),
            )
        )
    return findings


def _weak_decision_coverage_findings(
    *,
    expected: set[str],
    actual: set[str],
    counts: dict[str, int],
) -> list[GovernanceFinding]:
    """Missing expected decisions and stale decisions not in current WEAK set."""
    findings: list[GovernanceFinding] = []
    for missing in sorted(expected - actual):
        findings.append(
            GovernanceFinding(
                kind="missing_weak_cluster_decision",
                subject=missing,
                message=(
                    f"WEAK cluster {missing} meets the review threshold and is missing "
                    "an explicit owner decision"
                ),
            )
        )
    for stale in sorted(actual - set(counts)):
        findings.append(
            GovernanceFinding(
                kind="stale_weak_cluster_decision",
                subject=stale,
                message=(
                    f"weak cluster decision {stale} does not map to a current WEAK cluster"
                ),
            )
        )
    return findings


def _weak_decision_findings(
    payload: dict[str, Any],
    *,
    rows: tuple[dict[str, str], ...],
) -> list[GovernanceFinding]:
    findings: list[GovernanceFinding] = []
    policy = payload.get("weak_cluster_policy", {})
    if not isinstance(policy, dict):
        return [
            GovernanceFinding(
                kind="missing_weak_cluster_policy",
                subject="weak_cluster_policy",
                message="semantic audit review registry must define weak_cluster_policy",
            )
        ]
    threshold = policy.get("weak_decision_min_rows")
    if not isinstance(threshold, int) or threshold < 1:
        findings.append(
            GovernanceFinding(
                kind="invalid_weak_cluster_policy_threshold",
                subject="weak_cluster_policy",
                message=(
                    "weak_cluster_policy.weak_decision_min_rows must be a positive integer"
                ),
            )
        )
        threshold = 1
    counts = _cluster_counts(rows, "WEAK")
    expected = {
        cluster_id for cluster_id, count in counts.items() if count >= threshold
    }
    (
        tracked_clusters,
        role_governed_clusters,
        explicit_contract_clusters,
        required_tracked_metadata,
    ) = _weak_policy_sets(policy)
    findings.extend(
        _weak_policy_stale_findings(
            counts=counts,
            tracked_clusters=tracked_clusters,
            role_governed_clusters=role_governed_clusters,
            explicit_contract_clusters=explicit_contract_clusters,
        )
    )
    expected |= tracked_clusters
    entries = payload.get("weak_cluster_decisions", [])
    if not isinstance(entries, list):
        return findings + [
            GovernanceFinding(
                kind="missing_weak_cluster_decisions",
                subject="weak_cluster_decisions",
                message="semantic audit review registry must define weak_cluster_decisions",
            )
        ]
    actual: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            findings.append(
                GovernanceFinding(
                    kind="invalid_weak_cluster_decision",
                    subject="weak_cluster_decisions",
                    message="weak cluster decisions must be mappings",
                )
            )
            continue
        cluster_id = str(entry.get("cluster_id") or "<unknown>")
        actual.add(cluster_id)
        findings.extend(
            _weak_decision_entry_findings(
                entry,
                tracked_clusters=tracked_clusters,
                role_governed_clusters=role_governed_clusters,
                explicit_contract_clusters=explicit_contract_clusters,
                required_tracked_metadata=required_tracked_metadata,
            )
        )
    findings.extend(
        _weak_decision_coverage_findings(
            expected=expected, actual=actual, counts=counts
        )
    )
    return findings


def _generic_collision_findings(
    payload: dict[str, Any],
    *,
    rows: tuple[dict[str, str], ...],
    generic_ownership: dict[str, Any],
) -> list[GovernanceFinding]:
    findings: list[GovernanceFinding] = []
    expected = set(_cluster_counts(rows, "CONFLICTING"))
    entries = payload.get("generic_collision_policies", [])
    if not isinstance(entries, list):
        return [
            GovernanceFinding(
                kind="missing_generic_collision_policies",
                subject="generic_collision_policies",
                message="semantic audit review registry must define generic_collision_policies",
            )
        ]
    denied_terms = {
        str(term)
        for term in generic_ownership.get("denied_terms", [])
        if isinstance(term, str)
    }
    actual: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            findings.append(
                GovernanceFinding(
                    kind="invalid_generic_collision_policy",
                    subject="generic_collision_policies",
                    message="generic collision policies must be mappings",
                )
            )
            continue
        cluster_id = str(entry.get("cluster_id") or "<unknown>")
        actual.add(cluster_id)
        for key in (
            "cluster_id",
            "lexical_field",
            "owner",
            "semantic_scope",
            "promotion_policy",
            "rationale",
        ):
            if not _non_empty_str(entry, key):
                findings.append(
                    GovernanceFinding(
                        kind="missing_generic_collision_policy_metadata",
                        subject=cluster_id,
                        message=f"generic collision policy for {cluster_id} is missing {key}",
                    )
                )
        lexical_field = entry.get("lexical_field")
        if isinstance(lexical_field, str) and lexical_field not in denied_terms:
            findings.append(
                GovernanceFinding(
                    kind="generic_collision_not_in_denied_terms",
                    subject=cluster_id,
                    message=(
                        f"generic collision policy for {cluster_id} uses lexical_field "
                        f"{lexical_field!r} which is not governed by generic_field_ownership.yaml"
                    ),
                )
            )
    for missing in sorted(expected - actual):
        findings.append(
            GovernanceFinding(
                kind="missing_generic_collision_policy",
                subject=missing,
                message=f"CONFLICTING cluster {missing} is missing explicit ownership policy",
            )
        )
    for stale in sorted(actual - expected):
        findings.append(
            GovernanceFinding(
                kind="stale_generic_collision_policy",
                subject=stale,
                message=f"generic collision policy {stale} does not map to a current CONFLICTING cluster",
            )
        )
    return findings


def _current_unknown_composite_fields(
    rows: tuple[dict[str, str], ...],
) -> set[tuple[str, str]]:
    fields: set[tuple[str, str]] = set()
    for row in rows:
        for side in ("A", "B"):
            pipeline = row.get(f"Pipeline {side}", "")
            field = row.get(f"Field {side}", "")
            field_type = row.get(f"Type {side}", "")
            if pipeline.startswith("composite_") and field_type == "unknown":
                fields.add((pipeline, field))
    return fields


def _typing_policy_findings(
    payload: dict[str, Any],
    *,
    rows: tuple[dict[str, str], ...],
) -> list[GovernanceFinding]:
    findings: list[GovernanceFinding] = []
    entries = payload.get("composite_unknown_typing_reviews", [])
    if not isinstance(entries, list):
        return [
            GovernanceFinding(
                kind="missing_composite_unknown_typing_reviews",
                subject="composite_unknown_typing_reviews",
                message="semantic audit review registry must define composite_unknown_typing_reviews",
            )
        ]
    actual = _current_unknown_composite_fields(rows)
    covered: set[tuple[str, str]] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            findings.append(
                GovernanceFinding(
                    kind="invalid_composite_unknown_typing_review",
                    subject="composite_unknown_typing_reviews",
                    message="composite unknown typing reviews must be mappings",
                )
            )
            continue
        review_id = str(entry.get("id") or "<unknown>")
        for key in ("id", "disposition", "schema_authority", "owner", "rationale"):
            if not _non_empty_str(entry, key):
                findings.append(
                    GovernanceFinding(
                        kind="missing_composite_unknown_typing_metadata",
                        subject=review_id,
                        message=f"composite unknown typing review {review_id} is missing {key}",
                    )
                )
        pipelines = entry.get("pipelines")
        fields = entry.get("fields")
        if not isinstance(pipelines, list) or not all(
            isinstance(item, str) and item.strip() for item in pipelines
        ):
            findings.append(
                GovernanceFinding(
                    kind="invalid_composite_unknown_typing_pipelines",
                    subject=review_id,
                    message=f"composite unknown typing review {review_id} must define pipelines list",
                )
            )
            continue
        if not isinstance(fields, list) or not all(
            isinstance(item, str) and item.strip() for item in fields
        ):
            findings.append(
                GovernanceFinding(
                    kind="invalid_composite_unknown_typing_fields",
                    subject=review_id,
                    message=f"composite unknown typing review {review_id} must define fields list",
                )
            )
            continue
        matched = False
        for pipeline in pipelines:
            for field in fields:
                pair = (pipeline, field)
                if pair in actual:
                    covered.add(pair)
                    matched = True
        if not matched:
            findings.append(
                GovernanceFinding(
                    kind="stale_composite_unknown_typing_review",
                    subject=review_id,
                    message=(
                        f"composite unknown typing review {review_id} does not cover "
                        "any current unknown composite schema field"
                    ),
                )
            )
    for missing in sorted(actual - covered):
        findings.append(
            GovernanceFinding(
                kind="missing_composite_unknown_typing_coverage",
                subject=f"{missing[0]}.{missing[1]}",
                message=(
                    f"composite unknown schema field {missing[0]}.{missing[1]} "
                    "is not covered by composite_unknown_typing_reviews"
                ),
            )
        )
    return findings


def validate_semantic_governance_policy(
    *,
    review_registry_path: Path = DEFAULT_REVIEW_REGISTRY,
    pair_matrix_path: Path = DEFAULT_PAIR_MATRIX,
    cluster_registry_path: Path = DEFAULT_CLUSTER_REGISTRY,
    generic_ownership_path: Path = DEFAULT_GENERIC_OWNERSHIP,
    assay_metadata_path: Path = DEFAULT_ASSAY_METADATA_REGISTRY,
    partial_identifier_path: Path = DEFAULT_PARTIAL_IDENTIFIER_REGISTRY,
    root: Path | None = None,
) -> tuple[GovernanceFinding, ...]:
    """Return semantic governance policy findings for the current repository."""
    payload = _load_yaml(review_registry_path, root=root)
    rows = _load_rows(pair_matrix_path, root=root)
    cluster_lookup = _cluster_lookup(_load_json(cluster_registry_path, root=root))
    generic_ownership = _load_yaml(generic_ownership_path, root=root)
    assay_metadata = _load_yaml(assay_metadata_path, root=root)
    partial_identifiers = _load_yaml(partial_identifier_path, root=root)

    findings: list[GovernanceFinding] = []
    findings.extend(
        _dedicated_authority_findings(
            payload,
            assay_payload=assay_metadata,
            partial_payload=partial_identifiers,
        )
    )
    findings.extend(_required_evidence_findings(payload))
    findings.extend(
        _partial_policy_findings(payload, rows=rows, cluster_lookup=cluster_lookup)
    )
    findings.extend(_weak_decision_findings(payload, rows=rows))
    findings.extend(
        _generic_collision_findings(
            payload,
            rows=rows,
            generic_ownership=generic_ownership,
        )
    )
    findings.extend(_typing_policy_findings(payload, rows=rows))
    return tuple(findings)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate semantic governance policy for residual ETL semantic debt.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail with a non-zero exit code when findings are present",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable validation output",
    )
    parser.add_argument(
        "--review-registry-path",
        type=Path,
        default=DEFAULT_REVIEW_REGISTRY,
        help="semantic audit review registry YAML",
    )
    parser.add_argument(
        "--pair-matrix-path",
        type=Path,
        default=DEFAULT_PAIR_MATRIX,
        help="semantic pair matrix CSV",
    )
    parser.add_argument(
        "--cluster-registry-path",
        type=Path,
        default=DEFAULT_CLUSTER_REGISTRY,
        help="semantic cluster registry JSON",
    )
    parser.add_argument(
        "--generic-ownership-path",
        type=Path,
        default=DEFAULT_GENERIC_OWNERSHIP,
        help="generic field ownership registry YAML",
    )
    parser.add_argument(
        "--assay-metadata-path",
        type=Path,
        default=DEFAULT_ASSAY_METADATA_REGISTRY,
        help="dedicated assay metadata semantic registry YAML",
    )
    parser.add_argument(
        "--partial-identifier-path",
        type=Path,
        default=DEFAULT_PARTIAL_IDENTIFIER_REGISTRY,
        help="dedicated PARTIAL identifier owner-role registry YAML",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    from scripts.engineering.common.repo_paths import REPO_ROOT

    parser = _build_parser()
    args = parser.parse_args(argv)
    findings = validate_semantic_governance_policy(
        review_registry_path=args.review_registry_path,
        pair_matrix_path=args.pair_matrix_path,
        cluster_registry_path=args.cluster_registry_path,
        generic_ownership_path=args.generic_ownership_path,
        assay_metadata_path=args.assay_metadata_path,
        partial_identifier_path=args.partial_identifier_path,
        root=REPO_ROOT,
    )
    if args.json:
        print(
            json.dumps(
                {
                    "ok": not findings,
                    "finding_count": len(findings),
                    "findings": [finding.as_dict() for finding in findings],
                },
                indent=2,
                sort_keys=True,
            )
        )
    elif findings:
        print("[semantic-governance-policy] validation failed")
        for finding in findings:
            print(f"- {finding.message}")
    else:
        print("[semantic-governance-policy] ok")
    return 1 if args.check and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
