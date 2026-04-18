#!/usr/bin/env python3
"""Generate deterministic normalization field-matrix artifacts for all pipelines."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

import yaml

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "src"))

from bioetl.application.composite.checkpoint import (
    create_expected_checkpoint_context,
    merge_expected_anchors,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.application.composite.join_key_normalization import (
    JOIN_KEY_NORMALIZATION_POLICIES,
)
from bioetl.application.core.normalization_fallbacks import (
    is_date_field,
    is_doi_field,
    is_pmid_field,
    is_smiles_field,
)
from bioetl.application.core.normalization_rules import NormalizationRulesPolicy
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    normalize_run_ledger_payload,
    normalize_run_manifest_spec,
    normalize_runtime_anchor_payload,
)
from bioetl.domain.normalization.profiles import (
    NORMALIZATION_PROFILE_REGISTRY,
    resolve_normalization_profile,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_json_string,
    normalize_profile_passthrough,
)
from bioetl.infrastructure.schemas.silver import (
    CHEMBL_ACTIVITY_SCHEMA,
    CHEMBL_ASSAY_PARAMETERS_SCHEMA,
    CHEMBL_ASSAY_SCHEMA,
    CHEMBL_CELL_LINE_SCHEMA,
    CHEMBL_COMPOUND_RECORD_SCHEMA,
    CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
    CHEMBL_DOCUMENT_TERM_SCHEMA,
    CHEMBL_MOLECULE_SCHEMA,
    CHEMBL_PROTEIN_CLASS_SCHEMA,
    CHEMBL_PUBLICATION_SCHEMA,
    CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
    CHEMBL_TARGET_COMPONENT_SCHEMA,
    CHEMBL_TARGET_SCHEMA,
    CHEMBL_TISSUE_SCHEMA,
    CROSSREF_PUBLICATION_SCHEMA,
    OPENALEX_PUBLICATION_SCHEMA,
    PUBCHEM_COMPOUND_SCHEMA,
    PUBMED_PUBLICATION_SCHEMA,
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
    UNIPROT_ID_MAPPING_SCHEMA,
    UNIPROT_PROTEIN_SCHEMA,
)

if TYPE_CHECKING:
    import pyarrow as pa

DEFAULT_OUT_DIR = Path("docs/reports/generated/pipeline_normalization_field_matrix")
CSV_NAME = "pipeline_normalization_field_matrix.csv"
MD_NAME = "pipeline_normalization_field_matrix.md"

CSV_COLUMNS = (
    "pipeline_name",
    "pipeline_kind",
    "field_name",
    "field_type",
    "normalization_source",
    "normalizer",
    "normalization_summary",
    "include_in_content_hash",
    "set_like",
    "notes",
)

FALLBACK_BUSINESS = "fallback_business"
FALLBACK_TECHNICAL_PASSTHROUGH = "fallback_technical_passthrough"
EXPLICIT_PROFILE_COVERAGE_KPI = "explicit_profile_coverage_pct"
COMPOSITE_JOIN_KEY_COVERAGE_KPI = "composite_join_key_policy_coverage_pct"
CONTROL_PLANE_NORMALIZATION_COVERAGE_KPI = "control_plane_normalization_coverage_pct"
ENTITY_RECORD_SURFACE = "entity_record"
COMPOSITE_JOIN_KEY_SURFACE = "composite_join_key"
CONTROL_PLANE_REPRODUCIBILITY_SURFACE = "control_plane_reproducibility"
PROFILE_SEMANTICS_SURFACE = "profile_semantics"
PROFILE_META_PASSTHROUGH_KPI = "shipped_profile_meta_passthrough_pct"
PROFILE_SET_LIKE_JSON_STRING_KPI = "shipped_profile_set_like_json_string_pct"
PROFILE_NON_META_PASSTHROUGH_FREE_KPI = "shipped_profile_non_meta_passthrough_free_pct"

# Intentionally explicit governance seam:
# the normalization matrix is config-discovered, but the Silver schema mapping
# remains a reviewed allow-list so shipped entity pipelines cannot silently gain
# matrix coverage without an explicit schema registration step.
ENTITY_SILVER_SCHEMA_REGISTRY: dict[str, Any] = {
    "chembl_activity": CHEMBL_ACTIVITY_SCHEMA,
    "chembl_assay": CHEMBL_ASSAY_SCHEMA,
    "chembl_assay_parameters": CHEMBL_ASSAY_PARAMETERS_SCHEMA,
    "chembl_cell_line": CHEMBL_CELL_LINE_SCHEMA,
    "chembl_compound_record": CHEMBL_COMPOUND_RECORD_SCHEMA,
    "chembl_molecule": CHEMBL_MOLECULE_SCHEMA,
    "chembl_protein_class": CHEMBL_PROTEIN_CLASS_SCHEMA,
    "chembl_publication": CHEMBL_PUBLICATION_SCHEMA,
    "chembl_publication_similarity": CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
    "chembl_publication_term": CHEMBL_DOCUMENT_TERM_SCHEMA,
    "chembl_subcellular_fraction": CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
    "chembl_target": CHEMBL_TARGET_SCHEMA,
    "chembl_target_component": CHEMBL_TARGET_COMPONENT_SCHEMA,
    "chembl_tissue": CHEMBL_TISSUE_SCHEMA,
    "crossref_publication": CROSSREF_PUBLICATION_SCHEMA,
    "openalex_publication": OPENALEX_PUBLICATION_SCHEMA,
    "pubchem_compound": PUBCHEM_COMPOUND_SCHEMA,
    "pubmed_publication": PUBMED_PUBLICATION_SCHEMA,
    "semanticscholar_publication": SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
    "uniprot_idmapping": UNIPROT_ID_MAPPING_SCHEMA,
    "uniprot_protein": UNIPROT_PROTEIN_SCHEMA,
}

COMPOSITE_GOLD_SCHEMA_TYPE_REGISTRY: dict[str, str] = {
    "composite_activity": "unknown",
    "composite_assay": "unknown",
    "composite_molecule": "unknown",
    "composite_publication": "unknown",
    "composite_target": "unknown",
}


def _normalizer_name(
    normalizer: Any,
    *,
    field_name: str,
    notes: str | None,
) -> str:
    name = getattr(normalizer, "__name__", type(normalizer).__name__)
    if name != "<lambda>":
        return name

    normalized_notes = (notes or "").casefold()
    if field_name == "canonical_smiles" or "canonical smiles" in normalized_notes:
        return "normalize_profile_canonical_smiles"
    if field_name == "isomeric_smiles" or "isomeric smiles" in normalized_notes:
        return "normalize_profile_isomeric_smiles"
    return "lambda"


def _entity_config_paths() -> list[Path]:
    return sorted(Path("configs/entities").glob("*/*.yaml"))


def _composite_config_paths() -> list[Path]:
    return sorted(Path("configs/composites").glob("*.yaml"))


def _load_yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _render_bool(value: bool | None) -> str:
    if value is None:
        return ""
    return "true" if value else "false"


def _looks_like_string_type(type_name: str) -> bool:
    lowered = type_name.lower()
    return "string" in lowered or "large_string" in lowered


def _normalize_summary_from_policy(*, key: str, trim: bool, lowercase: bool) -> str:
    if key == "doi":
        return (
            "Validate DOI through the canonical domain identifier contract, then "
            "emit lowercase join-canonical text."
        )
    if key == "pmid":
        return (
            "Validate PMID through the canonical domain identifier contract, then "
            "emit digits-only join-canonical text."
        )
    if key == "pmc_id":
        return (
            "Validate PMC identifier through the canonical domain identifier "
            "contract, then emit lowercase join-canonical text."
        )
    if trim and lowercase:
        return "Trim surrounding whitespace and lowercase join-key text."
    if trim:
        return "Trim surrounding whitespace for join-key text."
    if lowercase:
        return "Lowercase join-key text."
    return "Composite join key is preserved as-is by explicit no-op policy."


def _fallback_contract(
    rule_set: NormalizationRulesPolicy,
    *,
    field_name: str,
    field_type: str,
) -> tuple[str, str, str]:
    if field_name in rule_set.passthrough_fields:
        return (
            FALLBACK_TECHNICAL_PASSTHROUGH,
            "passthrough",
            "Field is passed through unchanged by the canonical fallback normalization seam.",
        )
    if field_name.startswith("_"):
        return (
            FALLBACK_TECHNICAL_PASSTHROUGH,
            "passthrough",
            "Technical field appears in the normalization inventory only; "
            "persisted-row publication is governed separately by the "
            "Silver/Gold storage contract.",
        )
    if field_name in rule_set.title_fields:
        return (
            FALLBACK_BUSINESS,
            "normalize_title",
            "Normalize title text through HTML/entity cleanup and whitespace normalization.",
        )
    if field_name in rule_set.abstract_fields:
        return (
            FALLBACK_BUSINESS,
            "normalize_abstract",
            "Normalize abstract text through HTML/entity cleanup and whitespace normalization.",
        )
    if field_name in rule_set.oa_status_fields:
        return (
            FALLBACK_BUSINESS,
            "normalize_oa_status",
            "Trim textual OA status and lowercase the resulting value.",
        )
    if is_doi_field(field_name, rule_set=rule_set):
        return (
            FALLBACK_BUSINESS,
            "normalize_profile_doi",
            "Normalize DOI through the canonical fallback identifier helper.",
        )
    if is_pmid_field(field_name, rule_set=rule_set):
        return (
            FALLBACK_BUSINESS,
            "normalize_profile_pmid",
            "Normalize PMID through the canonical fallback identifier helper.",
        )
    if is_date_field(field_name, rule_set=rule_set):
        return (
            FALLBACK_BUSINESS,
            "normalize_partial_date",
            "Canonicalize supported date text to the stable partial-date representation.",
        )
    if is_smiles_field(field_name):
        return (
            FALLBACK_BUSINESS,
            "SMILES.from_raw(mode=soft)",
            "Validate and trim SMILES text; invalid values collapse to None.",
        )
    if _looks_like_string_type(field_type):
        return (
            FALLBACK_BUSINESS,
            "normalize_string + canonicalize_json_string(json-like)",
            "Trim string values, collapse blanks to None, and canonicalize JSON-looking string payloads.",
        )
    return (
        FALLBACK_BUSINESS,
        "preserve_non_string",
        "No field-specific fallback normalizer is applied; non-string values are preserved as-is.",
    )


def _build_entity_rows_for_pipeline(
    *,
    pipeline_name: str,
    provider: str,
    entity: str,
    schema: pa.Schema,
) -> list[dict[str, str]]:
    profile = resolve_normalization_profile(provider, entity)
    rule_set = NormalizationRulesPolicy()
    rows: list[dict[str, str]] = []
    for field_name in schema.names:
        field = schema.field(field_name)
        field_type = str(field.type)
        profile_rule = None if profile is None else profile.rule_for(field_name)
        if profile_rule is not None:
            rows.append(
                {
                    "pipeline_name": pipeline_name,
                    "pipeline_kind": "entity",
                    "field_name": field_name,
                    "field_type": field_type,
                    "normalization_source": "profile",
                    "normalizer": _normalizer_name(
                        profile_rule.normalizer,
                        field_name=field_name,
                        notes=profile_rule.notes,
                    ),
                    "normalization_summary": profile_rule.notes or "",
                    "include_in_content_hash": _render_bool(profile_rule.include_in_hash),
                    "set_like": _render_bool(profile_rule.set_like),
                    "notes": profile_rule.notes or "",
                }
            )
            continue

        source, normalizer, summary = _fallback_contract(
            rule_set,
            field_name=field_name,
            field_type=field_type,
        )
        rows.append(
            {
                "pipeline_name": pipeline_name,
                "pipeline_kind": "entity",
                "field_name": field_name,
                "field_type": field_type,
                "normalization_source": source,
                "normalizer": normalizer,
                "normalization_summary": summary,
                "include_in_content_hash": "",
                "set_like": "false",
                "notes": "",
            }
        )
    return rows


def _iter_composite_fields(payload: dict[str, object]) -> list[str]:
    composite = payload.get("composite")
    if not isinstance(composite, dict):
        return []
    merge = composite.get("merge")
    if not isinstance(merge, dict):
        return []
    column_groups = merge.get("column_groups")
    if not isinstance(column_groups, list):
        return []

    ordered: list[str] = []
    seen: set[str] = set()
    for group in column_groups:
        if not isinstance(group, dict):
            continue
        fields = group.get("fields")
        if not isinstance(fields, list):
            continue
        for field_name in fields:
            if not isinstance(field_name, str) or field_name in seen:
                continue
            seen.add(field_name)
            ordered.append(field_name)
    return ordered


def _iter_composite_join_keys(payload: dict[str, object]) -> set[str]:
    composite = payload.get("composite")
    if not isinstance(composite, dict):
        return set()

    keys: set[str] = set()
    dependencies = composite.get("dependencies")
    if isinstance(dependencies, list):
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                continue
            join_keys = dependency.get("join_keys")
            if isinstance(join_keys, list):
                keys.update(str(key) for key in join_keys if isinstance(key, str))

    enrichers = composite.get("enrichers")
    if isinstance(enrichers, list):
        for enricher in enrichers:
            if not isinstance(enricher, dict):
                continue
            join_keys = enricher.get("join_keys")
            if isinstance(join_keys, list):
                keys.update(str(key) for key in join_keys if isinstance(key, str))
    return keys


def _iter_composite_join_key_occurrences(payload: dict[str, object]) -> list[str]:
    return sorted(_iter_composite_join_keys(payload))


def _build_composite_rows_for_pipeline(
    *,
    pipeline_name: str,
    payload: dict[str, object],
) -> list[dict[str, str]]:
    join_keys = _iter_composite_join_keys(payload)
    rows: list[dict[str, str]] = []
    for field_name in _iter_composite_fields(payload):
        policy = JOIN_KEY_NORMALIZATION_POLICIES.get(field_name)
        if field_name in join_keys and policy is not None:
            source = "composite_join_key_policy"
            normalizer = "join_key_policy"
            summary = _normalize_summary_from_policy(
                key=field_name,
                trim=policy.trim,
                lowercase=policy.lowercase,
            )
            notes = "Applied only while resolving and comparing composite join keys."
        else:
            source = "upstream_inherited"
            normalizer = "none"
            summary = (
                "No composite-specific field normalizer is defined; field is inherited "
                "from already-normalized upstream records."
            )
            notes = (
                "Composite normalization is key-oriented; non-key fields preserve upstream semantics."
            )
        rows.append(
            {
                "pipeline_name": pipeline_name,
                "pipeline_kind": "composite",
                "field_name": field_name,
                "field_type": COMPOSITE_GOLD_SCHEMA_TYPE_REGISTRY.get(
                    pipeline_name, "unknown"
                ),
                "normalization_source": source,
                "normalizer": normalizer,
                "normalization_summary": summary,
                "include_in_content_hash": "",
                "set_like": "false",
                "notes": notes,
            }
        )
    return rows


def build_field_matrix_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for config_path in _entity_config_paths():
        payload = _load_yaml(config_path)
        pipeline = payload.get("pipeline")
        if not isinstance(pipeline, dict):
            continue
        pipeline_name = str(pipeline.get("pipeline_name", "")).strip()
        if not pipeline_name:
            continue
        provider = str(payload.get("provider", "")).strip()
        entity = str(payload.get("entity", "")).strip()
        schema = ENTITY_SILVER_SCHEMA_REGISTRY.get(pipeline_name)
        if schema is None:
            raise ValueError(f"Missing Silver schema registry entry for {pipeline_name}")
        rows.extend(
            _build_entity_rows_for_pipeline(
                pipeline_name=pipeline_name,
                provider=provider,
                entity=entity,
                schema=schema,
            )
        )

    for config_path in _composite_config_paths():
        payload = _load_yaml(config_path)
        composite = payload.get("composite")
        if not isinstance(composite, dict):
            continue
        pipeline_name = str(composite.get("name", "")).strip()
        if not pipeline_name:
            continue
        rows.extend(
            _build_composite_rows_for_pipeline(
                pipeline_name=pipeline_name,
                payload=payload,
            )
        )

    return rows


def build_entity_profile_coverage_kpi(
    rows: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    entity_rows = [
        row for row in (build_field_matrix_rows() if rows is None else rows)
        if row["pipeline_kind"] == "entity"
    ]
    entity_field_count = len(entity_rows)
    explicit_profile_field_count = sum(
        1 for row in entity_rows if row["normalization_source"] == "profile"
    )
    value_pct = round(
        (explicit_profile_field_count * 100 / entity_field_count) if entity_field_count else 0.0,
        2,
    )
    return {
        "surface": ENTITY_RECORD_SURFACE,
        "name": EXPLICIT_PROFILE_COVERAGE_KPI,
        "description": "Percent of shipped entity-record fields covered by explicit normalization profiles.",
        "numerator": explicit_profile_field_count,
        "denominator": entity_field_count,
        "value_pct": value_pct,
    }


def build_composite_join_key_policy_coverage_kpi() -> dict[str, object]:
    total_join_key_fields = 0
    explicit_policy_fields = 0
    for config_path in _composite_config_paths():
        payload = _load_yaml(config_path)
        join_keys = _iter_composite_join_key_occurrences(payload)
        total_join_key_fields += len(join_keys)
        explicit_policy_fields += sum(
            1 for key in join_keys if key in JOIN_KEY_NORMALIZATION_POLICIES
        )
    value_pct = round(
        (explicit_policy_fields * 100 / total_join_key_fields)
        if total_join_key_fields
        else 0.0,
        2,
    )
    return {
        "surface": COMPOSITE_JOIN_KEY_SURFACE,
        "name": COMPOSITE_JOIN_KEY_COVERAGE_KPI,
        "description": (
            "Percent of configured composite join-key fields covered by explicit "
            "join-key normalization policies."
        ),
        "numerator": explicit_policy_fields,
        "denominator": total_join_key_fields,
        "value_pct": value_pct,
    }


def _control_plane_surface_statuses() -> list[dict[str, object]]:
    occurred_at = datetime(2026, 4, 8, 12, 53, 47, tzinfo=UTC)
    manifest_status = normalize_run_manifest_spec(
        {
            "code_provenance": {"config_hash": "DEADBEEF"},
            "source_refs": [
                {
                    "pipeline_name": "chembl_activity",
                    "input_snapshots": [
                        {"snapshot_id": "b"},
                        {"snapshot_id": "a"},
                    ],
                }
            ],
            "planned_artifacts": [
                {"path": "b", "layer": "gold"},
                {"path": "a", "layer": "bronze"},
            ],
        }
    )
    ledger_status = normalize_run_ledger_payload(
        {
            "run_id": UUID("11111111-1111-1111-1111-111111111111"),
            "occurred_at": occurred_at,
            "metrics_snapshot": {"records_b": 2, "records_a": 1},
        }
    )
    execution_identity_status = build_execution_identity_payload(
        pipeline_name=" chembl_activity ",
        run_type=" INCREMENTAL ",
        pipeline_version=" 1.2.3 ",
        effective_config_hash=" SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA ",
        dq_contract_compatibility_hash=" DEADBEEF ",
        contract_ref=" ChemBL.Activity ",
        contract_version=" v2 ",
        effective_config_artifact_id=" artifact-42 ",
        exact_replay=True,
        input_snapshot_fingerprint=" FACE ",
    )
    runtime_anchor_status = normalize_runtime_anchor_payload(
        {
            "effective_config_hash": " SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA ",
            "contract_ref": " ChemBL.Activity ",
            "contract_version": " v2 ",
            "manifest_id": " manifest-123 ",
            "composite_run_identity": " run-42 ",
        }
    )
    checkpoint_context = create_expected_checkpoint_context(
        effective_config_hash=" SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA ",
        contract_ref=" ChemBL.Activity ",
        contract_version=" v2 ",
        manifest_id=" manifest-123 ",
        composite_run_identity=" run-42 ",
    )
    merged_checkpoint = merge_expected_anchors(
        CompositeCheckpointState(
            composite_name="composite_publication",
            run_id="run-1",
            state=CompositePipelineState.SEED_RUNNING,
        ),
        checkpoint_context,
    )

    return [
        {
            "seam": "run_manifest_spec",
            "covered": (
                manifest_status["code_provenance"] == {"config_hash": "deadbeef"}
                and manifest_status["planned_artifacts"][0]["layer"] == "bronze"
                and manifest_status["source_refs"][0]["input_snapshots"][0]["snapshot_id"]
                == "a"
            ),
        },
        {
            "seam": "run_ledger_payload",
            "covered": (
                ledger_status["run_id"] == "11111111-1111-1111-1111-111111111111"
                and ledger_status["occurred_at"] == "2026-04-08T12:53:47Z"
                and ledger_status["metrics_snapshot"] == {"records_a": 1, "records_b": 2}
            ),
        },
        {
            "seam": "execution_identity_payload",
            "covered": (
                execution_identity_status["contract_ref"] == "chembl.activity"
                and execution_identity_status["contract_version"] == "2.0.0"
                and execution_identity_status["exact_replay"] == "true"
            ),
        },
        {
            "seam": "runtime_anchor_payload",
            "covered": (
                runtime_anchor_status["effective_config_hash"]
                == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                and runtime_anchor_status["contract_ref"] == "chembl.activity"
                and runtime_anchor_status["contract_version"] == "2.0.0"
            ),
        },
        {
            "seam": "checkpoint_expected_context",
            "covered": (
                checkpoint_context.effective_config_hash
                == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                and checkpoint_context.contract_ref == "chembl.activity"
                and checkpoint_context.contract_version == "2.0.0"
            ),
        },
        {
            "seam": "checkpoint_anchor_merge",
            "covered": (
                merged_checkpoint.effective_config_hash
                == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                and merged_checkpoint.contract_ref == "chembl.activity"
                and merged_checkpoint.contract_version == "2.0.0"
                and merged_checkpoint.manifest_id == "manifest-123"
                and merged_checkpoint.composite_run_identity == "run-42"
            ),
        },
    ]


def build_control_plane_normalization_coverage_kpi() -> dict[str, object]:
    statuses = _control_plane_surface_statuses()
    covered = sum(1 for status in statuses if bool(status["covered"]))
    total = len(statuses)
    value_pct = round((covered * 100 / total) if total else 0.0, 2)
    return {
        "surface": CONTROL_PLANE_REPRODUCIBILITY_SURFACE,
        "name": CONTROL_PLANE_NORMALIZATION_COVERAGE_KPI,
        "description": (
            "Percent of governed control-plane and reproducibility normalization seams "
            "covered by canonical normalization contracts."
        ),
        "numerator": covered,
        "denominator": total,
        "value_pct": value_pct,
    }


def build_surface_coverage_kpis(
    rows: list[dict[str, str]] | None = None,
) -> list[dict[str, object]]:
    matrix_rows = build_field_matrix_rows() if rows is None else rows
    return [
        build_entity_profile_coverage_kpi(matrix_rows),
        build_composite_join_key_policy_coverage_kpi(),
        build_control_plane_normalization_coverage_kpi(),
    ]


def _build_profile_semantic_kpi(
    *,
    name: str,
    numerator: int,
    denominator: int,
    description: str,
    regressions: list[str],
) -> dict[str, object]:
    value_pct = 100.0 if denominator == 0 else round((numerator * 100 / denominator), 2)
    return {
        "surface": PROFILE_SEMANTICS_SURFACE,
        "name": name,
        "description": description,
        "numerator": numerator,
        "denominator": denominator,
        "value_pct": value_pct,
        "regressions": regressions,
    }


def build_profile_semantic_invariants() -> list[dict[str, object]]:
    """Return shipped-profile semantic invariants derived from active profile contracts."""
    meta_total = 0
    meta_ok = 0
    set_like_total = 0
    set_like_ok = 0
    non_meta_total = 0
    non_meta_ok = 0
    meta_regressions: list[str] = []
    set_like_regressions: list[str] = []
    non_meta_passthrough_regressions: list[str] = []

    for (provider, entity), profile in sorted(NORMALIZATION_PROFILE_REGISTRY.items()):
        for field_name, rule in sorted(profile.field_rules.items()):
            location = f"{provider}.{entity}.{field_name}"
            if field_name in profile.meta_fields:
                meta_total += 1
                if (
                    rule.normalizer is normalize_profile_passthrough
                    and not rule.include_in_hash
                ):
                    meta_ok += 1
                else:
                    meta_regressions.append(
                        f"{location} -> {getattr(rule.normalizer, '__name__', type(rule.normalizer).__name__)}"
                    )
                continue

            non_meta_total += 1
            if rule.normalizer is normalize_profile_passthrough:
                non_meta_passthrough_regressions.append(location)
            else:
                non_meta_ok += 1

            if rule.set_like:
                set_like_total += 1
                if rule.normalizer is normalize_profile_json_string:
                    set_like_ok += 1
                else:
                    set_like_regressions.append(
                        f"{location} -> {getattr(rule.normalizer, '__name__', type(rule.normalizer).__name__)}"
                    )

    return [
        _build_profile_semantic_kpi(
            name=PROFILE_META_PASSTHROUGH_KPI,
            numerator=meta_ok,
            denominator=meta_total,
            description=(
                "Shipped profile meta fields must use passthrough semantics and stay excluded from content_hash."
            ),
            regressions=meta_regressions,
        ),
        _build_profile_semantic_kpi(
            name=PROFILE_SET_LIKE_JSON_STRING_KPI,
            numerator=set_like_ok,
            denominator=set_like_total,
            description=(
                "Shipped profile set-like fields must canonicalize through the JSON-string normalizer family."
            ),
            regressions=set_like_regressions,
        ),
        _build_profile_semantic_kpi(
            name=PROFILE_NON_META_PASSTHROUGH_FREE_KPI,
            numerator=non_meta_ok,
            denominator=non_meta_total,
            description=(
                "Non-meta shipped profile fields must not silently fall through the passthrough seam."
            ),
            regressions=non_meta_passthrough_regressions,
        ),
    ]


def render_csv(rows: list[dict[str, str]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=list(CSV_COLUMNS),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def render_markdown(rows: list[dict[str, str]]) -> str:
    headers = list(CSV_COLUMNS)
    surface_kpis = build_surface_coverage_kpis(rows)
    semantic_kpis = build_profile_semantic_invariants()
    lines = [
        "# Pipeline Normalization Field Matrix",
        "",
        "Generated from active pipeline configs, Silver schemas, and current normalization code paths.",
        "",
        "This matrix is a normalization inventory, not a persisted-row publication contract.",
        "Occurrence-scoped provenance fields may appear here because normalization or config policy still references them,",
        "but canonical Silver/Gold row contracts are defined by provider references and Gold contract exports.",
        "",
        "## Surface Coverage Summary",
        "",
        "Entity coverage is entity-scoped only; composite join-key and control-plane surfaces are reported separately below.",
        "",
    ]
    for kpi in surface_kpis:
        lines.append(
            f"- {kpi['surface']} / {kpi['name']}: `{kpi['value_pct']:.2f}%` "
            f"(`{kpi['numerator']}` / `{kpi['denominator']}`) {kpi['description']}"
        )
    lines.extend(["", "## Semantic Invariant Summary", ""])
    for kpi in semantic_kpis:
        regressions = list(kpi.get("regressions", []))
        regression_note = (
            f" Regressions: {', '.join(regressions)}."
            if regressions
            else ""
        )
        lines.append(
            f"- {kpi['surface']} / {kpi['name']}: `{kpi['value_pct']:.2f}%` "
            f"(`{kpi['numerator']}` / `{kpi['denominator']}`) {kpi['description']}"
            f"{regression_note}"
        )
    lines.extend(
        [
            "",
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
    )
    for row in rows:
        lines.append("| " + " | ".join(row[header] for header in headers) + " |")
    lines.append("")
    return "\n".join(lines)


def build_artifacts() -> dict[str, str]:
    rows = build_field_matrix_rows()
    return {
        CSV_NAME: render_csv(rows),
        MD_NAME: render_markdown(rows),
    }


def write_artifacts(out_dir: Path) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts = build_artifacts()
    rows = build_field_matrix_rows()
    surface_kpis = build_surface_coverage_kpis(rows)
    semantic_kpis = build_profile_semantic_invariants()
    for name, payload in artifacts.items():
        (out_dir / name).write_text(payload, encoding="utf-8")
    return {
        "out_dir": str(out_dir),
        "rows": len(rows),
        "coverage_kpi": surface_kpis[0],
        "surface_kpis": surface_kpis,
        "semantic_kpis": semantic_kpis,
    }


def check_artifacts(out_dir: Path) -> int:
    artifacts = build_artifacts()
    for name, payload in artifacts.items():
        path = out_dir / name
        if not path.exists():
            return 1
        if path.read_text(encoding="utf-8") != payload:
            return 1
    return 0


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate deterministic normalization field-matrix artifacts for all pipelines."
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Output directory for generated artifacts.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with status 1 when artifacts on disk differ from generated output.",
    )
    return parser


def main() -> int:
    args = _arg_parser().parse_args()
    out_dir = args.out_dir.resolve()
    if args.check:
        return check_artifacts(out_dir)
    result = write_artifacts(out_dir)
    print(yaml.safe_dump(result, sort_keys=False), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
