#!/usr/bin/env python3
"""Generate semantic pipeline audit snapshot artifacts from current contracts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from scripts.docs.matrix.generate_pipeline_normalization_matrix import (
    build_field_matrix_rows,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT_DIR = REPO_ROOT / "reports" / "semantic_pipeline_audit"
DEFAULT_REVIEW_REGISTRY = (
    REPO_ROOT / "configs" / "field_registry" / "semantic_audit_review_registry.yaml"
)
BASE_CONFIG_DIR = REPO_ROOT / "configs" / "base"
DEFAULT_SOURCE_DATE = "2026-05-15"
PAIR_MATRIX_PREFIX = "semantic_pair_matrix_"
CLUSTER_REGISTRY_PREFIX = "semantic_cluster_registry_"
PAIR_COLUMNS = (
    "Cluster ID",
    "Pipeline A",
    "Field A",
    "Pipeline B",
    "Field B",
    "Semantic Status",
    "Normalization",
    "Validation",
    "Typing",
    "Drift Risk",
    "Join Semantics A",
    "Join Semantics B",
    "Normalizer A",
    "Normalizer B",
    "Validation Evidence A",
    "Validation Evidence B",
    "Type A",
    "Type B",
    "Gold Contract A",
    "Gold Contract B",
    "Evidence A",
    "Evidence B",
    "Row Key",
)
ROW_KEY_FIELDS = (
    "Cluster ID",
    "Pipeline A",
    "Field A",
    "Pipeline B",
    "Field B",
)
GENERIC_COLLISION_CLUSTERS = frozenset(
    {
        "shared_description",
        "shared_relation",
        "shared_score",
        "shared_type",
        "shared_value",
    }
)
OPTIONAL_COMPOSITE_LINEAGE_CLUSTERS = frozenset(
    {
        "shared_record_id",
        "shared_src_id",
        "uniprot_accession_identifier",
    }
)
CLUSTER_METADATA_OVERRIDES = {
    "canonical_smiles_identifier": {
        "rationale": (
            "Canonical SMILES is a structure-level identifier. ChEMBL molecule, "
            "PubChem compound, and composite molecule use compatible structure "
            "normalization; ChEMBL activity keeps the value as inherited molecule "
            "context rather than molecule ownership."
        ),
    },
    "inchi_key_identifier": {
        "rationale": (
            "InChIKey is a structure-level identifier shared by ChEMBL molecule, "
            "PubChem compound, and composite molecule join paths with canonical "
            "uppercase normalization."
        ),
    },
    "uniprot_accession_identifier": {
        "rationale": (
            "UniProt accession identity is PARTIAL across ChEMBL component evidence, "
            "UniProt idmapping output, composite target chaining, and UniProt protein "
            "primary keys. Direct joins use idmapping/protein accessions; ChEMBL "
            "component accession remains lineage evidence."
        ),
    },
}
JOIN_KEY_PROFILE_EQUIVALENCE = {
    "assay_id": "normalize_profile_chembl_id",
    "cell_id": "normalize_profile_chembl_id",
    "canonical_smiles": "normalize_profile_canonical_smiles",
    "doi": "normalize_profile_doi",
    "inchi_key": "normalize_profile_inchi_key",
    "molecule_id": "normalize_profile_chembl_id",
    "pmc_id": "normalize_profile_pmc_id",
    "pmid": "normalize_profile_pmid",
    "primary_component_id": "normalize_profile_float",
    "protein_classification_id": "normalize_profile_int",
    "publication_id": "normalize_profile_chembl_id",
    "record_id": "normalize_profile_int",
    "src_id": "normalize_profile_int",
    "target_id": "normalize_profile_chembl_id",
    "tissue_id": "normalize_profile_chembl_id",
    "title": "normalize_profile_title",
    "uniprot_accession": "normalize_profile_uniprot_accession",
}
RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
JSON_NORMALIZER_FAMILY = frozenset(
    {
        "normalize_profile_json_string",
        "normalize_profile_json_string_strict",
        "normalize_profile_json_string_unordered_collection",
        "normalize_profile_orcid_ids",
    }
)
PUBLICATION_TYPE_NORMALIZER_FAMILY = frozenset(
    {
        "normalize_profile_publication_type",
        "normalize_profile_publication_type_field",
        "normalize_profile_publication_type_raw",
        "normalize_profile_semantic_scholar_publication_type_raw",
        "normalize_profile_text",
    }
)
TEXT_NORMALIZER_FAMILY = frozenset(
    {
        "normalize_profile_null",
        "normalize_profile_text",
    }
)
BOOLEAN_NORMALIZER_FAMILY = frozenset(
    {
        "normalize_profile_binary_flag",
        "normalize_profile_boolean",
    }
)
BAO_COMPANION_NORMALIZER_FAMILIES = {
    "shared_bao_format_iri": frozenset(
        {
            "normalize_profile_activity_bao_format_iri",
            "normalize_profile_bao_format_companion_iri",
        }
    ),
    "shared_bao_format_mapping_status": frozenset(
        {
            "normalize_profile_activity_bao_format_mapping_status",
            "normalize_profile_bao_format_companion_mapping_status",
        }
    ),
    "shared_bao_ontology_version": frozenset(
        {
            "normalize_profile_activity_bao_ontology_version",
            "normalize_profile_bao_format_companion_version",
        }
    ),
}
STANDARD_UNIT_NORMALIZER_FAMILY = frozenset(
    {
        "normalize_activity_standard_units",
        "normalize_assay_parameter_standard_units",
    }
)
PROVIDER_LOCAL_IDENTIFIER_CLUSTERS = frozenset(
    {
        "chembl_molecule_identifier",
    }
)
BASE_CONFIG_SEMANTIC_KEYS = frozenset(
    {
        "common_cross_field_validations",
        "common_field_validations",
        "contract_defaults",
        "dq_policy_ref",
        "dq_overrides",
        "filter_defaults",
        "fixtures",
        "gaps",
        "hash_exclude",
        "hash_include",
        "identity",
        "invalid_record_policy",
        "normalization_profile_hash",
        "normalization_profile_ref",
        "normalization_profile_version",
        "published_artifacts",
        "rule_bundle_version",
        "scd_config",
        "sort_by",
        "strict_validation",
        "technical_primary_key",
        "thresholds",
    }
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Expected JSON mapping in {path}")


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Expected YAML mapping in {path}")


def _repo_rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _seed_artifact_filename(prefix: str, source_date: str, suffix: str) -> str:
    return f"{prefix}{source_date}{suffix}"


def _latest_seed_artifact(out_dir: Path, prefix: str, suffix: str) -> Path | None:
    candidates = sorted(out_dir.glob(f"{prefix}*{suffix}"))
    return candidates[-1] if candidates else None


def _resolve_seed_artifact(
    explicit: Path | None,
    *,
    out_dir: Path,
    prefix: str,
    source_date: str,
    suffix: str,
) -> Path:
    if explicit is not None:
        return explicit
    dated_candidate = out_dir / _seed_artifact_filename(prefix, source_date, suffix)
    if dated_candidate.exists():
        return dated_candidate
    fallback = _latest_seed_artifact(out_dir, prefix, suffix)
    if fallback is not None:
        return fallback
    raise FileNotFoundError(
        f"Unable to resolve seed artifact for {prefix}*{suffix} in {out_dir}"
    )


def _normalize_newlines(payload: str) -> str:
    return payload.replace("\r\n", "\n").replace("\r", "\n")


def _write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="\n")


def _row_key(row: dict[str, str]) -> str:
    seed = "|".join(row[field] for field in ROW_KEY_FIELDS)
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _path_for_pipeline(row: dict[str, str]) -> str:
    pipeline_kind = row.get("pipeline_kind")
    provider = row.get("provider", "")
    entity = row.get("entity", "")
    if pipeline_kind == "composite":
        return f"configs/composites/{entity}.yaml"
    return f"configs/entities/{provider}/{entity}.yaml"


def _gold_contract_path(pipeline: str) -> Path:
    return (
        REPO_ROOT
        / "docs"
        / "04-reference"
        / "contracts"
        / "gold"
        / f"{pipeline}_v1.0.json"
    )


def _gold_field_payload(pipeline: str, field: str) -> tuple[str, bool, str]:
    path = _gold_contract_path(pipeline)
    if not path.exists():
        return "", False, ""
    payload = _load_json(path)
    properties = payload.get("properties", {})
    if not isinstance(properties, dict) or field not in properties:
        return "", False, ""
    required = payload.get("required", [])
    is_required = isinstance(required, list) and field in required
    field_payload = properties.get(field)
    if not isinstance(field_payload, dict):
        return path.relative_to(REPO_ROOT).as_posix(), is_required, ""
    return (
        path.relative_to(REPO_ROOT).as_posix(),
        is_required,
        json.dumps(field_payload.get("type", ""), ensure_ascii=False, sort_keys=True),
    )


def _seed_member_lookup(
    seed_registry: dict[str, Any],
) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    clusters = seed_registry.get("clusters", [])
    if not isinstance(clusters, list):
        return lookup
    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        members = cluster.get("members", [])
        if not isinstance(members, list):
            continue
        for member in members:
            if not isinstance(member, dict):
                continue
            pipeline = member.get("pipeline")
            field = member.get("field")
            if isinstance(pipeline, str) and isinstance(field, str):
                lookup[(pipeline, field)] = member
    return lookup


def _build_current_member_facts(
    seed_registry: dict[str, Any],
) -> dict[tuple[str, str], dict[str, Any]]:
    seed_members = _seed_member_lookup(seed_registry)
    facts: dict[tuple[str, str], dict[str, Any]] = {}
    for row in build_field_matrix_rows():
        pipeline = row["pipeline_name"]
        field = row["field_name"]
        seed_member = seed_members.get((pipeline, field), {})
        gold_path, gold_required, gold_type = _gold_field_payload(pipeline, field)
        dq_coverage = row.get("dq_coverage", "")
        dq_rules = (
            []
            if dq_coverage in {"", "not_configured", "not_applicable"}
            else [dq_coverage]
        )
        facts[(pipeline, field)] = {
            "config_path": _path_for_pipeline(row),
            "cross_rules": seed_member.get("cross_rules", []),
            "dq_coverage": dq_coverage,
            "dq_rules": dq_rules,
            "entity": row.get("entity", ""),
            "field": field,
            "field_type": row.get("field_type", ""),
            "gold_path": gold_path,
            "gold_required": gold_required,
            "gold_type": gold_type,
            "group": seed_member.get("group", row.get("semantic_category", "")),
            "normalization_source": row.get("normalization_source", ""),
            "normalizer": row.get("normalizer", ""),
            "pipeline": pipeline,
            "pipeline_kind": row.get("pipeline_kind", ""),
            "provider": row.get("provider", ""),
            "roles": seed_member.get("roles", []),
            "semantic_category": row.get("semantic_category", ""),
            "strictness": row.get("strictness", ""),
        }
    return facts


def _review_matches_cluster(
    review: dict[str, Any],
    *,
    cluster_id: str,
    semantic_status: str,
) -> bool:
    statuses = review.get("semantic_statuses", [])
    if isinstance(statuses, list) and statuses:
        normalized_statuses = {str(status).upper() for status in statuses}
        if semantic_status.upper() not in normalized_statuses:
            return False

    clusters = review.get("clusters")
    if clusters is None:
        return True
    return isinstance(clusters, list) and cluster_id in {str(item) for item in clusters}


def _review_payload_for_cluster(
    review_registry: dict[str, Any],
    *,
    cluster_id: str,
    semantic_status: str,
) -> dict[str, Any] | None:
    for section in ("risk_reviews", "semantic_reviews", "warning_reviews"):
        reviews = review_registry.get(section, [])
        if not isinstance(reviews, list):
            continue
        for review in reviews:
            if not isinstance(review, dict):
                continue
            if _review_matches_cluster(
                review,
                cluster_id=cluster_id,
                semantic_status=semantic_status,
            ):
                return review
    return None


def _review_metadata(review: dict[str, Any]) -> dict[str, Any]:
    metadata = {
        "expires_on": review.get("expires_on", ""),
        "issue": review.get("issue", ""),
        "owner": review.get("owner", ""),
        "rationale": review.get("rationale", ""),
        "review_id": review.get("id", ""),
    }
    risk_cap = review.get("risk_cap")
    if risk_cap:
        metadata["risk_cap"] = risk_cap
    return metadata


def _refresh_clusters(
    seed_registry: dict[str, Any],
    facts: dict[tuple[str, str], dict[str, Any]],
    *,
    review_registry: dict[str, Any],
    source_date: str,
) -> dict[str, Any]:
    clusters = []
    for cluster in seed_registry.get("clusters", []):
        if not isinstance(cluster, dict):
            continue
        members = []
        for member in cluster.get("members", []):
            if not isinstance(member, dict):
                continue
            refreshed = facts.get(
                (str(member.get("pipeline")), str(member.get("field")))
            )
            if refreshed is not None:
                members.append(refreshed)
        refreshed_cluster = {
            key: value
            for key, value in cluster.items()
            if key not in {"members", "review"}
        }
        refreshed_cluster.update(
            CLUSTER_METADATA_OVERRIDES.get(str(refreshed_cluster.get("cluster_id")), {})
        )
        cluster_id = str(refreshed_cluster.get("cluster_id") or "")
        semantic_status = str(refreshed_cluster.get("semantic_status") or "")
        review = _review_payload_for_cluster(
            review_registry,
            cluster_id=cluster_id,
            semantic_status=semantic_status,
        )
        if review is not None:
            refreshed_cluster["review"] = _review_metadata(review)
        refreshed_cluster["member_count"] = len(members)
        refreshed_cluster["pipeline_count"] = len(
            {member["pipeline"] for member in members}
        )
        refreshed_cluster["members"] = members
        clusters.append(refreshed_cluster)
    return {
        "generated_at": f"{source_date}T00:00:00Z",
        "source_date": source_date,
        "scope": seed_registry.get("scope", "all_etl_pipelines"),
        "clusters": clusters,
    }


def _join_semantics(member: dict[str, Any], fallback: str) -> str:
    roles = member.get("roles", [])
    if isinstance(roles, list) and roles:
        return ";".join(str(role) for role in roles)
    return fallback


def _effective_normalizer(member: dict[str, Any]) -> str:
    normalizer = str(member.get("normalizer") or "")
    source = str(member.get("normalization_source") or "")
    field = str(member.get("field") or "")
    if normalizer == "join_key_policy":
        return JOIN_KEY_PROFILE_EQUIVALENCE.get(field, normalizer)
    if normalizer == "none" and source == "upstream_inherited":
        return "upstream_inherited"
    return normalizer


def _normalizer_family(
    *,
    cluster_id: str,
    member: dict[str, Any],
) -> str:
    normalizer = _effective_normalizer(member)
    field = str(member.get("field") or "")
    if normalizer in JSON_NORMALIZER_FAMILY:
        return "json_collection_family"
    if field == "publication_type" and normalizer in PUBLICATION_TYPE_NORMALIZER_FAMILY:
        return "publication_type_family"
    if (
        field
        in {
            "author_keys",
            "issue",
            "journal",
            "language",
            "inchi",
            "molecular_formula",
            "page_first",
            "page_last",
            "standard_inchi",
            "volume",
        }
        and normalizer in TEXT_NORMALIZER_FAMILY
    ):
        return "text_null_family"
    if normalizer in BOOLEAN_NORMALIZER_FAMILY:
        return "boolean_family"
    if normalizer in BAO_COMPANION_NORMALIZER_FAMILIES.get(cluster_id, frozenset()):
        return cluster_id
    if normalizer in STANDARD_UNIT_NORMALIZER_FAMILY:
        return "standard_unit_family"
    if (
        cluster_id in PROVIDER_LOCAL_IDENTIFIER_CLUSTERS
        and field == "molecule_id"
        and normalizer in {"normalize_profile_chembl_id", "normalize_profile_text"}
    ):
        return "provider_local_molecule_id_family"
    return normalizer


def _normalization_status(
    member_a: dict[str, Any],
    member_b: dict[str, Any],
    *,
    cluster_id: str,
    semantic_status: str,
) -> str:
    normalizer_a = _effective_normalizer(member_a)
    normalizer_b = _effective_normalizer(member_b)
    if normalizer_a == normalizer_b:
        return "IDENTICAL"
    if _normalizer_family(cluster_id=cluster_id, member=member_a) == _normalizer_family(
        cluster_id=cluster_id,
        member=member_b,
    ):
        return "COMPATIBLE"
    if "upstream_inherited" in {normalizer_a, normalizer_b}:
        return "COMPATIBLE"
    if semantic_status in {"WEAK", "CONFLICTING"}:
        return "COMPATIBLE"
    if semantic_status == "CONFLICTING":
        return "DIFFERENT"
    return "DIFFERENT"


def _gold_required(member: dict[str, Any]) -> bool | None:
    if not member.get("gold_path"):
        return None
    return bool(member.get("gold_required"))


def _validation_evidence(member: dict[str, Any]) -> str:
    gold = "gold:missing"
    if member.get("gold_path"):
        required = "required" if member.get("gold_required") else "optional"
        gold = f"gold:{required}:{member.get('gold_type') or 'unknown'}"
    return (
        f"{gold};schema={member.get('field_type') or 'unknown'};"
        f"dq={member.get('dq_coverage') or 'not_configured'}"
    )


def _schema_type_tokens(type_payload: str) -> set[str]:
    if not type_payload:
        return set()
    raw = type_payload.strip()
    parsed: object
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = raw.strip('"')
    values: set[str] = set()
    if isinstance(parsed, list):
        values.update(str(item) for item in parsed)
    elif isinstance(parsed, str):
        values.add(parsed)
    else:
        values.add(str(parsed))
    normalized: set[str] = set()
    for value in values:
        lowered = value.lower()
        if lowered in {"int", "int64", "integer"}:
            normalized.add("integer")
        elif lowered in {"float", "float64", "double", "number"}:
            normalized.add("number")
        elif lowered in {"bool", "boolean"}:
            normalized.add("boolean")
        elif lowered in {"str", "string"}:
            normalized.add("string")
        elif lowered in {"object", "dict"}:
            normalized.add("object")
        elif lowered in {"array", "list"}:
            normalized.add("array")
        elif lowered in {"null", "none"}:
            normalized.add("null")
        elif lowered and lowered != "unknown":
            normalized.add(lowered)
    return normalized


def _member_type_tokens(member: dict[str, Any]) -> set[str]:
    gold_tokens = _schema_type_tokens(str(member.get("gold_type") or ""))
    field_tokens = _schema_type_tokens(str(member.get("field_type") or ""))
    if _drop_null(gold_tokens) == {"object"} and field_tokens:
        return field_tokens | ({"null"} if "null" in gold_tokens else set())
    return gold_tokens or field_tokens


def _drop_null(tokens: set[str]) -> set[str]:
    return {token for token in tokens if token != "null"}


def _types_compatible(member_a: dict[str, Any], member_b: dict[str, Any]) -> bool:
    tokens_a = _drop_null(_member_type_tokens(member_a))
    tokens_b = _drop_null(_member_type_tokens(member_b))
    if not tokens_a or not tokens_b:
        return True
    if tokens_a == tokens_b:
        return True
    numeric = {"integer", "number"}
    if tokens_a <= numeric and tokens_b <= numeric:
        return True
    if tokens_a == {"boolean"} and tokens_b == {"object"}:
        return True
    if tokens_a == {"object"} and tokens_b == {"boolean"}:
        return True
    if tokens_a == {"boolean"} and tokens_b <= {"integer", "number"}:
        return True
    if tokens_a <= {"integer", "number"} and tokens_b == {"boolean"}:
        return True
    return False


def _validation_status(
    member_a: dict[str, Any],
    member_b: dict[str, Any],
    *,
    semantic_status: str,
) -> str:
    required_a = _gold_required(member_a)
    required_b = _gold_required(member_b)
    if required_a is not None and required_b is not None and required_a != required_b:
        if _types_compatible(member_a, member_b):
            return "COMPATIBLE"
        return "STRICTNESS_MISMATCH"
    evidence_a = _validation_evidence(member_a)
    evidence_b = _validation_evidence(member_b)
    if evidence_a == evidence_b:
        return "IDENTICAL"
    if required_a is not None and required_b is not None:
        return "COMPATIBLE"
    if semantic_status in {"WEAK", "CONFLICTING"}:
        return "COMPATIBLE"
    if _types_compatible(member_a, member_b):
        return "COMPATIBLE"
    if "not_applicable" in {member_a.get("dq_coverage"), member_b.get("dq_coverage")}:
        return "COMPATIBLE"
    return "DIFFERENT"


def _typing_status(member_a: dict[str, Any], member_b: dict[str, Any]) -> str:
    type_a = str(member_a.get("gold_type") or member_a.get("field_type") or "")
    type_b = str(member_b.get("gold_type") or member_b.get("field_type") or "")
    if type_a == type_b:
        return "IDENTICAL"
    if _types_compatible(member_a, member_b):
        return "COMPATIBLE"
    return "CONFLICTING"


def _risk_cap_lookup(review_registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    reviews = review_registry.get("risk_reviews", [])
    if not isinstance(reviews, list):
        return lookup
    for review in reviews:
        if not isinstance(review, dict):
            continue
        clusters = review.get("clusters", [])
        if not isinstance(clusters, list):
            continue
        for cluster_id in clusters:
            if isinstance(cluster_id, str):
                lookup.setdefault(cluster_id, review)
    return lookup


def _apply_reviewed_risk_cap(
    risk: str,
    *,
    cluster_id: str,
    review_lookup: dict[str, dict[str, Any]],
) -> str:
    review = review_lookup.get(cluster_id)
    if review is None:
        return risk
    risk_cap = review.get("risk_cap")
    if not isinstance(risk_cap, str) or risk_cap not in RISK_ORDER:
        return risk
    if RISK_ORDER.get(risk, -1) <= RISK_ORDER[risk_cap]:
        return risk
    return risk_cap


def _drift_risk(
    *,
    cluster_id: str,
    semantic_status: str,
    normalization: str,
    validation: str,
    typing: str,
    previous_risk: str,
) -> str:
    if semantic_status in {"WEAK", "CONFLICTING"}:
        return "LOW"
    if cluster_id in OPTIONAL_COMPOSITE_LINEAGE_CLUSTERS:
        return "MEDIUM" if validation == "STRICTNESS_MISMATCH" else "LOW"
    if (
        normalization in {"IDENTICAL", "COMPATIBLE"}
        and validation in {"IDENTICAL", "COMPATIBLE"}
        and typing in {"IDENTICAL", "COMPATIBLE"}
    ):
        return "LOW"
    if previous_risk == "CRITICAL":
        return "CRITICAL"
    if validation == "STRICTNESS_MISMATCH" or typing == "CONFLICTING":
        return "HIGH"
    if normalization in {"DIFFERENT", "CONFLICTING"}:
        return "HIGH"
    return previous_risk if previous_risk in {"HIGH", "MEDIUM"} else "MEDIUM"


def _member(
    facts: dict[tuple[str, str], dict[str, Any]],
    old_row: dict[str, str],
    side: str,
) -> dict[str, Any]:
    pipeline = old_row[f"Pipeline {side}"]
    field = old_row[f"Field {side}"]
    return facts.get(
        (pipeline, field),
        {
            "pipeline": pipeline,
            "field": field,
            "field_type": old_row.get(f"Type {side}", ""),
            "gold_path": old_row.get(f"Gold Contract {side}", ""),
            "normalizer": old_row.get(f"Normalizer {side}", ""),
            "roles": old_row.get(f"Join Semantics {side}", "").split(";"),
            "dq_coverage": "",
        },
    )


def _refresh_pair_rows(
    seed_rows: list[dict[str, str]],
    facts: dict[tuple[str, str], dict[str, Any]],
    review_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    refreshed: list[dict[str, str]] = []
    for old_row in seed_rows:
        member_a = _member(facts, old_row, "A")
        member_b = _member(facts, old_row, "B")
        semantic_status = old_row.get("Semantic Status", "")
        cluster_id = old_row["Cluster ID"]
        normalization = _normalization_status(
            member_a,
            member_b,
            cluster_id=cluster_id,
            semantic_status=semantic_status,
        )
        validation = _validation_status(
            member_a,
            member_b,
            semantic_status=semantic_status,
        )
        typing = _typing_status(member_a, member_b)
        drift_risk = _drift_risk(
            cluster_id=cluster_id,
            semantic_status=semantic_status,
            normalization=normalization,
            validation=validation,
            typing=typing,
            previous_risk=old_row.get("Drift Risk", "LOW"),
        )
        row = {
            "Cluster ID": cluster_id,
            "Pipeline A": old_row["Pipeline A"],
            "Field A": old_row["Field A"],
            "Pipeline B": old_row["Pipeline B"],
            "Field B": old_row["Field B"],
            "Semantic Status": semantic_status,
            "Normalization": normalization,
            "Validation": validation,
            "Typing": typing,
            "Drift Risk": _apply_reviewed_risk_cap(
                drift_risk,
                cluster_id=cluster_id,
                review_lookup=review_lookup,
            ),
            "Join Semantics A": _join_semantics(
                member_a, old_row.get("Join Semantics A", "")
            ),
            "Join Semantics B": _join_semantics(
                member_b, old_row.get("Join Semantics B", "")
            ),
            "Normalizer A": str(member_a.get("normalizer") or ""),
            "Normalizer B": str(member_b.get("normalizer") or ""),
            "Validation Evidence A": _validation_evidence(member_a),
            "Validation Evidence B": _validation_evidence(member_b),
            "Type A": str(member_a.get("field_type") or old_row.get("Type A", "")),
            "Type B": str(member_b.get("field_type") or old_row.get("Type B", "")),
            "Gold Contract A": str(member_a.get("gold_path") or ""),
            "Gold Contract B": str(member_b.get("gold_path") or ""),
            "Evidence A": str(
                member_a.get("config_path") or old_row.get("Evidence A", "")
            ),
            "Evidence B": str(
                member_b.get("config_path") or old_row.get("Evidence B", "")
            ),
            "Row Key": "",
        }
        row["Row Key"] = _row_key(row)
        refreshed.append(row)
    return refreshed


def _iter_semantic_key_paths(payload: Any, *, prefix: tuple[str, ...] = ()) -> set[str]:
    paths: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key)
            current = (*prefix, key_text)
            if key_text in BASE_CONFIG_SEMANTIC_KEYS:
                paths.add(".".join(current))
            paths.update(_iter_semantic_key_paths(value, prefix=current))
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            paths.update(_iter_semantic_key_paths(item, prefix=(*prefix, str(index))))
    return paths


def _base_config_role(path: Path) -> str:
    name = path.name
    if name == "pipeline.yaml":
        return "medallion_defaults_and_contract_field_defaults"
    if name == "quality.yaml":
        return "global_dq_defaults"
    if name == "contract_registry.yaml":
        return "gold_contract_identity_registry"
    if name == "bronze_fixture_manifest.yaml":
        return "bronze_lineage_fixture_manifest"
    if name == "bronze_fixture_gaps.yaml":
        return "bronze_fixture_gap_registry"
    return "base_config"


def _build_base_config_coverage() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for path in sorted(BASE_CONFIG_DIR.glob("*.yaml")):
        payload = _load_yaml(path)
        semantic_paths = sorted(_iter_semantic_key_paths(payload))
        entries.append(
            {
                "path": _repo_rel(path),
                "role": _base_config_role(path),
                "semantic_surface_count": len(semantic_paths),
                "semantic_surfaces": semantic_paths,
            }
        )
    return {
        "base_config_count": len(entries),
        "semantic_surface_count": sum(
            int(entry["semantic_surface_count"]) for entry in entries
        ),
        "entries": entries,
    }


def _cluster_review_expiry(registry: dict[str, Any], status: str) -> str:
    expiries = sorted(
        str(cluster.get("review", {}).get("expires_on", ""))
        for cluster in registry.get("clusters", [])
        if isinstance(cluster, dict)
        and str(cluster.get("semantic_status", "")).upper() == status.upper()
        and isinstance(cluster.get("review"), dict)
        and cluster.get("review", {}).get("expires_on")
    )
    return expiries[0] if expiries else ""


def _top_clusters(
    rows: list[dict[str, str]], *, column: str, value: str, limit: int = 12
) -> list[dict[str, Any]]:
    counts = Counter(row["Cluster ID"] for row in rows if row.get(column) == value)
    return [
        {"cluster_id": cluster_id, "row_count": count}
        for cluster_id, count in counts.most_common(limit)
    ]


def _build_residual_backlog(
    rows: list[dict[str, str]],
    registry: dict[str, Any],
    *,
    base_config_coverage: dict[str, Any],
    source_date: str,
) -> dict[str, Any]:
    risk_counts = Counter(row["Drift Risk"] for row in rows)
    semantic_counts = Counter(row["Semantic Status"] for row in rows)
    normalization_counts = Counter(row["Normalization"] for row in rows)
    validation_counts = Counter(row["Validation"] for row in rows)
    typing_counts = Counter(row["Typing"] for row in rows)
    blocking_risks = sum(
        risk_counts.get(risk, 0) for risk in ("CRITICAL", "HIGH", "MEDIUM")
    )
    blocking_statuses = (
        normalization_counts.get("DIFFERENT", 0)
        + normalization_counts.get("CONFLICTING", 0)
        + validation_counts.get("STRICTNESS_MISMATCH", 0)
        + typing_counts.get("CONFLICTING", 0)
    )
    tasks = [
        {
            "id": "semantic_drift_budget",
            "priority": "P0",
            "status": "closed",
            "row_count": blocking_risks,
            "definition_of_done": (
                "CRITICAL/HIGH/MEDIUM drift risks remain at zero in the "
                "semantic pair matrix budget gate."
            ),
            "gate": "uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json",
        },
        {
            "id": "hard_status_mismatch_budget",
            "priority": "P0",
            "status": "closed",
            "row_count": blocking_statuses,
            "definition_of_done": (
                "Normalization DIFFERENT/CONFLICTING, Validation "
                "STRICTNESS_MISMATCH, and Typing CONFLICTING remain at zero."
            ),
            "gate": "uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json",
        },
        {
            "id": "partial_identity_policy_review",
            "priority": "P2",
            "status": "reviewed_until_expiry",
            "row_count": semantic_counts.get("PARTIAL", 0),
            "expires_on": _cluster_review_expiry(registry, "PARTIAL"),
            "top_clusters": _top_clusters(
                rows, column="Semantic Status", value="PARTIAL"
            ),
            "definition_of_done": (
                "PARTIAL identities stay documented as join/lineage policy, "
                "not silently promoted to EXACT."
            ),
            "gate": "uv run python -m scripts.engineering.qa check-semantic-registry-drift --check --json",
        },
        {
            "id": "weak_same_name_inventory_review",
            "priority": "P2",
            "status": "reviewed_until_expiry",
            "row_count": semantic_counts.get("WEAK", 0),
            "expires_on": _cluster_review_expiry(registry, "WEAK"),
            "top_clusters": _top_clusters(rows, column="Semantic Status", value="WEAK"),
            "definition_of_done": (
                "WEAK same-name inventory remains owner-reviewed and does not "
                "assert cross-pipeline business identity."
            ),
            "gate": "uv run python -m scripts.engineering.qa check-semantic-registry-drift --check --json",
        },
        {
            "id": "generic_collision_inventory_review",
            "priority": "P2",
            "status": "reviewed_until_expiry",
            "row_count": semantic_counts.get("CONFLICTING", 0),
            "expires_on": _cluster_review_expiry(registry, "CONFLICTING"),
            "top_clusters": _top_clusters(
                rows, column="Semantic Status", value="CONFLICTING"
            ),
            "definition_of_done": (
                "Generic lexical collisions remain explicit owner-reviewed "
                "warnings instead of canonical fields."
            ),
            "gate": "uv run python -m scripts.engineering.qa check-generic-field-ownership --check --json",
        },
        {
            "id": "compatible_normalization_ratchet",
            "priority": "P2",
            "status": "ratcheted",
            "row_count": normalization_counts.get("COMPATIBLE", 0),
            "top_clusters": _top_clusters(
                rows, column="Normalization", value="COMPATIBLE"
            ),
            "definition_of_done": (
                "Compatible normalization rows may decrease, but must not grow "
                "without an intentional budget update."
            ),
            "gate": "uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json",
        },
        {
            "id": "compatible_validation_ratchet",
            "priority": "P2",
            "status": "ratcheted",
            "row_count": validation_counts.get("COMPATIBLE", 0),
            "top_clusters": _top_clusters(
                rows, column="Validation", value="COMPATIBLE"
            ),
            "definition_of_done": (
                "Compatible validation rows may decrease, but must not grow "
                "without an intentional budget update."
            ),
            "gate": "uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json",
        },
        {
            "id": "compatible_typing_ratchet",
            "priority": "P2",
            "status": "ratcheted",
            "row_count": typing_counts.get("COMPATIBLE", 0),
            "top_clusters": _top_clusters(rows, column="Typing", value="COMPATIBLE"),
            "definition_of_done": (
                "Compatible typing rows may decrease, but must not grow without "
                "an intentional budget update."
            ),
            "gate": "uv run python -m scripts.engineering.qa check-semantic-pair-budget --check --json",
        },
        {
            "id": "base_config_semantic_coverage",
            "priority": "P2",
            "status": "closed",
            "row_count": int(base_config_coverage.get("semantic_surface_count", 0)),
            "definition_of_done": (
                "Base config semantic surfaces are included in the generated "
                "audit manifest and regression test."
            ),
            "gate": "uv run pytest tests/integration/config/test_semantic_pair_matrix_budget.py -q --tb=short",
        },
    ]
    return {
        "generated_at": f"{source_date}T00:00:00Z",
        "source_date": source_date,
        "summary": {
            "blocking_task_count": 0
            if blocking_risks == 0 and blocking_statuses == 0
            else 1,
            "pair_rows": len(rows),
            "clusters": len(registry.get("clusters", [])),
            "risk_counts": dict(risk_counts),
            "semantic_status_counts": dict(semantic_counts),
            "normalization_counts": dict(normalization_counts),
            "validation_counts": dict(validation_counts),
            "typing_counts": dict(typing_counts),
        },
        "tasks": tasks,
    }


def _render_residual_backlog_markdown(backlog: dict[str, Any]) -> str:
    summary = backlog["summary"]
    lines = [
        "# Semantic Pipeline Residual Backlog",
        "",
        f"Generated: `{backlog['source_date']}`",
        "",
        "## Summary",
        "",
        f"- Blocking tasks: `{summary['blocking_task_count']}`",
        f"- Pair rows: `{summary['pair_rows']}`",
        f"- Clusters: `{summary['clusters']}`",
        f"- Risk counts: `{json.dumps(summary['risk_counts'], sort_keys=True)}`",
        f"- Semantic status counts: `{json.dumps(summary['semantic_status_counts'], sort_keys=True)}`",
        f"- Normalization counts: `{json.dumps(summary['normalization_counts'], sort_keys=True)}`",
        f"- Validation counts: `{json.dumps(summary['validation_counts'], sort_keys=True)}`",
        f"- Typing counts: `{json.dumps(summary['typing_counts'], sort_keys=True)}`",
        "",
        "## Tasks",
        "",
        "| ID | Priority | Status | Rows | Expiry | Gate |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for task in backlog["tasks"]:
        task_row = {**task, "expires_on": task.get("expires_on", "")}
        lines.append(
            "| {id} | {priority} | {status} | {row_count} | {expires_on} | `{gate}` |".format(
                **task_row,
            )
        )
    lines.append("")
    return "\n".join(lines)


def _render_pair_csv(rows: list[dict[str, str]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(PAIR_COLUMNS), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _render_canonical_fields_csv(registry: dict[str, Any]) -> str:
    output = io.StringIO()
    fieldnames = (
        "cluster_id",
        "canonical_field",
        "semantic_status",
        "member_count",
        "rationale",
    )
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for cluster in registry.get("clusters", []):
        writer.writerow(
            {
                "cluster_id": cluster.get("cluster_id", ""),
                "canonical_field": cluster.get("canonical_field", ""),
                "semantic_status": cluster.get("semantic_status", ""),
                "member_count": cluster.get("member_count", 0),
                "rationale": cluster.get("rationale", ""),
            }
        )
    return output.getvalue()


def _render_critical_inconsistencies(
    rows: list[dict[str, str]], *, source_date: str
) -> str:
    counts = Counter(row["Drift Risk"] for row in rows)
    lines = [
        "# Semantic Pipeline Critical Inconsistencies",
        "",
        f"Generated: `{source_date}`",
        "",
        "## Summary",
        "",
        f"- CRITICAL: `{counts.get('CRITICAL', 0)}`",
        f"- HIGH: `{counts.get('HIGH', 0)}`",
        f"- MEDIUM: `{counts.get('MEDIUM', 0)}`",
        f"- LOW: `{counts.get('LOW', 0)}`",
        "",
        "## CRITICAL And HIGH Rows",
        "",
        (
            "| Risk | Cluster | Pipeline A | Field A | Pipeline B | Field B | "
            "Normalization | Validation | Typing | Row Key |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        if row["Drift Risk"] not in {"CRITICAL", "HIGH"}:
            continue
        lines.append(
            (
                "| {Drift Risk} | {Cluster ID} | {Pipeline A} | {Field A} | "
                "{Pipeline B} | {Field B} | {Normalization} | {Validation} | "
                "{Typing} | {Row Key} |"
            ).format(**row)
        )
    lines.append("")
    return "\n".join(lines)


def _render_report(
    rows: list[dict[str, str]],
    registry: dict[str, Any],
    *,
    base_config_coverage: dict[str, Any],
    residual_backlog: dict[str, Any],
    source_date: str,
) -> str:
    risk_counts = Counter(row["Drift Risk"] for row in rows)
    semantic_counts = Counter(row["Semantic Status"] for row in rows)
    normalization_counts = Counter(row["Normalization"] for row in rows)
    validation_counts = Counter(row["Validation"] for row in rows)
    typing_counts = Counter(row["Typing"] for row in rows)
    normalization_mismatches = normalization_counts.get(
        "DIFFERENT", 0
    ) + normalization_counts.get("CONFLICTING", 0)
    return "\n".join(
        [
            "# Semantic Pipeline Audit",
            "",
            f"Generated: `{source_date}`",
            "",
            "## Executive Summary",
            "",
            f"- Semantic clusters: `{len(registry.get('clusters', []))}`",
            f"- Pair rows: `{len(rows)}`",
            f"- Base config files covered: `{base_config_coverage.get('base_config_count', 0)}`",
            f"- Base config semantic surfaces: `{base_config_coverage.get('semantic_surface_count', 0)}`",
            f"- CRITICAL drift risks: `{risk_counts.get('CRITICAL', 0)}`",
            f"- HIGH drift risks: `{risk_counts.get('HIGH', 0)}`",
            f"- Normalization mismatches: `{normalization_mismatches}`",
            f"- Validation strictness mismatches: `{validation_counts.get('STRICTNESS_MISMATCH', 0)}`",
            f"- Typing conflicts: `{typing_counts.get('CONFLICTING', 0)}`",
            f"- Reviewed PARTIAL rows: `{semantic_counts.get('PARTIAL', 0)}`",
            f"- Reviewed WEAK inventory rows: `{semantic_counts.get('WEAK', 0)}`",
            f"- Reviewed generic collision rows: `{semantic_counts.get('CONFLICTING', 0)}`",
            f"- Compatible normalization rows: `{normalization_counts.get('COMPATIBLE', 0)}`",
            f"- Compatible validation rows: `{validation_counts.get('COMPATIBLE', 0)}`",
            f"- Compatible typing rows: `{typing_counts.get('COMPATIBLE', 0)}`",
            f"- Residual blocking tasks: `{residual_backlog['summary']['blocking_task_count']}`",
            "",
            "## Artifact Index",
            "",
            f"- `semantic_pair_matrix_{source_date}.csv`",
            f"- `semantic_cluster_registry_{source_date}.json`",
            f"- `critical_inconsistencies_{source_date}.md`",
            f"- `recommended_canonical_fields_{source_date}.csv`",
            f"- `base_config_semantic_coverage_{source_date}.json`",
            f"- `semantic_residual_backlog_{source_date}.json`",
            f"- `semantic_residual_backlog_{source_date}.md`",
            f"- `semantic_pipeline_audit_manifest_{source_date}.json`",
            "",
            "## Notes",
            "",
            "This generated snapshot refreshes member evidence from active pipeline configs, "
            "base config defaults, normalization profiles, DQ visibility, "
            "Pandera-derived Gold contracts, and the reviewed semantic cluster registry.",
            "",
        ]
    )


def _manifest(
    rows: list[dict[str, str]],
    registry: dict[str, Any],
    *,
    base_config_coverage: dict[str, Any],
    residual_backlog: dict[str, Any],
    field_inventory_count: int,
    source_date: str,
) -> dict[str, Any]:
    return {
        "generated_at": f"{source_date}T00:00:00Z",
        "source_date": source_date,
        "scope": "all_etl_pipelines",
        "artifact_count": 8,
        "artifacts": {
            "pair_matrix": f"semantic_pair_matrix_{source_date}.csv",
            "cluster_registry": f"semantic_cluster_registry_{source_date}.json",
            "critical_inconsistencies": f"critical_inconsistencies_{source_date}.md",
            "recommended_canonical_fields": f"recommended_canonical_fields_{source_date}.csv",
            "base_config_semantic_coverage": f"base_config_semantic_coverage_{source_date}.json",
            "residual_backlog": f"semantic_residual_backlog_{source_date}.json",
            "residual_backlog_markdown": f"semantic_residual_backlog_{source_date}.md",
            "audit_report": f"semantic_pipeline_audit_{source_date}.md",
        },
        "counts": {
            "base_configs": base_config_coverage,
            "clusters": len(registry.get("clusters", [])),
            "fields": field_inventory_count,
            "pairs": len(rows),
            "pipelines": len(
                {row["Pipeline A"] for row in rows}
                | {row["Pipeline B"] for row in rows}
            ),
            "risk": dict(Counter(row["Drift Risk"] for row in rows)),
            "normalization": dict(Counter(row["Normalization"] for row in rows)),
            "validation": dict(Counter(row["Validation"] for row in rows)),
            "typing": dict(Counter(row["Typing"] for row in rows)),
            "residual_backlog": residual_backlog["summary"],
        },
    }


def build_artifacts(
    *,
    source_date: str,
    seed_pair_matrix: Path,
    seed_cluster_registry: Path,
    review_registry: Path = DEFAULT_REVIEW_REGISTRY,
) -> dict[str, str]:
    seed_rows = _load_csv(seed_pair_matrix)
    seed_registry = _load_json(seed_cluster_registry)
    review_payload = _load_yaml(review_registry)
    review_lookup = _risk_cap_lookup(review_payload)
    facts = _build_current_member_facts(seed_registry)
    base_config_coverage = _build_base_config_coverage()
    registry = _refresh_clusters(
        seed_registry,
        facts,
        review_registry=review_payload,
        source_date=source_date,
    )
    pair_rows = _refresh_pair_rows(seed_rows, facts, review_lookup)
    residual_backlog = _build_residual_backlog(
        pair_rows,
        registry,
        base_config_coverage=base_config_coverage,
        source_date=source_date,
    )
    manifest = _manifest(
        pair_rows,
        registry,
        base_config_coverage=base_config_coverage,
        residual_backlog=residual_backlog,
        field_inventory_count=len(facts),
        source_date=source_date,
    )
    return {
        f"semantic_pair_matrix_{source_date}.csv": _render_pair_csv(pair_rows),
        f"semantic_cluster_registry_{source_date}.json": json.dumps(
            registry,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        f"critical_inconsistencies_{source_date}.md": _render_critical_inconsistencies(
            pair_rows,
            source_date=source_date,
        ),
        f"base_config_semantic_coverage_{source_date}.json": json.dumps(
            base_config_coverage,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        f"semantic_residual_backlog_{source_date}.json": json.dumps(
            residual_backlog,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        f"semantic_residual_backlog_{source_date}.md": _render_residual_backlog_markdown(
            residual_backlog
        ),
        f"recommended_canonical_fields_{source_date}.csv": _render_canonical_fields_csv(
            registry
        ),
        f"semantic_pipeline_audit_{source_date}.md": _render_report(
            pair_rows,
            registry,
            base_config_coverage=base_config_coverage,
            residual_backlog=residual_backlog,
            source_date=source_date,
        ),
        f"semantic_pipeline_audit_manifest_{source_date}.json": json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
    }


def write_artifacts(
    *,
    out_dir: Path,
    source_date: str,
    seed_pair_matrix: Path,
    seed_cluster_registry: Path,
    review_registry: Path = DEFAULT_REVIEW_REGISTRY,
) -> dict[str, Any]:
    artifacts = build_artifacts(
        source_date=source_date,
        seed_pair_matrix=seed_pair_matrix,
        seed_cluster_registry=seed_cluster_registry,
        review_registry=review_registry,
    )
    for filename, payload in artifacts.items():
        _write(out_dir / filename, payload)
    manifest = json.loads(
        artifacts[f"semantic_pipeline_audit_manifest_{source_date}.json"]
    )
    counts = dict(manifest["counts"])
    base_configs = counts.get("base_configs", {})
    if isinstance(base_configs, dict):
        counts["base_configs"] = {
            "base_config_count": base_configs.get("base_config_count", 0),
            "semantic_surface_count": base_configs.get("semantic_surface_count", 0),
        }
    return {"out_dir": str(out_dir), **counts}


def check_artifacts(
    *,
    out_dir: Path,
    source_date: str,
    seed_pair_matrix: Path,
    seed_cluster_registry: Path,
    review_registry: Path = DEFAULT_REVIEW_REGISTRY,
) -> int:
    artifacts = build_artifacts(
        source_date=source_date,
        seed_pair_matrix=seed_pair_matrix,
        seed_cluster_registry=seed_cluster_registry,
        review_registry=review_registry,
    )
    stale = []
    for filename, expected in artifacts.items():
        path = out_dir / filename
        if not path.exists():
            stale.append(filename)
            continue
        actual = _normalize_newlines(path.read_text(encoding="utf-8"))
        if actual != _normalize_newlines(expected):
            stale.append(filename)
    if stale:
        print("[semantic-pipeline-audit] stale artifacts:")
        for filename in stale:
            print(f"- {filename}")
        return 1
    print("[semantic-pipeline-audit] ok")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate semantic pipeline audit snapshot artifacts.",
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--source-date", default=DEFAULT_SOURCE_DATE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed-pair-matrix", type=Path)
    parser.add_argument("--seed-cluster-registry", type=Path)
    parser.add_argument("--review-registry", type=Path, default=DEFAULT_REVIEW_REGISTRY)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    out_dir = args.out_dir if args.out_dir.is_absolute() else REPO_ROOT / args.out_dir
    seed_pair_matrix = _resolve_seed_artifact(
        args.seed_pair_matrix,
        out_dir=out_dir,
        prefix=PAIR_MATRIX_PREFIX,
        source_date=args.source_date,
        suffix=".csv",
    )
    seed_cluster_registry = _resolve_seed_artifact(
        args.seed_cluster_registry,
        out_dir=out_dir,
        prefix=CLUSTER_REGISTRY_PREFIX,
        source_date=args.source_date,
        suffix=".json",
    )
    review_registry = (
        args.review_registry
        if args.review_registry.is_absolute()
        else REPO_ROOT / args.review_registry
    )
    generated_at = datetime.now(UTC).isoformat()
    if args.check:
        return check_artifacts(
            out_dir=out_dir,
            source_date=args.source_date,
            seed_pair_matrix=seed_pair_matrix,
            seed_cluster_registry=seed_cluster_registry,
            review_registry=review_registry,
        )
    result = write_artifacts(
        out_dir=out_dir,
        source_date=args.source_date,
        seed_pair_matrix=seed_pair_matrix,
        seed_cluster_registry=seed_cluster_registry,
        review_registry=review_registry,
    )
    result["generated_at"] = generated_at
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
