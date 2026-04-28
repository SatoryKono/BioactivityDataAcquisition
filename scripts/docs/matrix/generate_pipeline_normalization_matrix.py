#!/usr/bin/env python3
# ruff: noqa: E402
"""Generate deterministic normalization field-matrix artifacts for all pipelines."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from datetime import UTC, datetime
from functools import cache
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

from bioetl.composition.bootstrap.runtime.normalization_policy_init import (
    initialize_chembl_policy_registry as initialize_bootstrap_chembl_policy_registry,
)

initialize_bootstrap_chembl_policy_registry(Path("configs"))

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
from bioetl.domain.normalization.profiles._chembl_policy_registry import (
    chembl_policy_surface,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_json_string,
    normalize_profile_json_string_strict,
    normalize_profile_passthrough,
)
from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.chembl.assay_parameters import AssayParametersSchema
from bioetl.domain.schemas.chembl.cell_line import CellLineSchema
from bioetl.domain.schemas.chembl.compound_record import CompoundRecordSchema
from bioetl.domain.schemas.chembl.molecule import MoleculeSchema
from bioetl.domain.schemas.chembl.protein_classification import (
    ProteinClassificationSchema,
)
from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema
from bioetl.domain.schemas.chembl.publication_similarity import (
    PublicationSimilaritySchema,
)
from bioetl.domain.schemas.chembl.publication_term import PublicationTermSchema
from bioetl.domain.schemas.chembl.subcellular_fraction import (
    SubcellularFractionSchema,
)
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.target_component import TargetComponentSchema
from bioetl.domain.schemas.chembl.tissue import TissueSchema
from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema
from bioetl.domain.schemas.openalex.publication import OpenAlexPublicationSchema
from bioetl.domain.schemas.pubchem.compound import PubchemMoleculeSchema
from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema
from bioetl.domain.schemas.semanticscholar.publication import (
    SemanticScholarPublicationSchema,
)
from bioetl.domain.schemas.uniprot.idmapping import IDMappingSchema
from bioetl.domain.schemas.uniprot.protein import UniprotTargetSchema
from bioetl.infrastructure.config.dq_config_loader import DQConfigLoader
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
    "provider",
    "pipeline_name",
    "pipeline_kind",
    "entity",
    "field_name",
    "field_type",
    "normalization_source",
    "normalizer",
    "normalization_summary",
    "controlled_vocabulary_source",
    "policy_scope",
    "semantic_category",
    "include_in_content_hash",
    "set_like",
    "hash_ordering",
    "strictness",
    "schema_coverage",
    "dq_coverage",
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
COMPOSITE_SOURCE_FIELD_COVERAGE_KPI = (
    "composite_sensitive_source_field_profile_coverage_pct"
)
CONTROL_PLANE_NORMALIZATION_COVERAGE_KPI = "control_plane_normalization_coverage_pct"
ENTITY_RECORD_SURFACE = "entity_record"
COMPOSITE_JOIN_KEY_SURFACE = "composite_join_key"
COMPOSITE_SOURCE_FIELD_SURFACE = "composite_source_field"
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

ENTITY_DOMAIN_SCHEMA_REGISTRY: dict[str, Any] = {
    "chembl_activity": ActivitySchema,
    "chembl_assay": AssaySchema,
    "chembl_assay_parameters": AssayParametersSchema,
    "chembl_cell_line": CellLineSchema,
    "chembl_compound_record": CompoundRecordSchema,
    "chembl_molecule": MoleculeSchema,
    "chembl_protein_class": ProteinClassificationSchema,
    "chembl_publication": ChemblPublicationSchema,
    "chembl_publication_similarity": PublicationSimilaritySchema,
    "chembl_publication_term": PublicationTermSchema,
    "chembl_subcellular_fraction": SubcellularFractionSchema,
    "chembl_target": TargetSchema,
    "chembl_target_component": TargetComponentSchema,
    "chembl_tissue": TissueSchema,
    "crossref_publication": PublicationEnrichedSchema,
    "openalex_publication": OpenAlexPublicationSchema,
    "pubchem_compound": PubchemMoleculeSchema,
    "pubmed_publication": PubMedPublicationSchema,
    "semanticscholar_publication": SemanticScholarPublicationSchema,
    "uniprot_idmapping": IDMappingSchema,
    "uniprot_protein": UniprotTargetSchema,
}

_CHEMBL_ENUM_CONFIG = "configs/enums/chembl.yaml"
_UNIPROT_ENUM_CONFIG = "configs/enums/uniprot.yaml"

ENUM_CONFIG_SOURCES: dict[tuple[str, str, str], str] = {
    ("chembl", "activity", "assay_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "activity", "bao_endpoint_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "activity", "bao_format_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "activity", "data_validity_comment"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "activity", "qudt_unit_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "activity", "standard_relation"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "activity", "standard_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "activity", "uo_unit_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay", "assay_category"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay", "assay_group"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay", "assay_test_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay", "assay_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay", "confidence_description"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay", "relationship_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay_parameters", "standard_relation"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay_parameters", "standard_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay_parameters", "standard_units"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "molecule", "max_phase"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "molecule", "ro3_pass"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "molecule", "molecule_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "molecule", "structure_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "publication", "publication_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "publication_term", "term_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "target", "target_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "target_component", "component_type"): _CHEMBL_ENUM_CONFIG,
    ("uniprot", "protein", "entry_type"): _UNIPROT_ENUM_CONFIG,
    ("uniprot", "protein", "flag"): _UNIPROT_ENUM_CONFIG,
    ("uniprot", "protein", "protein_existence"): _UNIPROT_ENUM_CONFIG,
}

ENUM_REGISTRY_PATHS: dict[tuple[str, str, str], tuple[str, ...]] = {
    ("chembl", "activity", "assay_type"): ("assay", "types"),
    ("chembl", "activity", "bao_endpoint_mapping_status"): (
        "activity",
        "mapping_statuses",
    ),
    ("chembl", "activity", "bao_format_mapping_status"): (
        "activity",
        "mapping_statuses",
    ),
    ("chembl", "activity", "data_validity_comment"): (
        "activity",
        "data_validity_comments",
    ),
    ("chembl", "activity", "qudt_unit_mapping_status"): (
        "activity",
        "mapping_statuses",
    ),
    ("chembl", "activity", "standard_relation"): ("activity", "standard_relations"),
    ("chembl", "activity", "standard_type"): ("activity", "standard_types"),
    ("chembl", "activity", "uo_unit_mapping_status"): (
        "activity",
        "mapping_statuses",
    ),
    ("chembl", "activity", "standard_units"): ("activity", "standard_units"),
    ("chembl", "assay", "assay_category"): ("assay", "categories"),
    ("chembl", "assay", "assay_group"): ("assay", "assay_groups"),
    ("chembl", "assay", "assay_test_type"): ("assay", "test_types"),
    ("chembl", "assay", "assay_type"): ("assay", "types"),
    ("chembl", "assay", "confidence_description"): (
        "assay",
        "confidence_descriptions",
    ),
    ("chembl", "assay", "relationship_type"): ("assay", "relationship_types"),
    ("chembl", "assay_parameters", "standard_relation"): (
        "activity",
        "standard_relations",
    ),
    ("chembl", "assay_parameters", "standard_type"): (
        "assay",
        "parameter_standard_type_universe",
    ),
    ("chembl", "assay_parameters", "standard_units"): (
        "activity",
        "standard_units",
    ),
    ("chembl", "molecule", "max_phase"): ("molecule", "max_phase_values"),
    ("chembl", "molecule", "molecule_type"): ("molecule", "types"),
    ("chembl", "molecule", "ro3_pass"): ("molecule", "ro3_pass_values"),
    ("chembl", "molecule", "structure_type"): ("molecule", "structure_types"),
    ("chembl", "publication", "doc_type"): ("publication", "native_doc_types"),
    ("chembl", "publication", "publication_type"): ("publication", "types"),
    ("chembl", "publication_term", "term_type"): ("publication_term", "term_types"),
    ("chembl", "target", "target_type"): ("target", "types"),
    ("chembl", "target_component", "component_type"): (
        "target",
        "component_types",
    ),
}

ENUM_REGISTRY_UNIONS: dict[tuple[str, tuple[str, ...]], tuple[tuple[str, ...], ...]] = {
    (
        _CHEMBL_ENUM_CONFIG,
        ("assay", "parameter_standard_type_universe"),
    ): (
        ("activity", "standard_types"),
        ("assay", "parameter_standard_types"),
    ),
}

COMPOSITE_GOLD_SCHEMA_TYPE_REGISTRY: dict[str, str] = {
    "composite_activity": "unknown",
    "composite_assay": "unknown",
    "composite_molecule": "unknown",
    "composite_publication": "unknown",
    "composite_target": "unknown",
}
COMPOSITE_SENSITIVE_SOURCE_FIELDS: dict[str, tuple[tuple[str, str], ...]] = {
    "activity_id": (("chembl", "activity"),),
    "assay_id": (("chembl", "activity"), ("chembl", "assay")),
    "molecule_id": (("chembl", "activity"), ("chembl", "molecule")),
    "target_id": (("chembl", "activity"), ("chembl", "target")),
    "publication_id": (
        ("chembl", "activity"),
        ("chembl", "assay"),
        ("chembl", "publication"),
    ),
    "assay_type": (("chembl", "activity"), ("chembl", "assay")),
    "standard_type": (("chembl", "activity"),),
    "standard_relation": (("chembl", "activity"),),
    "target_type": (("chembl", "target"),),
    "molecule_type": (("chembl", "molecule"),),
    "bao_format": (("chembl", "activity"), ("chembl", "assay")),
    "standard_flag": (("chembl", "activity"),),
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


def _controlled_vocabulary_source(
    *,
    provider: str,
    entity: str,
    field_name: str,
    normalizer_name: str,
    notes: str,
) -> str:
    if provider == "chembl":
        policy_surface = chembl_policy_surface(entity, field_name)
        if policy_surface is not None:
            return policy_surface.registry_source

    configured_source = ENUM_CONFIG_SOURCES.get((provider, entity, field_name))
    if configured_source is not None:
        return configured_source

    normalized_notes = notes.casefold()
    if "enum field" in normalized_notes or "allowed values" in normalized_notes:
        return f"profile:{provider}.{entity}"
    if "operator" in normalizer_name or "operator" in normalized_notes:
        return "domain.normalization.rules.operator_aliases"
    if "unit" in normalizer_name or "unit" in normalized_notes:
        return "domain.normalization.rules.unit_aliases"
    if "bao" in normalizer_name or "bao identifier" in normalized_notes:
        return "domain.normalization.ontology_id_prefixes"
    if "ontology id" in normalized_notes or "ontology_id" in normalizer_name:
        return "domain.normalization.ontology_id_prefixes"
    return ""


@cache
def _load_enum_registry(config_path: str) -> dict[str, object]:
    payload = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _registry_values(
    *,
    config_path: str,
    registry_path: tuple[str, ...],
) -> frozenset[str]:
    union_paths = ENUM_REGISTRY_UNIONS.get((config_path, registry_path))
    if union_paths is not None:
        return frozenset().union(
            *(
                _registry_values(config_path=config_path, registry_path=union_path)
                for union_path in union_paths
            )
        )

    current: object = _load_enum_registry(config_path)
    for part in registry_path:
        if not isinstance(current, dict):
            return frozenset()
        current = current.get(part)
    if not isinstance(current, list):
        return frozenset()
    return frozenset(str(value) for value in current)


@cache
def _load_entity_config(provider: str, entity: str) -> dict[str, object]:
    path = Path("configs") / "entities" / provider / f"{entity}.yaml"
    if not path.exists():
        return {}
    return _load_yaml(path)


def _dq_allowed_values(
    *,
    provider: str,
    entity: str,
    field_name: str,
) -> frozenset[str]:
    dq_config = _load_dq_config(provider, entity)
    if dq_config is None:
        return frozenset()
    matches = [
        rule
        for rule in dq_config.field_validations
        if rule.field == field_name and rule.validation_type == "enum"
    ]
    if len(matches) != 1:
        return frozenset()
    return frozenset(str(value) for value in matches[0].allowed)


def _filter_value_set(raw_values: object) -> frozenset[str]:
    if raw_values is None:
        return frozenset()
    if isinstance(raw_values, str):
        return frozenset(
            value for value in (v.strip() for v in raw_values.split(",")) if value
        )
    if isinstance(raw_values, (list, tuple, set)):
        return frozenset(
            value for value in (str(v).strip() for v in raw_values) if value
        )
    return frozenset({str(raw_values).strip()})


def _filter_values(
    *,
    provider: str,
    entity: str,
    field_name: str,
) -> frozenset[str]:
    config = _load_entity_config(provider, entity)
    if not config:
        return frozenset()
    filters = config.get("filters") or {}
    if not isinstance(filters, dict):
        return frozenset()

    values: set[str] = set()
    extraction_params = filters.get("extraction_params") or {}
    if isinstance(extraction_params, dict):
        values.update(_filter_value_set(extraction_params.get(field_name)))
        values.update(_filter_value_set(extraction_params.get(f"{field_name}__in")))

    for filter_key in ("silver_filters", "gold_filters"):
        filter_config = filters.get(filter_key) or {}
        if not isinstance(filter_config, dict):
            continue
        columns = filter_config.get("columns") or {}
        if not isinstance(columns, dict):
            continue
        values.update(_filter_value_set(columns.get(field_name)))

    return frozenset(values)


def _policy_scope(
    *,
    provider: str,
    entity: str,
    field_name: str,
    controlled_vocabulary_source: str,
) -> str:
    registry_path = ENUM_REGISTRY_PATHS.get((provider, entity, field_name))
    if registry_path is None or not controlled_vocabulary_source.endswith(".yaml"):
        return "not_applicable"

    registry_values = _registry_values(
        config_path=controlled_vocabulary_source,
        registry_path=registry_path,
    )
    if not registry_values:
        return "not_applicable"

    for project_values in (
        _dq_allowed_values(provider=provider, entity=entity, field_name=field_name),
        _filter_values(provider=provider, entity=entity, field_name=field_name),
    ):
        if not project_values:
            continue
        if project_values < registry_values:
            return "project_subset_of_provider_universe"
        if not project_values <= registry_values:
            return "project_projection_of_provider_universe"
    return "provider_full_universe"


def _semantic_category(
    *,
    provider: str,
    entity: str,
    field_name: str,
    strictness: str,
) -> str:
    if provider == "chembl":
        policy_surface = chembl_policy_surface(entity, field_name)
        if policy_surface is not None:
            return policy_surface.category

    if strictness in {
        "strict_enum",
        "strict_operator",
        "strict_boolean",
        "strict_flag",
    }:
        return "strict_enum"
    if strictness == "strict_json":
        return "structured_json"
    if strictness == "canonical_ontology_id":
        return "ontology_reference_identifier"
    if strictness == "controlled_unit":
        return "controlled_vocabulary"
    if strictness == "normalization_only":
        return "free_text"
    return strictness


def _hash_ordering(*, include_in_hash: bool | None, set_like: bool) -> str:
    if include_in_hash is False:
        return "not_hashed"
    if set_like:
        return "set_like"
    return "order_sensitive"


def _strictness(
    *,
    field_name: str,
    normalization_source: str,
    normalizer_name: str,
    notes: str,
) -> str:
    normalized_notes = notes.casefold()
    if normalization_source == "composite_join_key_policy":
        return "join_key_policy"
    if normalization_source == "upstream_inherited":
        return "upstream_inherited"
    if normalizer_name == "normalize_profile_passthrough":
        return "technical_passthrough"
    if (
        field_name.endswith("_flag")
        or normalizer_name == "normalize_profile_binary_flag"
    ):
        return "strict_flag"
    category_match = _strictness_category_match(
        normalizer_name=normalizer_name,
        normalized_notes=normalized_notes,
    )
    if category_match is not None:
        return category_match
    if normalizer_name in {
        "normalize_profile_doi",
        "normalize_profile_pmid",
        "normalize_profile_pmc_id",
    }:
        return "canonical_identifier"
    if normalizer_name == "normalize_profile_json_string":
        return "canonical_json"
    if normalizer_name == "normalize_profile_json_string_strict":
        return "strict_json"
    if normalizer_name == "normalize_profile_boolean":
        return "strict_boolean"
    return "normalization_only"


def _strictness_category_match(
    *,
    normalizer_name: str,
    normalized_notes: str,
) -> str | None:
    if "ontology_version" in normalizer_name or "ontology version" in normalized_notes:
        return "normalization_only"
    if "operator" in normalizer_name or "operator" in normalized_notes:
        return "strict_operator"
    if "enum" in normalized_notes or "allowed values" in normalized_notes:
        return "strict_enum"
    if "unit" in normalizer_name or "unit" in normalized_notes:
        return "controlled_unit"
    if (
        "bao" in normalizer_name
        or "bao identifier" in normalized_notes
        or "ontology id" in normalized_notes
        or "ontology_id" in normalizer_name
    ):
        return "canonical_ontology_id"
    if "cellosaurus" in normalizer_name or "identifier" in normalized_notes:
        return "canonical_identifier"
    return None


def _row_policy_metadata(
    *,
    provider: str,
    entity: str,
    field_name: str,
    normalization_source: str,
    normalizer_name: str,
    notes: str,
) -> tuple[str, str, str, str]:
    controlled_vocabulary_source = _controlled_vocabulary_source(
        provider=provider,
        entity=entity,
        field_name=field_name,
        normalizer_name=normalizer_name,
        notes=notes,
    )
    strictness = _strictness(
        field_name=field_name,
        normalization_source=normalization_source,
        normalizer_name=normalizer_name,
        notes=notes,
    )
    semantic_category = _semantic_category(
        provider=provider,
        entity=entity,
        field_name=field_name,
        strictness=strictness,
    )
    policy_scope = _policy_scope(
        provider=provider,
        entity=entity,
        field_name=field_name,
        controlled_vocabulary_source=controlled_vocabulary_source,
    )
    return controlled_vocabulary_source, strictness, semantic_category, policy_scope


def _check_type_for_check(check: Any) -> str | None:
    check_fn = str(getattr(check, "_check_fn", ""))
    markers = (
        ("isin", ("isin",)),
        ("ge", ("ge", "greater_than_or_equal")),
        ("le", ("le", "less_than_or_equal")),
        ("gt", ("gt",)),
        ("lt", ("lt",)),
        ("str_length", ("str_length",)),
    )
    for check_type, values in markers:
        if any(value in check_fn for value in values):
            return check_type
    return None


@cache
def _domain_schema_field_coverage_by_pipeline(pipeline_name: str) -> dict[str, str]:
    schema_model = ENTITY_DOMAIN_SCHEMA_REGISTRY.get(pipeline_name)
    if schema_model is None:
        return {}
    schema = schema_model.to_schema()
    coverage: dict[str, str] = {}
    for column_name, column in schema.columns.items():
        check_types = sorted(
            {
                check_type
                for check in column.checks
                if (check_type := _check_type_for_check(check)) is not None
            }
        )
        checks = "+".join(check_types) if check_types else "none"
        coverage[column_name] = (
            f"domain_schema:present(nullable={column.nullable},checks={checks})"
        )
    return coverage


def _schema_coverage(
    *,
    pipeline_name: str,
    field_name: str,
    arrow_nullable: bool,
) -> str:
    domain_coverage = _domain_schema_field_coverage_by_pipeline(pipeline_name).get(
        field_name
    )
    if domain_coverage is None:
        return f"silver_arrow:present(nullable={arrow_nullable});domain_schema:missing"
    return f"silver_arrow:present(nullable={arrow_nullable});{domain_coverage}"


@cache
def _dq_rule_coverage_by_field(provider: str, entity: str) -> dict[str, str]:
    dq_config = _load_dq_config(provider, entity)
    if dq_config is None:
        return {}

    rules_by_field: dict[str, list[Any]] = {}
    for rule in dq_config.field_validations:
        rules_by_field.setdefault(rule.field, []).append(rule)
    return {
        field_name: ",".join(
            f"{rule.validation_type}:{rule.effective_severity(is_enricher=False)}"
            for rule in sorted(rules, key=lambda rule: rule.validation_type)
        )
        for field_name, rules in rules_by_field.items()
    }


@cache
def _load_dq_config(provider: str, entity: str) -> Any | None:
    try:
        return DQConfigLoader(Path("configs")).load(provider, entity)
    except (FileNotFoundError, ValueError, TypeError):
        return None


def _dq_coverage(
    *,
    provider: str,
    entity: str,
    field_name: str,
    strictness: str,
) -> str:
    if provider != "composite" and _load_dq_config(provider, entity) is None:
        return "dq_config:unavailable"
    coverage = _dq_rule_coverage_by_field(provider, entity).get(field_name)
    if coverage is None:
        if strictness == "strict_json":
            return "runtime_warning:malformed_json_normalized_to_null"
        return "not_configured"
    return coverage


def _entity_config_paths() -> list[Path]:
    return sorted(
        path
        for path in Path("configs/entities").glob("*/*.yaml")
        if path.parent.name != "composite"
    )


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
                    provider=provider,
                    entity=entity,
                    pipeline_name=pipeline_name,
                    field_name=field_name,
                    field_type=field_type,
                    arrow_nullable=field.nullable,
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
                provider=provider,
                entity=entity,
                pipeline_name=pipeline_name,
                field_name=field_name,
                field_type=field_type,
                arrow_nullable=field.nullable,
                source=source,
                normalizer=normalizer,
                summary=summary,
            )
        )
    return rows


def _entity_profile_row(
    *,
    provider: str,
    entity: str,
    pipeline_name: str,
    field_name: str,
    field_type: str,
    arrow_nullable: bool,
    profile_rule: Any,
) -> dict[str, str]:
    """Build one entity matrix row sourced from an explicit profile rule."""
    notes = profile_rule.notes or ""
    normalizer_name = _normalizer_name(
        profile_rule.normalizer,
        field_name=field_name,
        notes=profile_rule.notes,
    )
    controlled_vocabulary_source, strictness, semantic_category, policy_scope = (
        _row_policy_metadata(
            provider=provider,
            entity=entity,
            field_name=field_name,
            normalization_source=PROFILE_NORMALIZATION_SOURCE,
            normalizer_name=normalizer_name,
            notes=notes,
        )
    )
    return {
        "provider": provider,
        "pipeline_name": pipeline_name,
        "pipeline_kind": ENTITY_PIPELINE_KIND,
        "entity": entity,
        "field_name": field_name,
        "field_type": field_type,
        "normalization_source": PROFILE_NORMALIZATION_SOURCE,
        "normalizer": normalizer_name,
        "normalization_summary": notes,
        "controlled_vocabulary_source": controlled_vocabulary_source,
        "policy_scope": policy_scope,
        "semantic_category": semantic_category,
        "include_in_content_hash": _render_bool(profile_rule.include_in_hash),
        "set_like": _render_bool(profile_rule.set_like),
        "hash_ordering": _hash_ordering(
            include_in_hash=profile_rule.include_in_hash,
            set_like=profile_rule.set_like,
        ),
        "strictness": strictness,
        "schema_coverage": _schema_coverage(
            pipeline_name=pipeline_name,
            field_name=field_name,
            arrow_nullable=arrow_nullable,
        ),
        "dq_coverage": _dq_coverage(
            provider=provider,
            entity=entity,
            field_name=field_name,
            strictness=strictness,
        ),
        "notes": notes,
    }


def _entity_fallback_row(
    *,
    provider: str,
    entity: str,
    pipeline_name: str,
    field_name: str,
    field_type: str,
    arrow_nullable: bool,
    source: str,
    normalizer: str,
    summary: str,
) -> dict[str, str]:
    """Build one entity matrix row sourced from fallback normalization policy."""
    controlled_vocabulary_source, strictness, semantic_category, policy_scope = (
        _row_policy_metadata(
            provider=provider,
            entity=entity,
            field_name=field_name,
            normalization_source=source,
            normalizer_name=normalizer,
            notes=summary,
        )
    )
    return {
        "provider": provider,
        "pipeline_name": pipeline_name,
        "pipeline_kind": ENTITY_PIPELINE_KIND,
        "entity": entity,
        "field_name": field_name,
        "field_type": field_type,
        "normalization_source": source,
        "normalizer": normalizer,
        "normalization_summary": summary,
        "controlled_vocabulary_source": controlled_vocabulary_source,
        "policy_scope": policy_scope,
        "semantic_category": semantic_category,
        "include_in_content_hash": "",
        "set_like": FALSE_TEXT,
        "hash_ordering": "fallback_policy",
        "strictness": strictness,
        "schema_coverage": _schema_coverage(
            pipeline_name=pipeline_name,
            field_name=field_name,
            arrow_nullable=arrow_nullable,
        ),
        "dq_coverage": _dq_coverage(
            provider=provider,
            entity=entity,
            field_name=field_name,
            strictness=strictness,
        ),
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
    strictness = _strictness(
        field_name=field_name,
        normalization_source=source,
        normalizer_name=normalizer,
        notes=summary,
    )
    return {
        "provider": "composite",
        "pipeline_name": pipeline_name,
        "pipeline_kind": COMPOSITE_PIPELINE_KIND,
        "entity": pipeline_name.removeprefix("composite_"),
        "field_name": field_name,
        "field_type": COMPOSITE_GOLD_SCHEMA_TYPE_REGISTRY.get(pipeline_name, "unknown"),
        "normalization_source": source,
        "normalizer": normalizer,
        "normalization_summary": summary,
        "controlled_vocabulary_source": "",
        "policy_scope": "not_applicable",
        "semantic_category": _semantic_category(
            provider="composite",
            entity=pipeline_name.removeprefix("composite_"),
            field_name=field_name,
            strictness=strictness,
        ),
        "include_in_content_hash": "",
        "set_like": FALSE_TEXT,
        "hash_ordering": "not_applicable",
        "strictness": strictness,
        "schema_coverage": "gold_contract:inherited",
        "dq_coverage": "not_applicable",
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
        row
        for row in (build_field_matrix_rows() if rows is None else rows)
        if row["pipeline_kind"] == ENTITY_PIPELINE_KIND
    ]
    entity_field_count = len(entity_rows)
    explicit_profile_field_count = sum(
        1
        for row in entity_rows
        if row["normalization_source"] == PROFILE_NORMALIZATION_SOURCE
    )
    value_pct = round(
        (explicit_profile_field_count * 100 / entity_field_count)
        if entity_field_count
        else 0.0,
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


def _iter_composite_sensitive_source_field_requirements() -> list[tuple[str, str, str]]:
    composite_fields = {
        row["field_name"]
        for row in _composite_field_matrix_rows()
        if row["normalization_source"] == "upstream_inherited"
        or row["normalization_source"] == "composite_join_key_policy"
    }
    requirements: list[tuple[str, str, str]] = []
    for field_name, source_profiles in COMPOSITE_SENSITIVE_SOURCE_FIELDS.items():
        if field_name not in composite_fields:
            continue
        requirements.extend(
            (field_name, provider, entity) for provider, entity in source_profiles
        )
    return requirements


def build_composite_sensitive_source_field_profile_coverage_kpi() -> dict[str, object]:
    """Report source-profile coverage for composite-sensitive inherited fields."""
    requirements = _iter_composite_sensitive_source_field_requirements()
    regressions: list[str] = []
    covered = 0
    for field_name, provider, entity in requirements:
        profile = resolve_normalization_profile(provider, entity)
        rule = None if profile is None else profile.rule_for(field_name)
        if rule is None:
            regressions.append(f"{provider}.{entity}.{field_name}")
            continue
        covered += 1

    denominator = len(requirements)
    value_pct = round((covered * 100 / denominator) if denominator else 0.0, 2)
    return {
        "surface": COMPOSITE_SOURCE_FIELD_SURFACE,
        "name": COMPOSITE_SOURCE_FIELD_COVERAGE_KPI,
        "description": (
            "Percent of composite-sensitive source fields covered by explicit "
            "source normalization profiles."
        ),
        "numerator": covered,
        "denominator": denominator,
        "value_pct": value_pct,
        "regressions": regressions,
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
        git_commit=" ABCDEF123 ",
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
        and runtime_anchor_status.get("contract_version") == CANONICAL_CONTRACT_VERSION
    )


def _checkpoint_context_covered(checkpoint_context: object) -> bool:
    """Return whether checkpoint context normalization preserves canonical anchors."""
    return (
        checkpoint_context.effective_config_hash == CANONICAL_EFFECTIVE_CONFIG_HASH
        and checkpoint_context.contract_ref == CANONICAL_CONTRACT_REF
        and checkpoint_context.contract_version == CANONICAL_CONTRACT_VERSION
    )


def _checkpoint_anchor_merge_covered(merged_checkpoint: object) -> bool:
    """Return whether merged checkpoint anchors preserve canonical values."""
    return (
        merged_checkpoint.effective_config_hash == CANONICAL_EFFECTIVE_CONFIG_HASH
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
        build_composite_sensitive_source_field_profile_coverage_kpi(),
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
            _update_profile_semantic_stats(
                stats, provider, entity, profile, field_name, rule
            )

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
    normalizer_name = getattr(
        rule.normalizer, "__name__", type(rule.normalizer).__name__
    )
    return f"{location} -> {normalizer_name}"


def _is_json_string_normalizer(rule: Any) -> bool:
    """Return whether a rule uses the effective JSON-string normalizer family."""
    return (
        rule.normalizer is normalize_profile_json_string
        or getattr(rule.normalizer, "__name__", "") == "normalize_profile_json_string"
        or rule.normalizer is normalize_profile_json_string_strict
        or getattr(rule.normalizer, "__name__", "")
        == "normalize_profile_json_string_strict"
    )


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
    if _is_json_string_normalizer(rule):
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
        (
            "Generated from active pipeline configs, Silver schemas, domain schema "
            "contracts, DQ policy configs, and current normalization code paths."
        ),
        "",
        "This matrix is a normalization inventory, not a persisted-row publication contract.",
        (
            "Occurrence-scoped provenance fields may appear here because normalization "
            "or config policy still references them,"
        ),
        "but canonical Silver/Gold row contracts are defined by provider references and Gold contract exports.",
        "",
        (
            "Governance columns expose controlled-vocabulary sources, content_hash "
            "scope, content_hash inclusion, hash ordering, semantic category, "
            "strictness, domain/Silver schema visibility, and DQ rule visibility "
            "for each field."
        ),
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
    regression_note = f" Regressions: {', '.join(regressions)}." if regressions else ""
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
    return "| " + " | ".join(row.get(header, "") for header in headers) + " |"


def build_artifacts() -> dict[str, str]:
    rows = build_field_matrix_rows()
    return {
        CSV_NAME: render_csv(rows),
        MD_NAME: render_markdown(rows),
    }


def _normalize_newlines(payload: str) -> str:
    """Normalize line endings for deterministic cross-platform comparisons."""
    return payload.replace("\r\n", "\n").replace("\r", "\n")


def write_artifacts(out_dir: Path) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts = build_artifacts()
    rows = build_field_matrix_rows()
    surface_kpis = build_surface_coverage_kpis(rows)
    semantic_kpis = build_profile_semantic_invariants()
    for name, payload in artifacts.items():
        (out_dir / name).write_text(payload, encoding="utf-8", newline="\n")
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
        if _normalize_newlines(path.read_text(encoding="utf-8")) != _normalize_newlines(
            payload
        ):
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
