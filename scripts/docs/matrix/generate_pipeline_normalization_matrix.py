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
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _bootstrap import ensure_repo_imports
else:
    from scripts.docs.matrix._bootstrap import ensure_repo_imports

ensure_repo_imports(include_src=True)

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
ENTITY_PIPELINE_KIND = "entity"
COMPOSITE_PIPELINE_KIND = "composite"
PROFILE_NORMALIZATION_SOURCE = "profile"
NO_NORMALIZER = "none"
FALSE_TEXT = "false"

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
CANONICAL_EFFECTIVE_CONFIG_HASH_RAW = (
    " SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA "
)
CANONICAL_CONTRACT_REF_RAW = " ChemBL.Activity "
CANONICAL_EFFECTIVE_CONFIG_HASH = (
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
)
CANONICAL_CONTRACT_REF = "chembl.activity"
CANONICAL_CONTRACT_VERSION = "2.0.0"
CANONICAL_MANIFEST_ID = "manifest-123"
CANONICAL_COMPOSITE_RUN_ID = "run-42"

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


class _ProfileSemanticStats:
    """Mutable counters for shipped-profile semantic invariants."""

    def __init__(self) -> None:
        self.meta_total = 0
        self.meta_ok = 0
        self.set_like_total = 0
        self.set_like_ok = 0
        self.non_meta_total = 0
        self.non_meta_ok = 0
        self.meta_regressions: list[str] = []
        self.set_like_regressions: list[str] = []
        self.non_meta_passthrough_regressions: list[str] = []


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
                _entity_profile_row(
                    pipeline_name=pipeline_name,
                    field_name=field_name,
                    field_type=field_type,
                    profile_rule=profile_rule,
                )
            )
            continue

        source, normalizer, summary = _fallback_contract(
            rule_set,
            field_name=field_name,
            field_type=field_type,
        )
        rows.append(
            _entity_fallback_row(
                pipeline_name=pipeline_name,
                field_name=field_name,
                field_type=field_type,
                source=source,
                normalizer=normalizer,
                summary=summary,
            )
        )
    return rows


def _entity_profile_row(
    *,
    pipeline_name: str,
    field_name: str,
    field_type: str,
    profile_rule: Any,
) -> dict[str, str]:
    """Build one entity matrix row sourced from an explicit profile rule."""
    notes = profile_rule.notes or ""
    return {
        "pipeline_name": pipeline_name,
        "pipeline_kind": ENTITY_PIPELINE_KIND,
        "field_name": field_name,
        "field_type": field_type,
        "normalization_source": PROFILE_NORMALIZATION_SOURCE,
        "normalizer": _normalizer_name(
            profile_rule.normalizer,
            field_name=field_name,
            notes=profile_rule.notes,
        ),
        "normalization_summary": notes,
        "include_in_content_hash": _render_bool(profile_rule.include_in_hash),
        "set_like": _render_bool(profile_rule.set_like),
        "notes": notes,
    }


def _entity_fallback_row(
    *,
    pipeline_name: str,
    field_name: str,
    field_type: str,
    source: str,
    normalizer: str,
    summary: str,
) -> dict[str, str]:
    """Build one entity matrix row sourced from fallback normalization policy."""
    return {
        "pipeline_name": pipeline_name,
        "pipeline_kind": ENTITY_PIPELINE_KIND,
        "field_name": field_name,
        "field_type": field_type,
        "normalization_source": source,
        "normalizer": normalizer,
        "normalization_summary": summary,
        "include_in_content_hash": "",
        "set_like": FALSE_TEXT,
        "notes": "",
    }


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
    for entries in _composite_join_key_entry_lists(composite):
        keys.update(_join_keys_from_entries(entries))
    return keys


def _composite_join_key_entry_lists(composite: dict[str, object]) -> list[list[object]]:
    """Return composite dependency/enricher entry lists that may declare join keys."""
    entry_lists: list[list[object]] = []
    for key in ("dependencies", "enrichers"):
        value = composite.get(key)
        if isinstance(value, list):
            entry_lists.append(value)
    return entry_lists


def _join_keys_from_entries(entries: list[object]) -> set[str]:
    """Extract declared join keys from composite dependency-like entries."""
    keys: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        join_keys = entry.get("join_keys")
        if not isinstance(join_keys, list):
            continue
        keys.update(key for key in join_keys if isinstance(key, str))
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
        rows.append(_composite_row(pipeline_name, field_name, join_keys))
    return rows


def _composite_row(
    pipeline_name: str,
    field_name: str,
    join_keys: set[str],
) -> dict[str, str]:
    """Build one composite matrix row."""
    source, normalizer, summary, notes = _composite_field_policy(field_name, join_keys)
    return {
        "pipeline_name": pipeline_name,
        "pipeline_kind": COMPOSITE_PIPELINE_KIND,
        "field_name": field_name,
        "field_type": COMPOSITE_GOLD_SCHEMA_TYPE_REGISTRY.get(
            pipeline_name, "unknown"
        ),
        "normalization_source": source,
        "normalizer": normalizer,
        "normalization_summary": summary,
        "include_in_content_hash": "",
        "set_like": FALSE_TEXT,
        "notes": notes,
    }


def _composite_field_policy(
    field_name: str,
    join_keys: set[str],
) -> tuple[str, str, str, str]:
    """Resolve normalization semantics for one composite field."""
    policy = JOIN_KEY_NORMALIZATION_POLICIES.get(field_name)
    if field_name not in join_keys or policy is None:
        return (
            "upstream_inherited",
            NO_NORMALIZER,
            (
                "No composite-specific field normalizer is defined; field is inherited "
                "from already-normalized upstream records."
            ),
            "Composite normalization is key-oriented; non-key fields preserve upstream semantics.",
        )
    return (
        "composite_join_key_policy",
        "join_key_policy",
        _normalize_summary_from_policy(
            key=field_name,
            trim=policy.trim,
            lowercase=policy.lowercase,
        ),
        "Applied only while resolving and comparing composite join keys.",
    )


def build_field_matrix_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    rows.extend(_entity_field_matrix_rows())
    rows.extend(_composite_field_matrix_rows())
    return rows


def _entity_field_matrix_rows() -> list[dict[str, str]]:
    """Build matrix rows for all shipped entity pipelines."""
    rows: list[dict[str, str]] = []
    for config_path in _entity_config_paths():
        pipeline_inputs = _entity_pipeline_inputs(config_path)
        if pipeline_inputs is None:
            continue
        pipeline_name, provider, entity, schema = pipeline_inputs
        rows.extend(
            _build_entity_rows_for_pipeline(
                pipeline_name=pipeline_name,
                provider=provider,
                entity=entity,
                schema=schema,
            )
        )
    return rows


def _entity_pipeline_inputs(
    config_path: Path,
) -> tuple[str, str, str, Any] | None:
    """Resolve matrix inputs for one entity pipeline config."""
    payload = _load_yaml(config_path)
    pipeline = payload.get("pipeline")
    if not isinstance(pipeline, dict):
        return None
    pipeline_name = str(pipeline.get("pipeline_name", "")).strip()
    if not pipeline_name:
        return None
    schema = ENTITY_SILVER_SCHEMA_REGISTRY.get(pipeline_name)
    if schema is None:
        raise ValueError(f"Missing Silver schema registry entry for {pipeline_name}")
    provider = str(payload.get("provider", "")).strip()
    entity = str(payload.get("entity", "")).strip()
    return pipeline_name, provider, entity, schema


def _composite_field_matrix_rows() -> list[dict[str, str]]:
    """Build matrix rows for all shipped composite pipelines."""
    rows: list[dict[str, str]] = []
    for config_path in _composite_config_paths():
        composite_inputs = _composite_pipeline_inputs(config_path)
        if composite_inputs is None:
            continue
        pipeline_name, payload = composite_inputs
        rows.extend(
            _build_composite_rows_for_pipeline(
                pipeline_name=pipeline_name,
                payload=payload,
            )
        )
    return rows


def _composite_pipeline_inputs(
    config_path: Path,
) -> tuple[str, dict[str, object]] | None:
    """Resolve matrix inputs for one composite pipeline config."""
    payload = _load_yaml(config_path)
    composite = payload.get("composite")
    if not isinstance(composite, dict):
        return None
    pipeline_name = str(composite.get("name", "")).strip()
    if not pipeline_name:
        return None
    return pipeline_name, payload


def build_entity_profile_coverage_kpi(
    rows: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    entity_rows = [
        row for row in (build_field_matrix_rows() if rows is None else rows)
        if row["pipeline_kind"] == ENTITY_PIPELINE_KIND
    ]
    entity_field_count = len(entity_rows)
    explicit_profile_field_count = sum(
        1
        for row in entity_rows
        if row["normalization_source"] == PROFILE_NORMALIZATION_SOURCE
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
        effective_config_hash=CANONICAL_EFFECTIVE_CONFIG_HASH_RAW,
        dq_contract_compatibility_hash=" DEADBEEF ",
        contract_ref=CANONICAL_CONTRACT_REF_RAW,
        contract_version=" v2 ",
        effective_config_artifact_id=" artifact-42 ",
        exact_replay=True,
        input_snapshot_fingerprint=" FACE ",
    )
    runtime_anchor_status = normalize_runtime_anchor_payload(
        {
            "effective_config_hash": CANONICAL_EFFECTIVE_CONFIG_HASH_RAW,
            "contract_ref": CANONICAL_CONTRACT_REF_RAW,
            "contract_version": " v2 ",
            "manifest_id": f" {CANONICAL_MANIFEST_ID} ",
            "composite_run_identity": f" {CANONICAL_COMPOSITE_RUN_ID} ",
        }
    )
    checkpoint_context = create_expected_checkpoint_context(
        effective_config_hash=CANONICAL_EFFECTIVE_CONFIG_HASH_RAW,
        contract_ref=CANONICAL_CONTRACT_REF_RAW,
        contract_version=" v2 ",
        manifest_id=f" {CANONICAL_MANIFEST_ID} ",
        composite_run_identity=f" {CANONICAL_COMPOSITE_RUN_ID} ",
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
        _control_plane_status(
            "run_manifest_spec",
            _manifest_status_covered(manifest_status),
        ),
        _control_plane_status(
            "run_ledger_payload",
            _ledger_status_covered(ledger_status),
        ),
        _control_plane_status(
            "execution_identity_payload",
            _execution_identity_status_covered(execution_identity_status),
        ),
        _control_plane_status(
            "runtime_anchor_payload",
            _runtime_anchor_status_covered(runtime_anchor_status),
        ),
        _control_plane_status(
            "checkpoint_expected_context",
            _checkpoint_context_covered(checkpoint_context),
        ),
        _control_plane_status(
            "checkpoint_anchor_merge",
            _checkpoint_anchor_merge_covered(merged_checkpoint),
        ),
    ]


def _control_plane_status(seam: str, covered: bool) -> dict[str, object]:
    """Build one control-plane normalization seam status row."""
    return {"seam": seam, "covered": covered}


def _manifest_status_covered(manifest_status: dict[str, object]) -> bool:
    """Return whether manifest normalization preserves canonical ordering/seams."""
    planned_artifacts = manifest_status.get("planned_artifacts", [])
    source_refs = manifest_status.get("source_refs", [])
    if not isinstance(planned_artifacts, list) or not isinstance(source_refs, list):
        return False
    return (
        manifest_status.get("code_provenance") == {"config_hash": "deadbeef"}
        and bool(planned_artifacts)
        and planned_artifacts[0].get("layer") == "bronze"
        and bool(source_refs)
        and _first_snapshot_id(source_refs) == "a"
    )


def _first_snapshot_id(source_refs: list[object]) -> str | None:
    """Return the first normalized snapshot id when present."""
    if not source_refs:
        return None
    first_source = source_refs[0]
    if not isinstance(first_source, dict):
        return None
    input_snapshots = first_source.get("input_snapshots")
    if not isinstance(input_snapshots, list) or not input_snapshots:
        return None
    first_snapshot = input_snapshots[0]
    if not isinstance(first_snapshot, dict):
        return None
    snapshot_id = first_snapshot.get("snapshot_id")
    return snapshot_id if isinstance(snapshot_id, str) else None


def _ledger_status_covered(ledger_status: dict[str, object]) -> bool:
    """Return whether ledger normalization preserves canonical ordering/format."""
    return (
        ledger_status.get("run_id") == "11111111-1111-1111-1111-111111111111"
        and ledger_status.get("occurred_at") == "2026-04-08T12:53:47Z"
        and ledger_status.get("metrics_snapshot") == {"records_a": 1, "records_b": 2}
    )


def _execution_identity_status_covered(
    execution_identity_status: dict[str, object],
) -> bool:
    """Return whether execution identity normalization produces canonical values."""
    return (
        execution_identity_status.get("contract_ref") == CANONICAL_CONTRACT_REF
        and execution_identity_status.get("contract_version")
        == CANONICAL_CONTRACT_VERSION
        and execution_identity_status.get("exact_replay") == "true"
    )


def _runtime_anchor_status_covered(runtime_anchor_status: dict[str, object]) -> bool:
    """Return whether runtime anchor normalization produces canonical values."""
    return (
        runtime_anchor_status.get("effective_config_hash")
        == CANONICAL_EFFECTIVE_CONFIG_HASH
        and runtime_anchor_status.get("contract_ref") == CANONICAL_CONTRACT_REF
        and runtime_anchor_status.get("contract_version")
        == CANONICAL_CONTRACT_VERSION
    )


def _checkpoint_context_covered(checkpoint_context: object) -> bool:
    """Return whether checkpoint context normalization preserves canonical anchors."""
    return (
        checkpoint_context.effective_config_hash
        == CANONICAL_EFFECTIVE_CONFIG_HASH
        and checkpoint_context.contract_ref == CANONICAL_CONTRACT_REF
        and checkpoint_context.contract_version == CANONICAL_CONTRACT_VERSION
    )


def _checkpoint_anchor_merge_covered(merged_checkpoint: object) -> bool:
    """Return whether merged checkpoint anchors preserve canonical values."""
    return (
        merged_checkpoint.effective_config_hash
        == CANONICAL_EFFECTIVE_CONFIG_HASH
        and merged_checkpoint.contract_ref == CANONICAL_CONTRACT_REF
        and merged_checkpoint.contract_version == CANONICAL_CONTRACT_VERSION
        and merged_checkpoint.manifest_id == CANONICAL_MANIFEST_ID
        and merged_checkpoint.composite_run_identity == CANONICAL_COMPOSITE_RUN_ID
    )


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
    stats = _ProfileSemanticStats()
    for (provider, entity), profile in sorted(NORMALIZATION_PROFILE_REGISTRY.items()):
        for field_name, rule in sorted(profile.field_rules.items()):
            _update_profile_semantic_stats(stats, provider, entity, profile, field_name, rule)

    return [
        _build_profile_semantic_kpi(
            name=PROFILE_META_PASSTHROUGH_KPI,
            numerator=stats.meta_ok,
            denominator=stats.meta_total,
            description=(
                "Shipped profile meta fields must use passthrough semantics and stay excluded from content_hash."
            ),
            regressions=stats.meta_regressions,
        ),
        _build_profile_semantic_kpi(
            name=PROFILE_SET_LIKE_JSON_STRING_KPI,
            numerator=stats.set_like_ok,
            denominator=stats.set_like_total,
            description=(
                "Shipped profile set-like fields must canonicalize through the JSON-string normalizer family."
            ),
            regressions=stats.set_like_regressions,
        ),
        _build_profile_semantic_kpi(
            name=PROFILE_NON_META_PASSTHROUGH_FREE_KPI,
            numerator=stats.non_meta_ok,
            denominator=stats.non_meta_total,
            description=(
                "Non-meta shipped profile fields must not silently fall through the passthrough seam."
            ),
            regressions=stats.non_meta_passthrough_regressions,
        ),
    ]


def _update_profile_semantic_stats(
    stats: _ProfileSemanticStats,
    provider: str,
    entity: str,
    profile: Any,
    field_name: str,
    rule: Any,
) -> None:
    """Update aggregate profile-semantic counters for one field rule."""
    location = _profile_rule_location(provider, entity, field_name)
    if field_name in profile.meta_fields:
        _update_meta_profile_semantics(stats, location, rule)
        return
    _update_non_meta_profile_semantics(stats, location, rule)


def _profile_rule_location(provider: str, entity: str, field_name: str) -> str:
    """Render stable provider.entity.field location for invariant reporting."""
    return f"{provider}.{entity}.{field_name}"


def _normalizer_regression(location: str, rule: Any) -> str:
    """Render one regression string with the effective normalizer name."""
    normalizer_name = getattr(rule.normalizer, "__name__", type(rule.normalizer).__name__)
    return f"{location} -> {normalizer_name}"


def _update_meta_profile_semantics(
    stats: _ProfileSemanticStats,
    location: str,
    rule: Any,
) -> None:
    """Update counters for shipped meta-field profile semantics."""
    stats.meta_total += 1
    if rule.normalizer is normalize_profile_passthrough and not rule.include_in_hash:
        stats.meta_ok += 1
        return
    stats.meta_regressions.append(_normalizer_regression(location, rule))


def _update_non_meta_profile_semantics(
    stats: _ProfileSemanticStats,
    location: str,
    rule: Any,
) -> None:
    """Update counters for shipped non-meta profile semantics."""
    stats.non_meta_total += 1
    if rule.normalizer is normalize_profile_passthrough:
        stats.non_meta_passthrough_regressions.append(location)
    else:
        stats.non_meta_ok += 1
    if not rule.set_like:
        return
    stats.set_like_total += 1
    if rule.normalizer is normalize_profile_json_string:
        stats.set_like_ok += 1
        return
    stats.set_like_regressions.append(_normalizer_regression(location, rule))


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
    lines = _markdown_intro_lines()
    lines.extend(_surface_kpi_lines(surface_kpis))
    lines.extend(_semantic_kpi_lines(semantic_kpis))
    lines.extend(_markdown_table_lines(rows, headers))
    lines.append("")
    return "\n".join(lines)


def _markdown_intro_lines() -> list[str]:
    """Render static markdown prelude for normalization matrix artifacts."""
    return [
        "# Pipeline Normalization Field Matrix",
        "",
        "Generated from active pipeline configs, Silver schemas, and current normalization code paths.",
        "",
        "This matrix is a normalization inventory, not a persisted-row publication contract.",
        (
            "Occurrence-scoped provenance fields may appear here because normalization "
            "or config policy still references them,"
        ),
        "but canonical Silver/Gold row contracts are defined by provider references and Gold contract exports.",
        "",
        "## Surface Coverage Summary",
        "",
        (
            "Entity coverage is entity-scoped only; composite join-key and "
            "control-plane surfaces are reported separately below."
        ),
        "",
    ]


def _surface_kpi_lines(surface_kpis: list[dict[str, object]]) -> list[str]:
    """Render surface coverage KPI bullet lines."""
    return [
        (
            f"- {kpi['surface']} / {kpi['name']}: `{kpi['value_pct']:.2f}%` "
            f"(`{kpi['numerator']}` / `{kpi['denominator']}`) {kpi['description']}"
        )
        for kpi in surface_kpis
    ]


def _semantic_kpi_lines(semantic_kpis: list[dict[str, object]]) -> list[str]:
    """Render semantic invariant KPI bullet lines."""
    lines = ["", "## Semantic Invariant Summary", ""]
    lines.extend(_semantic_kpi_line(kpi) for kpi in semantic_kpis)
    return lines


def _semantic_kpi_line(kpi: dict[str, object]) -> str:
    """Render one semantic invariant KPI line with optional regressions."""
    regressions = list(kpi.get("regressions", []))
    regression_note = (
        f" Regressions: {', '.join(regressions)}."
        if regressions
        else ""
    )
    return (
        f"- {kpi['surface']} / {kpi['name']}: `{kpi['value_pct']:.2f}%` "
        f"(`{kpi['numerator']}` / `{kpi['denominator']}`) {kpi['description']}"
        f"{regression_note}"
    )


def _markdown_table_lines(
    rows: list[dict[str, str]],
    headers: list[str],
) -> list[str]:
    """Render markdown table header and all matrix rows."""
    lines = [
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend(_markdown_table_row(row, headers) for row in rows)
    return lines


def _markdown_table_row(row: dict[str, str], headers: list[str]) -> str:
    """Render one markdown table row."""
    return "| " + " | ".join(row[header] for header in headers) + " |"


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
