"""Generate a semantic field-equivalence audit across BioETL pipelines."""

from __future__ import annotations

import csv
import importlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from bioetl.domain.normalization.profiles.registry import (
    NORMALIZATION_PROFILE_MODULE_PATHS,
    NORMALIZATION_PROFILE_REGISTRY,
)

ROOT = Path(__file__).resolve().parents[3]
CONFIGS_DIR = ROOT / "configs"
ENTITY_CONFIGS_DIR = CONFIGS_DIR / "entities"
COMPOSITE_CONFIGS_DIR = CONFIGS_DIR / "composites"
COMPOSITE_QUALITY_DIR = CONFIGS_DIR / "quality" / "entities" / "composite"
FIELD_REGISTRY_PATH = CONFIGS_DIR / "field_registry" / "canonical_registry.json"
CONTRACT_REGISTRY_PATH = CONFIGS_DIR / "base" / "contract_registry.yaml"
REPORTS_DIR = ROOT / "reports" / "quality"

REPORT_STEM = "pipeline_semantic_audit_20260515"
REPORT_PATH = REPORTS_DIR / f"{REPORT_STEM}.md"
MATRIX_PATH = REPORTS_DIR / f"{REPORT_STEM}_pairwise_matrix.csv"
CLUSTERS_PATH = REPORTS_DIR / f"{REPORT_STEM}_clusters.json"
CRITICAL_PATH = REPORTS_DIR / f"{REPORT_STEM}_critical_inconsistencies.md"
RECOMMENDED_FIELDS_PATH = (
    REPORTS_DIR / f"{REPORT_STEM}_recommended_canonical_fields.csv"
)

ADR_REFERENCES = {
    "ADR-018": "docs/02-architecture/decisions/ADR-018-gold-strict-validation.md",
    "ADR-026": "docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md",
    "ADR-035": "docs/02-architecture/decisions/ADR-035-json-field-typing-policy.md",
    "ADR-039": "docs/02-architecture/decisions/ADR-039-unified-entity-config-format.md",
    "ADR-045": "docs/02-architecture/decisions/ADR-045-dq-contract-system.md",
}

SYSTEM_FIELDS_EXCLUDED = frozenset(
    {
        "_dq_error",
        "_dq_warn",
        "_index",
        "_ingestion_ts",
        "_lookup_method",
        "_original_id",
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_state",
    }
)
FIELDS_ALWAYS_INCLUDE = frozenset({"entity_id", "content_hash", "_source"})


@dataclass(frozen=True, slots=True)
class PipelineDescriptor:
    pipeline_name: str
    provider: str
    entity: str
    kind: str
    config_path: Path
    quality_path: Path | None
    transformer_paths: tuple[str, ...]
    schema_module: str | None
    schema_class_name: str | None
    gold_contract_module: str | None
    gold_contract_class_name: str | None
    contract_ref: str


@dataclass(frozen=True, slots=True)
class ValidationSignature:
    field_rules: tuple[str, ...]
    cross_field_rules: tuple[str, ...]
    conditional_rules: tuple[str, ...]
    silver_nullable: bool | None
    silver_checks: tuple[str, ...]
    gold_nullable: bool | None
    gold_checks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TypingSignature:
    silver_dtype: str | None
    silver_nullable: bool | None
    gold_dtype: str | None
    gold_nullable: bool | None


@dataclass(frozen=True, slots=True)
class NormalizationSignature:
    profile_name: str | None
    profile_hash: str | None
    profile_module_path: str | None
    normalizer_ref: str | None
    include_in_hash: bool | None
    set_like: bool | None
    notes: str | None


@dataclass(frozen=True, slots=True)
class FieldSurface:
    pipeline_name: str
    provider: str
    entity: str
    kind: str
    field_name: str
    config_path: str
    quality_path: str | None
    transformer_paths: tuple[str, ...]
    schema_path: str | None
    gold_contract_path: str | None
    contract_ref: str
    column_groups: tuple[str, ...]
    join_roles: tuple[str, ...]
    normalization: NormalizationSignature
    validation: ValidationSignature
    typing: TypingSignature
    dq_policy_ref: str | None
    normalization_profile_ref: str | None
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SemanticClusterEntry:
    cluster_id: str
    canonical_name: str
    semantic_name: str
    source: str
    fields: tuple[FieldSurface, ...]
    notes: str


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _rel(path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _load_contract_registry() -> dict[str, dict[str, Any]]:
    payload = _load_yaml(CONTRACT_REGISTRY_PATH)
    entries = payload.get("entries", {})
    if not isinstance(entries, dict):
        raise ValueError("contract registry entries must be a mapping")
    return entries


def _load_canonical_registry() -> list[dict[str, Any]]:
    payload = json.loads(FIELD_REGISTRY_PATH.read_text(encoding="utf-8"))
    clusters = payload.get("clusters", [])
    if not isinstance(clusters, list):
        raise ValueError("canonical_registry clusters must be a list")
    return [cluster for cluster in clusters if isinstance(cluster, dict)]


def _entity_config_paths() -> list[Path]:
    return sorted(ENTITY_CONFIGS_DIR.glob("*/*.yaml"))


def _composite_config_paths() -> list[Path]:
    return sorted(
        path for path in COMPOSITE_CONFIGS_DIR.glob("*.yaml") if path.is_file()
    )


def _schema_module_for(provider: str, entity: str) -> tuple[str | None, str | None]:
    mapping = {
        ("chembl", "activity"): (
            "bioetl.domain.schemas.chembl.activity",
            "ActivitySchema",
        ),
        ("chembl", "assay"): ("bioetl.domain.schemas.chembl.assay", "AssaySchema"),
        ("chembl", "assay_parameters"): (
            "bioetl.domain.schemas.chembl.assay_parameters",
            "AssayParametersSchema",
        ),
        ("chembl", "cell_line"): (
            "bioetl.domain.schemas.chembl.cell_line",
            "CellLineSchema",
        ),
        ("chembl", "compound_record"): (
            "bioetl.domain.schemas.chembl.compound_record",
            "CompoundRecordSchema",
        ),
        ("chembl", "molecule"): (
            "bioetl.domain.schemas.chembl.molecule",
            "MoleculeSchema",
        ),
        ("chembl", "protein_class"): (
            "bioetl.domain.schemas.chembl.protein_classification",
            "ProteinClassificationSchema",
        ),
        ("chembl", "publication"): (
            "bioetl.domain.schemas.chembl.publication",
            "ChemblPublicationSchema",
        ),
        ("chembl", "publication_similarity"): (
            "bioetl.domain.schemas.chembl.publication_similarity",
            "PublicationSimilaritySchema",
        ),
        ("chembl", "publication_term"): (
            "bioetl.domain.schemas.chembl.publication_term",
            "PublicationTermSchema",
        ),
        ("chembl", "subcellular_fraction"): (
            "bioetl.domain.schemas.chembl.subcellular_fraction",
            "SubcellularFractionSchema",
        ),
        ("chembl", "target"): (
            "bioetl.domain.schemas.chembl.target",
            "TargetSchema",
        ),
        ("chembl", "target_component"): (
            "bioetl.domain.schemas.chembl.target_component",
            "TargetComponentSchema",
        ),
        ("chembl", "tissue"): ("bioetl.domain.schemas.chembl.tissue", "TissueSchema"),
        ("crossref", "publication"): (
            "bioetl.domain.schemas.crossref.publication",
            "PublicationEnrichedSchema",
        ),
        ("openalex", "publication"): (
            "bioetl.domain.schemas.openalex.publication",
            "OpenAlexPublicationSchema",
        ),
        ("pubchem", "compound"): (
            "bioetl.domain.schemas.pubchem.compound",
            "PubchemMoleculeSchema",
        ),
        ("pubmed", "publication"): (
            "bioetl.domain.schemas.pubmed.publication",
            "PubMedPublicationSchema",
        ),
        ("semanticscholar", "publication"): (
            "bioetl.domain.schemas.semanticscholar.publication",
            "SemanticScholarPublicationSchema",
        ),
        ("uniprot", "idmapping"): (
            "bioetl.domain.schemas.uniprot.idmapping",
            "IDMappingSchema",
        ),
        ("uniprot", "protein"): (
            "bioetl.domain.schemas.uniprot.protein",
            "UniprotTargetSchema",
        ),
    }
    return mapping.get((provider, entity), (None, None))


def _gold_contract_for(
    provider: str, entity: str, kind: str
) -> tuple[str | None, str | None]:
    mapping = {
        ("chembl", "activity", "entity"): (
            "bioetl.domain.contracts.gold.chembl",
            "ChEMBLActivityGoldSchema",
        ),
        ("chembl", "assay", "entity"): (
            "bioetl.domain.contracts.gold.chembl",
            "ChEMBLAssayGoldSchema",
        ),
        ("chembl", "assay_parameters", "entity"): (
            "bioetl.domain.contracts.gold.chembl",
            "ChEMBLAssayParametersGoldSchema",
        ),
        ("chembl", "cell_line", "entity"): (
            "bioetl.domain.contracts.gold.chembl",
            "ChEMBLCellLineGoldSchema",
        ),
        ("chembl", "compound_record", "entity"): (
            "bioetl.domain.contracts.gold.chembl",
            "ChEMBLCompoundRecordGoldSchema",
        ),
        ("chembl", "molecule", "entity"): (
            "bioetl.domain.contracts.gold.chembl",
            "ChEMBLMoleculeGoldSchema",
        ),
        ("chembl", "protein_class", "entity"): (
            "bioetl.domain.contracts.gold.chembl",
            "ChEMBLProteinClassGoldSchema",
        ),
        ("chembl", "publication", "entity"): (
            "bioetl.domain.contracts.gold.chembl",
            "ChEMBLPublicationGoldSchema",
        ),
        ("chembl", "publication_similarity", "entity"): (
            "bioetl.domain.contracts.gold.chembl",
            "ChEMBLPublicationSimilarityGoldSchema",
        ),
        ("chembl", "publication_term", "entity"): (
            "bioetl.domain.contracts.gold.chembl",
            "ChEMBLPublicationTermGoldSchema",
        ),
        ("chembl", "subcellular_fraction", "entity"): (
            "bioetl.domain.contracts.gold._chembl_target_lookup_schemas",
            "ChEMBLSubcellularFractionGoldSchema",
        ),
        ("chembl", "target", "entity"): (
            "bioetl.domain.contracts.gold._chembl_target_lookup_schemas",
            "ChEMBLTargetGoldSchema",
        ),
        ("chembl", "target_component", "entity"): (
            "bioetl.domain.contracts.gold._chembl_target_lookup_schemas",
            "ChEMBLTargetComponentGoldSchema",
        ),
        ("chembl", "tissue", "entity"): (
            "bioetl.domain.contracts.gold._chembl_target_lookup_schemas",
            "ChEMBLTissueGoldSchema",
        ),
        ("crossref", "publication", "entity"): (
            "bioetl.domain.contracts.gold.publications",
            "CrossRefPublicationGoldSchema",
        ),
        ("openalex", "publication", "entity"): (
            "bioetl.domain.contracts.gold.publications",
            "OpenAlexPublicationGoldSchema",
        ),
        ("pubchem", "compound", "entity"): (
            "bioetl.domain.contracts.gold.pubchem",
            "PubChemCompoundGoldSchema",
        ),
        ("pubmed", "publication", "entity"): (
            "bioetl.domain.contracts.gold.publications",
            "PubMedPublicationGoldSchema",
        ),
        ("semanticscholar", "publication", "entity"): (
            "bioetl.domain.contracts.gold.publications",
            "SemanticScholarPublicationGoldSchema",
        ),
        ("uniprot", "idmapping", "entity"): (
            "bioetl.domain.contracts.gold.uniprot",
            "UniProtIDMappingGoldSchema",
        ),
        ("uniprot", "protein", "entity"): (
            "bioetl.domain.contracts.gold.uniprot",
            "UniProtProteinGoldSchema",
        ),
        ("composite", "activity", "composite"): (
            "bioetl.domain.contracts.gold.composite",
            "CompositeActivityGoldSchema",
        ),
        ("composite", "assay", "composite"): (
            "bioetl.domain.contracts.gold.composite",
            "CompositeAssayGoldSchema",
        ),
        ("composite", "molecule", "composite"): (
            "bioetl.domain.contracts.gold.composite",
            "CompositeMoleculeGoldSchema",
        ),
        ("composite", "publication", "composite"): (
            "bioetl.domain.contracts.gold.composite",
            "CompositePublicationGoldSchema",
        ),
        ("composite", "target", "composite"): (
            "bioetl.domain.contracts.gold.composite",
            "CompositeTargetGoldSchema",
        ),
    }
    return mapping.get((provider, entity, kind), (None, None))


def _transformer_paths_for(
    provider: str,
    entity: str,
    kind: str,
) -> tuple[str, ...]:
    if kind == "composite":
        return ()
    candidates = {
        ("chembl", "activity"): (
            "src/bioetl/application/pipelines/chembl/activity_transformer.py",
        ),
        ("chembl", "assay"): (
            "src/bioetl/application/pipelines/chembl/assay_transformer.py",
        ),
        ("chembl", "assay_parameters"): (
            "src/bioetl/application/pipelines/chembl/assay_parameters_transformer.py",
        ),
        ("chembl", "cell_line"): (
            "src/bioetl/application/pipelines/chembl/cell_line_transformer.py",
        ),
        ("chembl", "compound_record"): (
            "src/bioetl/application/pipelines/chembl/compound_record_transformer.py",
        ),
        ("chembl", "molecule"): (
            "src/bioetl/application/pipelines/chembl/molecule_transformer.py",
        ),
        ("chembl", "protein_class"): (
            "src/bioetl/application/pipelines/chembl/protein_class_transformer.py",
        ),
        ("chembl", "publication"): (
            "src/bioetl/application/pipelines/chembl/publication_transformer.py",
        ),
        ("chembl", "publication_similarity"): (
            "src/bioetl/application/pipelines/chembl/publication_similarity_transformer.py",
        ),
        ("chembl", "publication_term"): (
            "src/bioetl/application/pipelines/chembl/publication_term_transformer.py",
        ),
        ("chembl", "subcellular_fraction"): (
            "src/bioetl/application/pipelines/chembl/subcellular_fraction_transformer.py",
        ),
        ("chembl", "target"): (
            "src/bioetl/application/pipelines/chembl/target_transformer.py",
        ),
        ("chembl", "target_component"): (
            "src/bioetl/application/pipelines/chembl/target_component_transformer.py",
        ),
        ("chembl", "tissue"): (
            "src/bioetl/application/pipelines/chembl/tissue_transformer.py",
        ),
        ("crossref", "publication"): (
            "src/bioetl/application/pipelines/crossref/transformer.py",
        ),
        ("openalex", "publication"): (
            "src/bioetl/application/pipelines/openalex/transformer.py",
        ),
        ("pubchem", "compound"): (
            "src/bioetl/application/pipelines/pubchem/transformer.py",
        ),
        ("pubmed", "publication"): (
            "src/bioetl/application/pipelines/pubmed/transformer.py",
        ),
        ("semanticscholar", "publication"): (
            "src/bioetl/application/pipelines/semanticscholar/transformer.py",
        ),
        ("uniprot", "idmapping"): (
            "src/bioetl/application/pipelines/uniprot/idmapping_transformer.py",
        ),
        ("uniprot", "protein"): (
            "src/bioetl/application/pipelines/uniprot/transformer.py",
            "src/bioetl/application/pipelines/uniprot/transformer_business_data_mixin.py",
        ),
    }
    return candidates.get((provider, entity), ())


def _build_pipeline_descriptors() -> list[PipelineDescriptor]:
    descriptors: list[PipelineDescriptor] = []
    for config_path in _entity_config_paths():
        payload = _load_yaml(config_path)
        provider = str(payload["provider"])
        entity = str(payload["entity"])
        pipeline_name = str(payload["pipeline"]["pipeline_name"])
        schema_module, schema_class_name = _schema_module_for(provider, entity)
        gold_module, gold_class_name = _gold_contract_for(provider, entity, "entity")
        descriptors.append(
            PipelineDescriptor(
                pipeline_name=pipeline_name,
                provider=provider,
                entity=entity,
                kind="entity",
                config_path=config_path,
                quality_path=None,
                transformer_paths=_transformer_paths_for(
                    provider,
                    entity,
                    "entity",
                ),
                schema_module=schema_module,
                schema_class_name=schema_class_name,
                gold_contract_module=gold_module,
                gold_contract_class_name=gold_class_name,
                contract_ref=f"{provider}.{entity}",
            )
        )
    for config_path in _composite_config_paths():
        entity = config_path.stem
        pipeline_name = f"composite_{entity}"
        quality_path = COMPOSITE_QUALITY_DIR / f"{entity}.yaml"
        gold_module, gold_class_name = _gold_contract_for(
            "composite", entity, "composite"
        )
        descriptors.append(
            PipelineDescriptor(
                pipeline_name=pipeline_name,
                provider="composite",
                entity=entity,
                kind="composite",
                config_path=config_path,
                quality_path=quality_path if quality_path.exists() else None,
                transformer_paths=(),
                schema_module=None,
                schema_class_name=None,
                gold_contract_module=gold_module,
                gold_contract_class_name=gold_class_name,
                contract_ref=f"composite.{entity}",
            )
        )
    return sorted(descriptors, key=lambda item: item.pipeline_name)


def _load_schema_columns(
    module_path: str | None, class_name: str | None
) -> dict[str, dict[str, Any]]:
    if module_path is None or class_name is None:
        return {}
    module = importlib.import_module(module_path)
    schema_cls = getattr(module, class_name, None)
    if schema_cls is None:
        return {}
    schema = schema_cls.to_schema()
    columns: dict[str, dict[str, Any]] = {}
    for name, column in schema.columns.items():
        checks = tuple(type(check).__name__ for check in getattr(column, "checks", ()))
        columns[name] = {
            "dtype": str(getattr(column, "dtype", None)),
            "nullable": bool(getattr(column, "nullable", False)),
            "checks": checks,
        }
    return columns


def _load_gold_columns(
    module_path: str | None, class_name: str | None
) -> dict[str, dict[str, Any]]:
    if module_path is None or class_name is None:
        return {}
    module = importlib.import_module(module_path)
    schema_cls = getattr(module, class_name, None)
    if schema_cls is None:
        return {}
    schema = schema_cls.to_schema()
    columns: dict[str, dict[str, Any]] = {}
    for name, column in schema.columns.items():
        checks = tuple(type(check).__name__ for check in getattr(column, "checks", ()))
        columns[name] = {
            "dtype": str(getattr(column, "dtype", None)),
            "nullable": bool(getattr(column, "nullable", False)),
            "checks": checks,
        }
    return columns


def _load_normalization_profile(
    provider: str, entity: str
) -> tuple[Any | None, str | None]:
    profile = NORMALIZATION_PROFILE_REGISTRY.get((provider, entity))
    module_path = NORMALIZATION_PROFILE_MODULE_PATHS.get((provider, entity))
    return profile, module_path


def _read_entity_quality_rules(
    payload: dict[str, Any], field_name: str
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    quality = payload.get("quality", {})
    field_validations = quality.get("entity_field_validations", [])
    cross_field_validations = quality.get("entity_cross_field_validations", [])
    conditional_validations = quality.get("entity_conditional_validations", [])
    field_rules: list[str] = []
    for rule in field_validations:
        if isinstance(rule, dict) and rule.get("field") == field_name:
            normalized = {
                key: value
                for key, value in rule.items()
                if key not in {"error_message", "description"}
            }
            field_rules.append(
                json.dumps(normalized, sort_keys=True, ensure_ascii=False)
            )
    cross_rules: list[str] = []
    for rule in cross_field_validations:
        if isinstance(rule, dict) and field_name in tuple(rule.get("fields", ())):
            cross_rules.append(json.dumps(rule, sort_keys=True, ensure_ascii=False))
    conditional_rules_out: list[str] = []
    for rule in conditional_validations:
        if not isinstance(rule, dict):
            continue
        if rule.get("condition_field") == field_name:
            conditional_rules_out.append(
                json.dumps(rule, sort_keys=True, ensure_ascii=False)
            )
            continue
        then_validations = rule.get("then_validations", [])
        if any(
            isinstance(validation, dict) and validation.get("field") == field_name
            for validation in then_validations
        ):
            conditional_rules_out.append(
                json.dumps(rule, sort_keys=True, ensure_ascii=False)
            )
    return (
        tuple(sorted(field_rules)),
        tuple(sorted(cross_rules)),
        tuple(sorted(conditional_rules_out)),
    )


def _read_composite_quality_rules(
    payload: dict[str, Any], field_name: str
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    dq_overrides = payload.get("dq_overrides", {})
    field_validations = dq_overrides.get("entity_field_validations", {})
    rule = field_validations.get(field_name)
    if isinstance(rule, dict):
        normalized = json.dumps(rule, sort_keys=True, ensure_ascii=False)
        return (normalized,), (), ()
    return (), (), ()


def _read_column_groups(
    payload: dict[str, Any], field_name: str, kind: str
) -> tuple[str, ...]:
    if kind == "entity":
        groups = payload.get("schema", {}).get("column_groups", [])
        names: list[str] = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            fields = group.get("fields", [])
            if isinstance(fields, list) and field_name in fields:
                name = group.get("name")
                if isinstance(name, str):
                    names.append(name)
        return tuple(sorted(set(names)))
    composite = payload.get("composite", {})
    merge = composite.get("merge", {})
    groups = merge.get("column_groups", [])
    names = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        fields = group.get("fields", [])
        if isinstance(fields, list) and field_name in fields:
            name = group.get("name")
            if isinstance(name, str):
                names.append(name)
    return tuple(sorted(set(names)))


def _join_roles_for_entity(
    payload: dict[str, Any], field_name: str, profile: Any | None
) -> tuple[str, ...]:
    roles: set[str] = set()
    pipeline = payload.get("pipeline", {})
    contracts = payload.get("contracts", {})
    pk = tuple(pipeline.get("business_primary_keys", ())) + tuple(
        contracts.get("primary_key", ())
    )
    merge_keys = tuple(contracts.get("merge_keys", ()))
    if field_name in pk:
        roles.add("PK")
    if field_name in merge_keys:
        roles.add("DEDUP_KEY")
        roles.add("FK_OR_MERGE_KEY")
    if profile is not None:
        if field_name in getattr(profile, "hash_included_fields", frozenset()):
            roles.add("CONTENT_HASH_SOURCE")
        if field_name in getattr(profile, "meta_fields", frozenset()):
            roles.add("LINEAGE_META")
    if field_name.endswith("_id") or field_name in {
        "doi",
        "pmid",
        "pmc_id",
        "inchi_key",
    }:
        roles.add("IDENTIFIER")
    return tuple(sorted(roles))


def _join_roles_for_composite(
    payload: dict[str, Any], field_name: str
) -> tuple[str, ...]:
    roles: set[str] = set()
    composite = payload.get("composite", {})
    seed_output_keys = tuple(composite.get("seed", {}).get("output_keys", ()))
    if field_name in seed_output_keys:
        roles.add("SEED_OUTPUT_KEY")
        roles.add("LINEAGE_ANCHOR")
    for dependency in tuple(composite.get("dependencies", ())):
        if isinstance(dependency, dict):
            if field_name in tuple(dependency.get("join_keys", ())):
                roles.add("COMPOSITE_JOIN_KEY")
            if field_name in tuple(dependency.get("filter_fields", ())):
                roles.add("FILTER_KEY")
    for enricher in tuple(composite.get("enrichers", ())):
        if isinstance(enricher, dict) and field_name in tuple(
            enricher.get("join_keys", ())
        ):
            roles.add("COMPOSITE_JOIN_KEY")
    priorities = composite.get("merge", {}).get("field_priorities", {})
    if field_name in priorities:
        roles.add("FIELD_PRIORITY_KEY")
    normalized_join = composite.get("normalized_join_key_policy", {})
    for policy in normalized_join.values():
        if not isinstance(policy, dict):
            continue
        if field_name in tuple(policy.get("primary_join_keys", ())):
            roles.add("COMPOSITE_JOIN_KEY")
        if field_name in tuple(policy.get("fallback_join_keys", ())):
            roles.add("FALLBACK_JOIN_KEY")
    normalized_anchor = composite.get("normalized_anchor_policy", {})
    for policy in normalized_anchor.values():
        if not isinstance(policy, dict):
            continue
        join_boundary = policy.get("join_boundary", {})
        if not isinstance(join_boundary, dict):
            continue
        if field_name in tuple(join_boundary.get("active_join_keys", ())):
            roles.add("COMPOSITE_JOIN_KEY")
        if field_name in tuple(join_boundary.get("retained_validation_anchors", ())):
            roles.add("LINEAGE_ANCHOR")
            roles.add("VALIDATION_ANCHOR")
    if field_name in {"entity_id", "content_hash", "_source"}:
        roles.add("LINEAGE_META")
    return tuple(sorted(roles))


def _normalization_signature_for(
    *,
    provider: str,
    entity: str,
    kind: str,
    field_name: str,
    payload: dict[str, Any],
) -> NormalizationSignature:
    if kind == "entity":
        profile, module_path = _load_normalization_profile(provider, entity)
        if profile is None:
            return NormalizationSignature(
                None, None, module_path, None, None, None, None
            )
        field_identity = profile.field_identity(field_name)
        rule = profile.rule_for(field_name)
        return NormalizationSignature(
            profile_name=profile.identity.profile_name,
            profile_hash=profile.identity.profile_hash,
            profile_module_path=module_path,
            normalizer_ref=None
            if field_identity is None
            else field_identity.normalizer_ref,
            include_in_hash=None if rule is None else rule.include_in_hash,
            set_like=None if rule is None else rule.set_like,
            notes=None if rule is None else rule.notes,
        )
    composite = payload.get("composite", {})
    alias_map = composite.get("field_aliases", {})
    note = None
    if field_name in alias_map:
        note = "composite_field_alias_registry"
    elif field_name in composite.get("merge", {}).get("field_priorities", {}):
        note = "composite_field_priority_registry"
    return NormalizationSignature(
        profile_name=None,
        profile_hash=None,
        profile_module_path=None,
        normalizer_ref=None,
        include_in_hash=None,
        set_like=None,
        notes=note,
    )


def _typing_signature_for(
    field_name: str,
    silver_columns: dict[str, dict[str, Any]],
    gold_columns: dict[str, dict[str, Any]],
) -> TypingSignature:
    silver = silver_columns.get(field_name, {})
    gold = gold_columns.get(field_name, {})
    return TypingSignature(
        silver_dtype=silver.get("dtype"),
        silver_nullable=silver.get("nullable"),
        gold_dtype=gold.get("dtype"),
        gold_nullable=gold.get("nullable"),
    )


def _validation_signature_for(
    *,
    field_name: str,
    payload: dict[str, Any],
    kind: str,
    silver_columns: dict[str, dict[str, Any]],
    gold_columns: dict[str, dict[str, Any]],
    quality_payload: dict[str, Any] | None,
) -> ValidationSignature:
    if kind == "entity":
        field_rules, cross_rules, conditional_rules = _read_entity_quality_rules(
            payload,
            field_name,
        )
    else:
        field_rules, cross_rules, conditional_rules = _read_composite_quality_rules(
            quality_payload or {},
            field_name,
        )
    silver = silver_columns.get(field_name, {})
    gold = gold_columns.get(field_name, {})
    return ValidationSignature(
        field_rules=field_rules,
        cross_field_rules=cross_rules,
        conditional_rules=conditional_rules,
        silver_nullable=silver.get("nullable"),
        silver_checks=tuple(silver.get("checks", ())),
        gold_nullable=gold.get("nullable"),
        gold_checks=tuple(gold.get("checks", ())),
    )


def _field_inventory_for_pipeline(
    descriptor: PipelineDescriptor,
    contract_registry: dict[str, dict[str, Any]],
) -> list[FieldSurface]:
    payload = _load_yaml(descriptor.config_path)
    quality_payload = (
        _load_yaml(descriptor.quality_path)
        if descriptor.quality_path is not None
        else None
    )
    silver_columns = _load_schema_columns(
        descriptor.schema_module, descriptor.schema_class_name
    )
    gold_columns = _load_gold_columns(
        descriptor.gold_contract_module,
        descriptor.gold_contract_class_name,
    )
    contract_entry = contract_registry.get(descriptor.contract_ref, {})
    if descriptor.kind == "entity":
        groups = payload.get("schema", {}).get("column_groups", [])
        fields = set()
        for group in groups:
            if not isinstance(group, dict):
                continue
            for field_name in group.get("fields", []):
                if isinstance(field_name, str):
                    fields.add(field_name)
        fields.update(silver_columns.keys())
        fields.update(gold_columns.keys())
        fields.update(
            rule["field"]
            for rule in payload.get("quality", {}).get("entity_field_validations", [])
            if isinstance(rule, dict) and isinstance(rule.get("field"), str)
        )
        fields.update(payload.get("pipeline", {}).get("business_primary_keys", []))
        fields.update(payload.get("contracts", {}).get("primary_key", []))
        fields.update(payload.get("contracts", {}).get("merge_keys", []))
    else:
        composite = payload.get("composite", {})
        merge = composite.get("merge", {})
        fields = set()
        for field_name in composite.get("seed", {}).get("output_keys", []):
            if isinstance(field_name, str):
                fields.add(field_name)
        for section in ("dependencies", "enrichers"):
            for item in composite.get(section, []):
                if not isinstance(item, dict):
                    continue
                for name in item.get("join_keys", []):
                    if isinstance(name, str):
                        fields.add(name)
                for name in item.get("filter_fields", []):
                    if isinstance(name, str):
                        fields.add(name)
        fields.update(merge.get("field_priorities", {}).keys())
        alias_map = composite.get("field_aliases", {})
        fields.update(alias_map.keys())
        for provider_fields in alias_map.values():
            if isinstance(provider_fields, dict):
                fields.update(provider_fields.values())
        for group in merge.get("column_groups", []):
            if isinstance(group, dict):
                fields.update(
                    field_name
                    for field_name in group.get("fields", [])
                    if isinstance(field_name, str)
                )
        if quality_payload:
            field_validations = quality_payload.get("dq_overrides", {}).get(
                "entity_field_validations", {}
            )
            if isinstance(field_validations, dict):
                fields.update(field_validations.keys())
        fields.update(gold_columns.keys())
    filtered_fields = sorted(
        field_name
        for field_name in fields
        if (
            field_name in FIELDS_ALWAYS_INCLUDE
            or (
                not field_name.startswith("_")
                and field_name not in SYSTEM_FIELDS_EXCLUDED
            )
        )
    )
    surfaces: list[FieldSurface] = []
    for field_name in filtered_fields:
        profile = NORMALIZATION_PROFILE_REGISTRY.get(
            (descriptor.provider, descriptor.entity)
        )
        join_roles = (
            _join_roles_for_entity(payload, field_name, profile)
            if descriptor.kind == "entity"
            else _join_roles_for_composite(payload, field_name)
        )
        normalization = _normalization_signature_for(
            provider=descriptor.provider,
            entity=descriptor.entity,
            kind=descriptor.kind,
            field_name=field_name,
            payload=payload,
        )
        validation = _validation_signature_for(
            field_name=field_name,
            payload=payload,
            kind=descriptor.kind,
            silver_columns=silver_columns,
            gold_columns=gold_columns,
            quality_payload=quality_payload,
        )
        typing = _typing_signature_for(
            field_name,
            silver_columns,
            gold_columns,
        )
        notes: list[str] = []
        if descriptor.kind == "composite" and field_name in payload.get(
            "composite", {}
        ).get("field_aliases", {}):
            notes.append("configured_as_composite_alias_canonical_name")
        if field_name in contract_entry.get("identity", {}):
            notes.append("appears_in_contract_identity")
        surfaces.append(
            FieldSurface(
                pipeline_name=descriptor.pipeline_name,
                provider=descriptor.provider,
                entity=descriptor.entity,
                kind=descriptor.kind,
                field_name=field_name,
                config_path=_rel(descriptor.config_path) or str(descriptor.config_path),
                quality_path=_rel(descriptor.quality_path),
                transformer_paths=descriptor.transformer_paths,
                schema_path=descriptor.schema_module,
                gold_contract_path=descriptor.gold_contract_module,
                contract_ref=descriptor.contract_ref,
                column_groups=_read_column_groups(payload, field_name, descriptor.kind),
                join_roles=join_roles,
                normalization=normalization,
                validation=validation,
                typing=typing,
                dq_policy_ref=contract_entry.get("dq_policy_ref"),
                normalization_profile_ref=contract_entry.get(
                    "normalization_profile_ref"
                ),
                notes=tuple(notes),
            )
        )
    return surfaces


def _heuristic_cluster_id(field_name: str) -> str:
    return f"heuristic::{field_name}"


def _build_clusters(field_surfaces: list[FieldSurface]) -> list[SemanticClusterEntry]:
    by_field = defaultdict(list)
    for surface in field_surfaces:
        by_field[surface.field_name].append(surface)

    registry_clusters = _load_canonical_registry()
    field_to_cluster_id: dict[str, str] = {}
    cluster_metadata: dict[str, tuple[str, str, str, str]] = {}
    for cluster in registry_clusters:
        cluster_id = str(cluster["cluster_id"])
        canonical_name = str(cluster["canonical_name"])
        semantic_name = str(cluster["semantic_name"])
        notes = str(cluster.get("notes", ""))
        cluster_metadata[cluster_id] = (
            canonical_name,
            semantic_name,
            "canonical_registry",
            notes,
        )
        for name in [
            canonical_name,
            *cluster.get("legacy_names", []),
            *cluster.get("raw_provider_names", []),
        ]:
            if isinstance(name, str):
                field_to_cluster_id.setdefault(name, cluster_id)
    for field_name, surfaces in by_field.items():
        if field_name in field_to_cluster_id:
            continue
        if len({surface.pipeline_name for surface in surfaces}) < 2:
            continue
        cluster_id = _heuristic_cluster_id(field_name)
        field_to_cluster_id[field_name] = cluster_id
        cluster_metadata[cluster_id] = (
            field_name,
            f"Heuristic shared field '{field_name}'",
            "shared_field_name",
            "Derived from repeated canonical field name across pipelines.",
        )
    grouped: dict[str, list[FieldSurface]] = defaultdict(list)
    for surface in field_surfaces:
        cluster_id = field_to_cluster_id.get(surface.field_name)
        if cluster_id is not None:
            grouped[cluster_id].append(surface)
    clusters: list[SemanticClusterEntry] = []
    for cluster_id, surfaces in sorted(grouped.items()):
        canonical_name, semantic_name, source, notes = cluster_metadata[cluster_id]
        ordered = tuple(
            sorted(surfaces, key=lambda item: (item.pipeline_name, item.field_name))
        )
        clusters.append(
            SemanticClusterEntry(
                cluster_id=cluster_id,
                canonical_name=canonical_name,
                semantic_name=semantic_name,
                source=source,
                fields=ordered,
                notes=notes,
            )
        )
    return clusters


def _semantic_status(
    cluster: SemanticClusterEntry, left: FieldSurface, right: FieldSurface
) -> str:
    if cluster.source == "canonical_registry":
        if (
            left.field_name == cluster.canonical_name
            and right.field_name == cluster.canonical_name
        ):
            return "EXACT"
        return "PARTIAL"
    if left.field_name == right.field_name:
        return "EXACT"
    return "WEAK"


def _normalization_status(left: FieldSurface, right: FieldSurface) -> str:
    left_sig = left.normalization
    right_sig = right.normalization
    if (
        left_sig.normalizer_ref == right_sig.normalizer_ref
        and left_sig.include_in_hash == right_sig.include_in_hash
        and left_sig.set_like == right_sig.set_like
    ):
        return "IDENTICAL"
    if left_sig.normalizer_ref and right_sig.normalizer_ref:
        if left_sig.normalizer_ref == right_sig.normalizer_ref:
            return "COMPATIBLE"
        return "DIFFERENT"
    if left.kind == "composite" or right.kind == "composite":
        return "COMPATIBLE"
    return "DIFFERENT"


def _validation_status(left: FieldSurface, right: FieldSurface) -> str:
    left_sig = left.validation
    right_sig = right.validation
    if left_sig == right_sig:
        return "IDENTICAL"
    same_nullability = (
        left_sig.silver_nullable == right_sig.silver_nullable
        and left_sig.gold_nullable == right_sig.gold_nullable
    )
    if same_nullability and (
        set(left_sig.field_rules).issubset(right_sig.field_rules)
        or set(right_sig.field_rules).issubset(left_sig.field_rules)
    ):
        return "STRICTNESS_MISMATCH"
    if same_nullability:
        return "COMPATIBLE"
    return "DIFFERENT"


def _typing_status(left: FieldSurface, right: FieldSurface) -> str:
    left_sig = left.typing
    right_sig = right.typing
    if left_sig == right_sig:
        return "IDENTICAL"
    if (
        left_sig.gold_dtype == right_sig.gold_dtype
        and left_sig.gold_nullable == right_sig.gold_nullable
    ):
        return "COMPATIBLE"
    if (
        left_sig.gold_dtype
        and right_sig.gold_dtype
        and "str" in left_sig.gold_dtype.lower()
        and "object" in right_sig.gold_dtype.lower()
    ) or (
        right_sig.gold_dtype
        and left_sig.gold_dtype
        and "str" in right_sig.gold_dtype.lower()
        and "object" in left_sig.gold_dtype.lower()
    ):
        return "LOSSY"
    if (
        left_sig.silver_dtype == right_sig.silver_dtype
        or left_sig.gold_dtype == right_sig.gold_dtype
    ):
        return "COMPATIBLE"
    return "CONFLICTING"


def _drift_risk(
    semantic_status: str,
    normalization_status: str,
    validation_status: str,
    typing_status: str,
    left: FieldSurface,
    right: FieldSurface,
) -> str:
    keyish = any(
        role
        in {
            "PK",
            "FK_OR_MERGE_KEY",
            "COMPOSITE_JOIN_KEY",
            "LINEAGE_ANCHOR",
            "VALIDATION_ANCHOR",
        }
        for role in (*left.join_roles, *right.join_roles)
    )
    if semantic_status == "CONFLICTING" or typing_status == "CONFLICTING":
        return "CRITICAL"
    if keyish and (
        normalization_status in {"DIFFERENT", "CONFLICTING"}
        or validation_status in {"DIFFERENT", "STRICTNESS_MISMATCH"}
        or typing_status == "LOSSY"
    ):
        return "CRITICAL"
    if (
        normalization_status in {"DIFFERENT", "CONFLICTING"}
        or validation_status in {"DIFFERENT", "STRICTNESS_MISMATCH"}
        or typing_status in {"LOSSY", "CONFLICTING"}
    ):
        return "HIGH"
    if semantic_status in {"PARTIAL", "WEAK"}:
        return "MEDIUM"
    return "LOW"


def _pairwise_rows(clusters: list[SemanticClusterEntry]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for cluster in clusters:
        fields = list(cluster.fields)
        for index, left in enumerate(fields):
            for right in fields[index + 1 :]:
                semantic_status = _semantic_status(cluster, left, right)
                normalization_status = _normalization_status(left, right)
                validation_status = _validation_status(left, right)
                typing_status = _typing_status(left, right)
                drift_risk = _drift_risk(
                    semantic_status,
                    normalization_status,
                    validation_status,
                    typing_status,
                    left,
                    right,
                )
                rows.append(
                    {
                        "cluster_id": cluster.cluster_id,
                        "canonical_name": cluster.canonical_name,
                        "semantic_name": cluster.semantic_name,
                        "pipeline_a": left.pipeline_name,
                        "field_a": left.field_name,
                        "pipeline_b": right.pipeline_name,
                        "field_b": right.field_name,
                        "semantic_status": semantic_status,
                        "normalization_status": normalization_status,
                        "validation_status": validation_status,
                        "typing_status": typing_status,
                        "drift_risk": drift_risk,
                        "join_semantics_a": "|".join(left.join_roles),
                        "join_semantics_b": "|".join(right.join_roles),
                        "normalization_location_a": left.normalization.profile_module_path
                        or "",
                        "normalization_location_b": right.normalization.profile_module_path
                        or "",
                        "transformers_a": "|".join(left.transformer_paths),
                        "transformers_b": "|".join(right.transformer_paths),
                        "dq_policy_ref_a": left.dq_policy_ref or "",
                        "dq_policy_ref_b": right.dq_policy_ref or "",
                        "contract_ref_a": left.contract_ref,
                        "contract_ref_b": right.contract_ref,
                        "config_path_a": left.config_path,
                        "config_path_b": right.config_path,
                    }
                )
    return rows


def _critical_findings(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    critical = [
        row
        for row in rows
        if row["drift_risk"] in {"CRITICAL", "HIGH"}
        or row["semantic_status"] in {"WEAK"}
        or row["validation_status"] == "STRICTNESS_MISMATCH"
    ]
    return sorted(
        critical,
        key=lambda item: (
            {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[item["drift_risk"]],
            item["cluster_id"],
            item["pipeline_a"],
            item["pipeline_b"],
        ),
    )


def _architectural_violations(rows: list[dict[str, str]]) -> list[str]:
    findings: list[str] = []
    for row in rows:
        cluster = row["cluster_id"]
        if row["typing_status"] == "LOSSY":
            findings.append(
                f"- `{cluster}` violates `{ADR_REFERENCES['ADR-035']}` typing consistency: "
                f"`{row['pipeline_a']}.{row['field_a']}` vs `{row['pipeline_b']}.{row['field_b']}` are lossy."
            )
        if row["validation_status"] == "STRICTNESS_MISMATCH":
            findings.append(
                f"- `{cluster}` risks `{ADR_REFERENCES['ADR-018']}` / `{ADR_REFERENCES['ADR-045']}` drift: "
                f"strictness mismatch between `{row['pipeline_a']}` and `{row['pipeline_b']}`."
            )
        if (
            "COMPOSITE_JOIN_KEY"
            in {
                role
                for roles in (row["join_semantics_a"], row["join_semantics_b"])
                for role in roles.split("|")
                if role
            }
            and row["semantic_status"] != "EXACT"
        ):
            findings.append(
                f"- `{cluster}` weakens `{ADR_REFERENCES['ADR-026']}` composite join semantics: "
                f"`{row['pipeline_a']}.{row['field_a']}` vs "
                f"`{row['pipeline_b']}.{row['field_b']}` are "
                f"`{row['semantic_status']}`."
            )
    return tuple(dict.fromkeys(findings))[:25]


def _recommended_canonical_fields(
    clusters: list[SemanticClusterEntry],
) -> list[dict[str, str]]:
    items = []
    for cluster in clusters:
        items.append(
            {
                "cluster_id": cluster.cluster_id,
                "canonical_name": cluster.canonical_name,
                "semantic_name": cluster.semantic_name,
                "cluster_source": cluster.source,
                "pipeline_count": str(
                    len({field.pipeline_name for field in cluster.fields})
                ),
                "field_count": str(len(cluster.fields)),
                "notes": cluster.notes,
            }
        )
    return items


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def _write_markdown_report(
    *,
    descriptors: list[PipelineDescriptor],
    clusters: list[SemanticClusterEntry],
    rows: list[dict[str, str]],
    critical_rows: list[dict[str, str]],
) -> None:
    cluster_count = len(clusters)
    conflict_count = sum(1 for row in rows if row["semantic_status"] == "CONFLICTING")
    normalization_mismatches = sum(
        1 for row in rows if row["normalization_status"] in {"DIFFERENT", "CONFLICTING"}
    )
    validation_mismatches = sum(
        1
        for row in rows
        if row["validation_status"] in {"DIFFERENT", "STRICTNESS_MISMATCH"}
    )
    critical_risks = sum(1 for row in rows if row["drift_risk"] == "CRITICAL")
    arch_findings = _architectural_violations(rows)
    lines = [
        "# Pipeline Semantic Audit",
        "",
        f"- Generated at: `{datetime.now(UTC).isoformat()}`",
        f"- Scope: `{len(descriptors)}` pipelines (`21` entity, `5` composite)",
        f"- ADRs: `{', '.join(ADR_REFERENCES)}`",
        "",
        "## Executive Summary",
        "",
        f"- Semantic clusters: `{cluster_count}`",
        f"- Pairwise semantic rows: `{len(rows)}`",
        f"- Semantic conflicts: `{conflict_count}`",
        f"- Normalization mismatches: `{normalization_mismatches}`",
        f"- Validation mismatches: `{validation_mismatches}`",
        f"- Critical drift risks: `{critical_risks}`",
        "",
        "## Canonical Semantic Clusters",
        "",
    ]
    for cluster in clusters:
        lines.append(f"### {cluster.cluster_id}")
        lines.append("")
        lines.append(f"- Canonical name: `{cluster.canonical_name}`")
        lines.append(f"- Semantic name: {cluster.semantic_name}")
        lines.append(f"- Source: `{cluster.source}`")
        lines.append(f"- Notes: {cluster.notes}")
        lines.append("")
        lines.append(
            "| Pipeline | Field | Kind | Join Roles | Normalization Profile | DQ Policy |"
        )
        lines.append("|---|---|---|---|---|---|")
        for field in cluster.fields:
            lines.append(
                f"| `{field.pipeline_name}` | `{field.field_name}` | `{field.kind}` | "
                f"`{' | '.join(field.join_roles)}` | "
                f"`{field.normalization.profile_name or 'n/a'}` | "
                f"`{field.dq_policy_ref or 'n/a'}` |"
            )
        lines.append("")
    lines.extend(
        [
            "## Pairwise Matrix",
            "",
            f"Full UTF-8 CSV matrix: [{MATRIX_PATH.name}]({MATRIX_PATH})",
            "",
            "## Critical Findings",
            "",
        ]
    )
    for row in critical_rows[:50]:
        lines.append(
            f"- `{row['cluster_id']}`: `{row['pipeline_a']}.{row['field_a']}` vs "
            f"`{row['pipeline_b']}.{row['field_b']}` -> semantic=`{row['semantic_status']}`, "
            f"normalization=`{row['normalization_status']}`, validation=`{row['validation_status']}`, "
            f"typing=`{row['typing_status']}`, drift=`{row['drift_risk']}`"
        )
    lines.extend(
        [
            "",
            "## Architectural Violations",
            "",
            *(
                arch_findings
                or [
                    "- No hard ADR violation was auto-proven; remaining concerns "
                    "are drift-risk findings, not direct architecture-boundary "
                    "violations."
                ]
            ),
            "",
            "## Refactoring Recommendations",
            "",
            "1. Centralize semantic identity in `configs/field_registry/canonical_registry.json` "
            "for clusters still discovered only heuristically.",
            "2. Promote repeated alias mappings into shared domain registries "
            "instead of per-pipeline YAML only, especially for publication and "
            "molecule families.",
            "3. Unify DQ field validation surfaces for shared "
            "identifier/title/citation clusters to satisfy ADR-045 consistently "
            "across publication pipelines.",
            "4. Reduce Gold typing drift by enforcing ADR-035 JSON-string policy "
            "for every shared JSON-like publication field.",
            "5. For composite join keys, require registry-backed canonical names "
            "and explicit lineage-anchor semantics per ADR-026.",
            "6. Where strictness mismatches remain, extract shared validators or "
            "contract fragments instead of duplicating per-provider rules.",
            "",
            "## Generated Artifacts",
            "",
            f"- Markdown report: [{REPORT_PATH.name}]({REPORT_PATH})",
            f"- Pairwise matrix CSV: [{MATRIX_PATH.name}]({MATRIX_PATH})",
            f"- Semantic cluster registry JSON: [{CLUSTERS_PATH.name}]({CLUSTERS_PATH})",
            f"- Critical inconsistencies: [{CRITICAL_PATH.name}]({CRITICAL_PATH})",
            f"- Recommended canonical fields CSV: [{RECOMMENDED_FIELDS_PATH.name}]({RECOMMENDED_FIELDS_PATH})",
            "",
        ]
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def _write_critical_markdown(critical_rows: list[dict[str, str]]) -> None:
    lines = ["# Critical Inconsistencies", ""]
    for row in critical_rows:
        lines.extend(
            [
                f"## {row['cluster_id']}: {row['pipeline_a']}.{row['field_a']} vs {row['pipeline_b']}.{row['field_b']}",
                "",
                f"- Semantic status: `{row['semantic_status']}`",
                f"- Normalization: `{row['normalization_status']}`",
                f"- Validation: `{row['validation_status']}`",
                f"- Typing: `{row['typing_status']}`",
                f"- Drift risk: `{row['drift_risk']}`",
                f"- Join semantics A: `{row['join_semantics_a']}`",
                f"- Join semantics B: `{row['join_semantics_b']}`",
                f"- Config A: `{row['config_path_a']}`",
                f"- Config B: `{row['config_path_b']}`",
                "",
            ]
        )
    CRITICAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    CRITICAL_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    contract_registry = _load_contract_registry()
    descriptors = _build_pipeline_descriptors()
    surfaces: list[FieldSurface] = []
    for descriptor in descriptors:
        surfaces.extend(_field_inventory_for_pipeline(descriptor, contract_registry))
    clusters = _build_clusters(surfaces)
    rows = _pairwise_rows(clusters)
    critical_rows = _critical_findings(rows)
    cluster_payload = [
        {
            "cluster_id": cluster.cluster_id,
            "canonical_name": cluster.canonical_name,
            "semantic_name": cluster.semantic_name,
            "source": cluster.source,
            "notes": cluster.notes,
            "fields": [
                {
                    "pipeline_name": field.pipeline_name,
                    "field_name": field.field_name,
                    "kind": field.kind,
                    "join_roles": field.join_roles,
                    "config_path": field.config_path,
                    "quality_path": field.quality_path,
                    "transformer_paths": field.transformer_paths,
                    "schema_path": field.schema_path,
                    "gold_contract_path": field.gold_contract_path,
                    "contract_ref": field.contract_ref,
                    "dq_policy_ref": field.dq_policy_ref,
                    "normalization_profile_ref": field.normalization_profile_ref,
                    "normalization": {
                        "profile_name": field.normalization.profile_name,
                        "profile_hash": field.normalization.profile_hash,
                        "profile_module_path": field.normalization.profile_module_path,
                        "normalizer_ref": field.normalization.normalizer_ref,
                        "include_in_hash": field.normalization.include_in_hash,
                        "set_like": field.normalization.set_like,
                        "notes": field.normalization.notes,
                    },
                    "typing": {
                        "silver_dtype": field.typing.silver_dtype,
                        "silver_nullable": field.typing.silver_nullable,
                        "gold_dtype": field.typing.gold_dtype,
                        "gold_nullable": field.typing.gold_nullable,
                    },
                    "validation": {
                        "field_rules": field.validation.field_rules,
                        "cross_field_rules": field.validation.cross_field_rules,
                        "conditional_rules": field.validation.conditional_rules,
                        "silver_nullable": field.validation.silver_nullable,
                        "silver_checks": field.validation.silver_checks,
                        "gold_nullable": field.validation.gold_nullable,
                        "gold_checks": field.validation.gold_checks,
                    },
                }
                for field in cluster.fields
            ],
        }
        for cluster in clusters
    ]
    _write_json(CLUSTERS_PATH, cluster_payload)
    _write_csv(MATRIX_PATH, rows)
    _write_csv(RECOMMENDED_FIELDS_PATH, _recommended_canonical_fields(clusters))
    _write_critical_markdown(critical_rows)
    _write_markdown_report(
        descriptors=descriptors,
        clusters=clusters,
        rows=rows,
        critical_rows=critical_rows,
    )
    print(
        json.dumps(
            {
                "report": str(REPORT_PATH.relative_to(ROOT)),
                "matrix_csv": str(MATRIX_PATH.relative_to(ROOT)),
                "clusters_json": str(CLUSTERS_PATH.relative_to(ROOT)),
                "critical_md": str(CRITICAL_PATH.relative_to(ROOT)),
                "recommended_csv": str(RECOMMENDED_FIELDS_PATH.relative_to(ROOT)),
                "pipeline_count": len(descriptors),
                "cluster_count": len(clusters),
                "pairwise_rows": len(rows),
                "critical_rows": len(critical_rows),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
