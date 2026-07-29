#!/usr/bin/env python3
# ruff: noqa: E402
"""Generate deterministic normalization field-matrix artifacts for all pipelines."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

DEFAULT_OUT_DIR = Path("docs/reports/generated/pipeline_normalization_field_matrix")


def _build_arg_parser() -> argparse.ArgumentParser:
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


def _maybe_exit_help_only_cli() -> None:
    """Short-circuit CLI help before importing heavy runtime dependencies."""
    if __name__ != "__main__":
        return
    if not any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        return
    _build_arg_parser().parse_args()


_maybe_exit_help_only_cli()

import pyarrow as pa
import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from scripts.docs.matrix._bootstrap import ensure_repo_imports
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
from bioetl.composition.bootstrap.runtime.normalization_policy_init import (
    initialize_chembl_policy_registry as initialize_bootstrap_chembl_policy_registry,
)
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
from bioetl.domain.normalization.profiles.chembl_json_ordering_policy import (
    chembl_json_fields,
)
from bioetl.domain.normalization.profiles.chembl_policy_registry import (
    chembl_policy_surface,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_json_string,
    normalize_profile_json_string_strict,
    normalize_profile_passthrough,
    normalize_profile_target_component_relationships,
    normalize_profile_target_component_types,
)
from bioetl.domain.normalization.publication_structured_fields import (
    publication_structured_field_policy,
)
from bioetl.domain.normalization.structured_payload_policies import (
    semantic_sensitive_structured_payload_policies,
    structured_payload_policy,
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
from bioetl.domain.schemas.chembl.target_protein_classification import (
    TargetProteinClassificationSchema,
)
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
    CHEMBL_TARGET_PROTEIN_CLASSIFICATION_SCHEMA,
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

CSV_NAME = "pipeline_normalization_field_matrix.csv"
MD_NAME = "pipeline_normalization_field_matrix.md"
NON_CHEMBL_MD_NAME = "non_chembl_normalization_field_matrix.md"
NON_CHEMBL_OBSERVED_VALUES_FIXTURE = Path(
    "tests/fixtures/normalization/non_chembl_observed_values.yaml"
)
NON_CHEMBL_PIPELINES = frozenset(
    {
        "crossref_publication",
        "openalex_publication",
        "pubchem_compound",
        "pubmed_publication",
        "semanticscholar_publication",
        "uniprot_idmapping",
        "uniprot_protein",
    }
)

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
    "classification",
    "identifier_family",
    "collection_semantics",
    "raw_sidecar",
    "canonical_sidecar",
    "include_in_content_hash",
    "set_like",
    "hash_ordering",
    "strictness",
    "schema_coverage",
    "dq_coverage",
    "dq_rule",
    "composite_usage",
    "observed_source",
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
CANONICAL_NORMALIZATION_PROFILE_REF_RAW = " ChemBL.Activity "
CANONICAL_NORMALIZATION_PROFILE_VERSION_RAW = " v1 "
CANONICAL_NORMALIZATION_PROFILE_HASH_RAW = (
    " SHA256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB "
)
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
    "chembl_target_protein_classification": CHEMBL_TARGET_PROTEIN_CLASSIFICATION_SCHEMA,
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
    "chembl_target_protein_classification": TargetProteinClassificationSchema,
    "chembl_tissue": TissueSchema,
    "crossref_publication": PublicationEnrichedSchema,
    "openalex_publication": OpenAlexPublicationSchema,
    "pubchem_compound": PubchemMoleculeSchema,
    "pubmed_publication": PubMedPublicationSchema,
    "semanticscholar_publication": SemanticScholarPublicationSchema,
    "uniprot_idmapping": IDMappingSchema,
    "uniprot_protein": UniprotTargetSchema,
}

# Reviewed Silver/domain naming seams. The shipped Silver schemas still expose a
# handful of historical generic field names, while the domain schemas and
# normalization profiles track their owner-specific canonical names. Matrix and
# fallback reporting must bridge those aliases before classifying a field as
# fallback debt.
ENTITY_PROFILE_FIELD_ALIASES: dict[str, dict[str, str]] = {
    "chembl_activity": {
        "relation": "activity_relation",
        "type": "activity_type",
        "value": "activity_value",
    },
    "chembl_assay": {
        "description": "assay_description",
        "score": "confidence_score",
    },
    "chembl_assay_parameters": {
        "relation": "parameter_relation",
        "type": "parameter_type",
        "value": "parameter_value",
    },
    "chembl_target": {
        "description": "target_description",
    },
    "chembl_target_component": {
        "description": "component_description",
    },
}

_CHEMBL_ENUM_CONFIG = "configs/enums/chembl.yaml"
_CHEMBL_CONTROLLED_VOCAB_CONFIG = "configs/vocab/chembl_controlled.yaml"
_PUBCHEM_ENUM_CONFIG = "configs/enums/pubchem.yaml"
_UNIPROT_ENUM_CONFIG = "configs/enums/uniprot.yaml"
_PUBLICATION_CONTROLLED_CONFIG = "configs/vocab/publication_controlled.yaml"
_UNIPROT_SEMANTIC_PAYLOADS_CONFIG = "configs/vocab/uniprot_semantic_payloads.yaml"
_PUBLICATION_TYPE_CLASSIFICATION_SOURCE = (
    "configs/enums/publication_type_classification.csv"
)
_CHEMBL_REFERENCE_SOURCES_CONFIG = "configs/vocab/chembl_reference_sources.yaml"
_CHEMBL_ONTOLOGY_CONFIG = "configs/vocab/chembl_ontology.yaml"
_COMPOSITE_SCHEMA_AUTHORITY_REGISTRY = (
    "configs/field_registry/composite_schema_authority_registry.yaml"
)
_REFERENCE_ID_SOURCE = "domain.normalization.reference_ids"
_OA_STATUS_SOURCE = "domain.schemas.common.publication_base.OA_STATUS_VALUES"

ENUM_CONFIG_SOURCES: dict[tuple[str, str, str], str] = {
    ("chembl", "activity", "action_type"): _CHEMBL_CONTROLLED_VOCAB_CONFIG,
    ("chembl", "activity", "assay_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "activity", "bao_endpoint_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "activity", "bao_format_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "activity", "data_validity_comment"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "activity", "qudt_unit_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "activity", "standard_relation"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "activity", "standard_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "activity", "uo_unit_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay", "assay_category"): _CHEMBL_CONTROLLED_VOCAB_CONFIG,
    ("chembl", "assay", "assay_group"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay", "assay_subcellular_fraction"): _CHEMBL_CONTROLLED_VOCAB_CONFIG,
    ("chembl", "assay", "assay_test_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay", "assay_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay", "subcellular_fraction"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay", "subcellular_fractions"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay", "bao_format_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay", "relationship_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "cell_line", "clo_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "cell_line", "efo_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay_parameters", "standard_relation"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay_parameters", "standard_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay_parameters", "qudt_unit_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "assay_parameters", "uo_unit_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "molecule", "availability_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "molecule", "chirality"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "tissue", "bto_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "tissue", "efo_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "tissue", "uberon_mapping_status"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "molecule", "max_phase"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "molecule", "ro3_pass"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "molecule", "molecule_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "molecule", "structure_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "publication", "oa_status"): _CHEMBL_CONTROLLED_VOCAB_CONFIG,
    ("chembl", "publication", "publication_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "publication_term", "term_type"): _CHEMBL_ENUM_CONFIG,
    (
        "chembl",
        "subcellular_fraction",
        "subcellular_fraction",
    ): _CHEMBL_CONTROLLED_VOCAB_CONFIG,
    ("chembl", "target", "component_relationships"): _CHEMBL_CONTROLLED_VOCAB_CONFIG,
    ("chembl", "target", "component_types"): _CHEMBL_CONTROLLED_VOCAB_CONFIG,
    ("chembl", "target", "organism_class"): _CHEMBL_CONTROLLED_VOCAB_CONFIG,
    ("chembl", "target", "target_type"): _CHEMBL_ENUM_CONFIG,
    ("chembl", "target", "cross_references"): _CHEMBL_REFERENCE_SOURCES_CONFIG,
    ("chembl", "target_component", "component_type"): _CHEMBL_ENUM_CONFIG,
    (
        "chembl",
        "target_component",
        "target_component_xrefs",
    ): _CHEMBL_REFERENCE_SOURCES_CONFIG,
    ("crossref", "publication", "publication_type"): _PUBLICATION_CONTROLLED_CONFIG,
    ("openalex", "publication", "publication_type"): _PUBLICATION_CONTROLLED_CONFIG,
    ("openalex", "publication", "type_crossref"): _PUBLICATION_CONTROLLED_CONFIG,
    (
        "pubchem",
        "compound",
        "chemical_standardization_policy_version",
    ): _PUBCHEM_ENUM_CONFIG,
    ("pubchem", "compound", "chemical_standardization_status"): _PUBCHEM_ENUM_CONFIG,
    ("pubmed", "publication", "publication_type"): _PUBLICATION_CONTROLLED_CONFIG,
    ("pubmed", "publication", "publication_type_list"): _PUBLICATION_CONTROLLED_CONFIG,
    ("pubmed", "publication", "publication_types"): _PUBLICATION_CONTROLLED_CONFIG,
    ("pubmed", "publication", "publication_status"): _PUBLICATION_CONTROLLED_CONFIG,
    (
        "semanticscholar",
        "publication",
        "publication_type",
    ): _PUBLICATION_CONTROLLED_CONFIG,
    (
        "semanticscholar",
        "publication",
        "publication_types",
    ): _PUBLICATION_CONTROLLED_CONFIG,
    ("uniprot", "protein", "entry_type"): _UNIPROT_ENUM_CONFIG,
    ("uniprot", "protein", "flag"): _UNIPROT_ENUM_CONFIG,
    ("uniprot", "protein", "protein_existence"): _UNIPROT_ENUM_CONFIG,
}

REFERENCE_ID_SOURCES: dict[tuple[str, str, str], str] = {
    ("chembl", "assay_parameters", "qudt_units"): _CHEMBL_ONTOLOGY_CONFIG,
    ("chembl", "assay_parameters", "uo_units"): _CHEMBL_ONTOLOGY_CONFIG,
    ("crossref", "publication", "author_orcids"): _REFERENCE_ID_SOURCE,
    ("crossref", "publication", "issn"): _REFERENCE_ID_SOURCE,
    ("crossref", "publication", "issn_electronic"): _REFERENCE_ID_SOURCE,
    ("crossref", "publication", "issn_list"): _REFERENCE_ID_SOURCE,
    ("crossref", "publication", "issn_print"): _REFERENCE_ID_SOURCE,
    ("openalex", "publication", "author_openalex_ids"): _REFERENCE_ID_SOURCE,
    ("openalex", "publication", "author_orcids"): _REFERENCE_ID_SOURCE,
    ("openalex", "publication", "institution_ids"): _REFERENCE_ID_SOURCE,
    ("openalex", "publication", "issn"): _REFERENCE_ID_SOURCE,
    ("openalex", "publication", "openalex_id"): _REFERENCE_ID_SOURCE,
    ("openalex", "publication", "primary_topic"): _REFERENCE_ID_SOURCE,
    ("openalex", "publication", "ror_ids"): _REFERENCE_ID_SOURCE,
    ("openalex", "publication", "subject_topics"): _REFERENCE_ID_SOURCE,
    ("pubmed", "publication", "author_orcids"): _REFERENCE_ID_SOURCE,
    ("pubmed", "publication", "issn"): _REFERENCE_ID_SOURCE,
    ("semanticscholar", "publication", "author_orcids"): _REFERENCE_ID_SOURCE,
    ("semanticscholar", "publication", "author_s2_ids"): _REFERENCE_ID_SOURCE,
    ("semanticscholar", "publication", "paper_id"): _REFERENCE_ID_SOURCE,
    ("uniprot", "idmapping", "all_mappings"): _REFERENCE_ID_SOURCE,
    ("uniprot", "idmapping", "target_id"): _REFERENCE_ID_SOURCE,
    ("uniprot", "idmapping", "uniprot_accession"): _REFERENCE_ID_SOURCE,
    ("uniprot", "protein", "cellular_component"): _REFERENCE_ID_SOURCE,
    ("uniprot", "protein", "chembl_ids"): _REFERENCE_ID_SOURCE,
    ("uniprot", "protein", "drugbank_ids"): _REFERENCE_ID_SOURCE,
    ("uniprot", "protein", "go_terms"): _REFERENCE_ID_SOURCE,
    ("uniprot", "protein", "interpro_xrefs"): _REFERENCE_ID_SOURCE,
    ("uniprot", "protein", "molecular_function"): _REFERENCE_ID_SOURCE,
    ("uniprot", "protein", "pdb_xrefs"): _REFERENCE_ID_SOURCE,
    ("uniprot", "protein", "pfam_xrefs"): _REFERENCE_ID_SOURCE,
    ("uniprot", "protein", "reactome_xrefs"): _REFERENCE_ID_SOURCE,
    ("uniprot", "protein", "secondary_accessions"): _REFERENCE_ID_SOURCE,
}

_PUBLICATION_TAXONOMY_FIELDS = frozenset(
    {"publication_type_unified", "publication_subclass", "publication_class"}
)
_NON_CHEMBL_IDENTIFIER_FAMILIES: dict[tuple[str, str, str], str] = {
    ("crossref", "publication", "author_orcids"): "orcid",
    ("crossref", "publication", "doi"): "doi",
    ("crossref", "publication", "issn"): "issn",
    ("openalex", "publication", "author_openalex_ids"): "openalex_author_id",
    ("openalex", "publication", "author_orcids"): "orcid",
    ("openalex", "publication", "doi"): "doi",
    ("openalex", "publication", "institution_ids"): "openalex_institution_id",
    ("openalex", "publication", "openalex_id"): "openalex_work_id",
    ("openalex", "publication", "primary_topic"): "openalex_topic_id",
    ("openalex", "publication", "ror_ids"): "ror",
    ("openalex", "publication", "subject_topics"): "openalex_topic_id",
    ("pubchem", "compound", "molecule_id"): "pubchem_cid",
    ("pubmed", "publication", "author_orcids"): "orcid",
    ("pubmed", "publication", "doi"): "doi",
    ("pubmed", "publication", "issn"): "issn",
    ("pubmed", "publication", "pmc_id"): "pmcid",
    ("pubmed", "publication", "pmid"): "pmid",
    ("semanticscholar", "publication", "author_orcids"): "orcid",
    ("semanticscholar", "publication", "author_s2_ids"): "semanticscholar_author_id",
    ("semanticscholar", "publication", "doi"): "doi",
    ("semanticscholar", "publication", "paper_id"): "semanticscholar_paper_id",
    ("semanticscholar", "publication", "pmc_id"): "pmcid",
    ("semanticscholar", "publication", "pmid"): "pmid",
    ("uniprot", "idmapping", "all_mappings"): "mixed_identifier_set",
    ("uniprot", "idmapping", "target_id"): "chembl_target_id",
    ("uniprot", "idmapping", "taxonomy_id"): "ncbi_taxonomy_id",
    ("uniprot", "idmapping", "uniprot_accession"): "uniprot_accession",
    ("uniprot", "protein", "accession"): "uniprot_accession",
    ("uniprot", "protein", "cellular_component"): "go",
    ("uniprot", "protein", "chembl_ids"): "chembl_id",
    ("uniprot", "protein", "drugbank_ids"): "drugbank_id",
    ("uniprot", "protein", "go_terms"): "go",
    ("uniprot", "protein", "interpro_xrefs"): "interpro",
    ("uniprot", "protein", "molecular_function"): "go",
    ("uniprot", "protein", "pdb_xrefs"): "pdb",
    ("uniprot", "protein", "pfam_xrefs"): "pfam",
    ("uniprot", "protein", "reactome_xrefs"): "reactome",
    ("uniprot", "protein", "secondary_accessions"): "uniprot_accession",
    ("uniprot", "protein", "taxonomy_id"): "ncbi_taxonomy_id",
}
_NON_CHEMBL_INVENTORY_SECTIONS = (
    "observed_values",
    "observed_raw_values",
    "expected_normalized_values",
    "expected_controlled_values",
)

ENUM_REGISTRY_PATHS: dict[tuple[str, str, str], tuple[str, ...]] = {
    ("chembl", "activity", "action_type"): ("activity", "action_types"),
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
    ("chembl", "assay", "assay_subcellular_fraction"): (
        "assay",
        "subcellular_fractions",
    ),
    ("chembl", "assay", "assay_test_type"): ("assay", "test_types"),
    ("chembl", "assay", "assay_type"): ("assay", "types"),
    ("chembl", "assay", "bao_format_mapping_status"): (
        "activity",
        "mapping_statuses",
    ),
    ("chembl", "assay", "confidence_description"): (
        "assay",
        "confidence_descriptions",
    ),
    ("chembl", "assay", "relationship_type"): ("assay", "relationship_types"),
    ("chembl", "assay", "subcellular_fraction"): ("assay", "subcellular_fractions"),
    ("chembl", "assay", "subcellular_fractions"): ("assay", "subcellular_fractions"),
    ("chembl", "assay_parameters", "parameter_type"): (
        "assay",
        "parameter_standard_type_universe",
    ),
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
    ("chembl", "assay_parameters", "type"): (
        "assay",
        "parameter_standard_type_universe",
    ),
    ("chembl", "assay_parameters", "qudt_unit_mapping_status"): (
        "activity",
        "mapping_statuses",
    ),
    ("chembl", "assay_parameters", "uo_unit_mapping_status"): (
        "activity",
        "mapping_statuses",
    ),
    ("chembl", "cell_line", "clo_mapping_status"): (
        "activity",
        "mapping_statuses",
    ),
    ("chembl", "cell_line", "efo_mapping_status"): (
        "activity",
        "mapping_statuses",
    ),
    # Molecule flag fields use provider-specific numeric codes
    ("chembl", "molecule", "black_box_warning"): (
        "molecule",
        "binary_flag_values",
    ),
    ("chembl", "molecule", "availability_type"): (
        "molecule",
        "availability_type_values",
    ),
    ("chembl", "molecule", "chirality"): ("molecule", "chirality_values"),
    ("chembl", "molecule", "dosed_ingredient"): (
        "molecule",
        "binary_flag_values",
    ),
    ("chembl", "molecule", "first_in_class"): (
        "molecule",
        "trinary_flag_values",
    ),
    ("chembl", "molecule", "inorganic_flag"): (
        "molecule",
        "trinary_flag_values",
    ),
    ("chembl", "molecule", "max_phase"): ("molecule", "max_phase_values"),
    ("chembl", "molecule", "molecule_type"): ("molecule", "types"),
    ("chembl", "molecule", "natural_product"): (
        "molecule",
        "trinary_flag_values",
    ),
    ("chembl", "molecule", "polymer_flag"): (
        "molecule",
        "binary_flag_values",
    ),
    ("chembl", "molecule", "prodrug"): (
        "molecule",
        "trinary_flag_values",
    ),
    ("chembl", "molecule", "ro3_pass"): ("molecule", "ro3_pass_values"),
    ("chembl", "molecule", "structure_type"): ("molecule", "structure_types"),
    ("chembl", "publication", "doc_type"): ("publication", "native_doc_types"),
    ("chembl", "publication", "oa_status"): ("publication", "oa_status_values"),
    # publication_type compares the ChEMBL-specific DQ subset against the
    # cross-provider global taxonomy.
    ("chembl", "publication", "publication_type"): ("publication", "types"),
    ("chembl", "publication_term", "term_type"): ("publication_term", "term_types"),
    ("chembl", "subcellular_fraction", "subcellular_fraction"): (
        "assay",
        "subcellular_fractions",
    ),
    ("chembl", "target", "component_relationships"): (
        "target",
        "component_relationships",
    ),
    ("chembl", "target", "component_types"): ("target", "component_types"),
    ("chembl", "target", "organism_class"): ("target", "organism_classes"),
    ("chembl", "target", "target_type"): ("target", "types"),
    (
        "chembl",
        "target",
        "cross_references",
    ): ("nested_reference_vocabularies", "target_component_xref_src_db", "values"),
    (
        "chembl",
        "target_component",
        "target_component_xrefs",
    ): ("nested_reference_vocabularies", "target_component_xref_src_db", "values"),
    ("chembl", "target_component", "component_type"): (
        "target",
        "component_types",
    ),
    ("chembl", "tissue", "bto_mapping_status"): (
        "activity",
        "mapping_statuses",
    ),
    ("chembl", "tissue", "efo_mapping_status"): (
        "activity",
        "mapping_statuses",
    ),
    ("chembl", "tissue", "uberon_mapping_status"): (
        "activity",
        "mapping_statuses",
    ),
    ("crossref", "publication", "publication_type"): (
        "providers",
        "crossref",
        "publication_type",
        "values",
    ),
    ("openalex", "publication", "publication_type"): (
        "providers",
        "openalex",
        "publication_type",
        "values",
    ),
    ("openalex", "publication", "type_crossref"): (
        "providers",
        "openalex",
        "type_crossref",
        "values",
    ),
    (
        "pubchem",
        "compound",
        "chemical_standardization_policy_version",
    ): ("compound", "chemical_standardization_policy_versions"),
    ("pubchem", "compound", "chemical_standardization_status"): (
        "compound",
        "chemical_standardization_statuses",
    ),
    ("pubmed", "publication", "publication_type"): (
        "providers",
        "pubmed",
        "publication_types",
        "values",
    ),
    ("pubmed", "publication", "publication_type_list"): (
        "providers",
        "pubmed",
        "publication_types",
        "values",
    ),
    ("pubmed", "publication", "publication_types"): (
        "providers",
        "pubmed",
        "publication_types",
        "values",
    ),
    ("pubmed", "publication", "publication_status"): (
        "providers",
        "pubmed",
        "publication_status",
        "values",
    ),
    ("semanticscholar", "publication", "publication_type"): (
        "providers",
        "semanticscholar",
        "publication_types",
        "values",
    ),
    ("semanticscholar", "publication", "publication_types"): (
        "providers",
        "semanticscholar",
        "publication_types",
        "values",
    ),
    ("uniprot", "protein", "features_json"): (
        "protein",
        "semantic_payload_terms",
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
    (
        _PUBLICATION_CONTROLLED_CONFIG,
        ("providers", "openalex", "type_crossref", "values"),
    ): (("providers", "crossref", "publication_type", "values"),),
    (
        _UNIPROT_SEMANTIC_PAYLOADS_CONFIG,
        ("protein", "semantic_payload_terms"),
    ): (
        ("protein", "feature_types"),
        ("protein", "comment_types"),
        ("protein", "keyword_categories"),
    ),
}

_JSON_SCHEMA_TYPE_TO_MATRIX_TYPE: dict[str, str] = {
    "string": "string",
    "integer": "int64",
    "number": "float64",
    "boolean": "bool",
    "object": "object",
    "array": "list",
}

COMPOSITE_SOURCE_FIELD_TYPE_ALIAS_HINTS: dict[tuple[str, str], tuple[str, ...]] = {
    ("composite_publication", "year"): ("publication_year",),
}


@cache
def _composite_gold_contract_properties(
    pipeline_name: str,
) -> dict[str, dict[str, object]]:
    contract_path = (
        Path("docs/04-reference/contracts/gold") / f"{pipeline_name}_v1.0.json"
    )
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    properties = payload.get("properties", {})
    if not isinstance(properties, dict):
        return {}
    return {
        field_name: spec
        for field_name, spec in properties.items()
        if isinstance(field_name, str) and isinstance(spec, dict)
    }


def _matrix_field_type_from_json_schema(type_payload: object) -> str:
    values: list[str]
    if isinstance(type_payload, list):
        values = [str(value).strip().lower() for value in type_payload]
    elif isinstance(type_payload, str):
        values = [type_payload.strip().lower()]
    else:
        return "unknown"
    non_null = [value for value in values if value and value != "null"]
    if len(non_null) != 1:
        return "unknown"
    return _JSON_SCHEMA_TYPE_TO_MATRIX_TYPE.get(non_null[0], non_null[0] or "unknown")


def _composite_field_type(pipeline_name: str, field_name: str) -> str:
    properties = _composite_gold_contract_properties(pipeline_name)
    spec = properties.get(field_name)
    if isinstance(spec, dict):
        contract_type = _matrix_field_type_from_json_schema(spec.get("type"))
        if contract_type != "unknown":
            return contract_type
    return "unknown"


def _authority_entry_lookup(
    entry: object,
) -> dict[tuple[str, str], dict[str, str]]:
    if not isinstance(entry, dict):
        return {}
    authority_id = entry.get("id")
    pipelines = entry.get("pipelines")
    field_types = entry.get("field_types")
    if not isinstance(authority_id, str):
        return {}
    if not isinstance(pipelines, list) or not isinstance(field_types, dict):
        return {}
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    for pipeline_name in pipelines:
        if not isinstance(pipeline_name, str) or not pipeline_name:
            continue
        for field_name, field_type in field_types.items():
            if not isinstance(field_name, str) or not isinstance(field_type, str):
                continue
            lookup[(pipeline_name, field_name)] = {
                "authority_id": authority_id,
                "field_type": field_type,
            }
    return lookup


@cache
def _composite_schema_authority_lookup() -> dict[tuple[str, str], dict[str, str]]:
    payload = yaml.safe_load(
        Path(_COMPOSITE_SCHEMA_AUTHORITY_REGISTRY).read_text(encoding="utf-8")
    )
    if not isinstance(payload, dict):
        return {}
    entries = payload.get("authorities", [])
    if not isinstance(entries, list):
        return {}
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    for entry in entries:
        lookup.update(_authority_entry_lookup(entry))
    return lookup


def _composite_schema_authority_override(
    pipeline_name: str,
    field_name: str,
) -> dict[str, str] | None:
    return _composite_schema_authority_lookup().get((pipeline_name, field_name))


@cache
def _entity_schema_field_type(pipeline_name: str, field_name: str) -> str:
    schema_object = ENTITY_SILVER_SCHEMA_REGISTRY.get(pipeline_name)
    if schema_object is None:
        return "unknown"
    if isinstance(schema_object, pa.Schema):
        schema = schema_object
    elif hasattr(schema_object, "to_schema"):
        schema = schema_object.to_schema()
    else:
        return "unknown"
    try:
        return str(schema.field(field_name).type)
    except KeyError:
        return "unknown"


def _pipeline_name_from_entry(entry: object) -> str | None:
    if not isinstance(entry, dict):
        return None
    pipeline = entry.get("pipeline")
    if isinstance(pipeline, str) and pipeline:
        return pipeline
    return None


def _pipeline_names_from_entries(entries: object) -> list[str]:
    if not isinstance(entries, list):
        return []
    names: list[str] = []
    for entry in entries:
        pipeline = _pipeline_name_from_entry(entry)
        if pipeline is not None:
            names.append(pipeline)
    return names


def _composite_source_pipeline_names(payload: dict[str, object]) -> tuple[str, ...]:
    composite = payload.get("composite")
    if not isinstance(composite, dict):
        return ()
    names: list[str] = []
    seed_pipeline = _pipeline_name_from_entry(composite.get("seed"))
    if seed_pipeline is not None:
        names.append(seed_pipeline)
    for key in ("dependencies", "enrichers"):
        names.extend(_pipeline_names_from_entries(composite.get(key)))
    return tuple(dict[str, object].fromkeys(names))


def _provider_order_from_column_group(
    entry: object, field_name: str
) -> tuple[str, ...] | None:
    if not isinstance(entry, dict):
        return None
    fields = entry.get("fields")
    if not isinstance(fields, list) or field_name not in fields:
        return None
    provider_order = entry.get("provider_order")
    if not isinstance(provider_order, list):
        return ()
    providers = [
        provider
        for provider in provider_order
        if isinstance(provider, str) and provider
    ]
    return tuple(dict[str, object].fromkeys(providers))


def _composite_field_provider_order(
    payload: dict[str, object],
    field_name: str,
) -> tuple[str, ...]:
    composite = payload.get("composite")
    if not isinstance(composite, dict):
        return ()
    merge = composite.get("merge")
    if not isinstance(merge, dict):
        return ()
    column_groups = merge.get("column_groups")
    if not isinstance(column_groups, list):
        return ()
    for entry in column_groups:
        result = _provider_order_from_column_group(entry, field_name)
        if result is not None:
            return result
    return ()


def _lineage_field_alias(
    composite: dict[str, object], *, field_name: str, provider_name: str
) -> str | None:
    lineage = composite.get("lineage")
    if not isinstance(lineage, dict):
        return None
    provider_lookup_fields = lineage.get("provider_lookup_fields")
    if not isinstance(provider_lookup_fields, dict):
        return None
    provider_entry = provider_lookup_fields.get(provider_name)
    if not isinstance(provider_entry, dict):
        return None
    alias = provider_entry.get(field_name)
    if isinstance(alias, str) and alias:
        return alias
    return None


def _mapped_source_fields(
    merge: object, *, field_name: str, provider_name: str
) -> list[str]:
    if not isinstance(merge, dict):
        return []
    field_mappings = merge.get("field_mappings")
    if not isinstance(field_mappings, dict):
        return []
    mapped: list[str] = []
    for source_ref, target_field in field_mappings.items():
        if target_field != field_name or not isinstance(source_ref, str):
            continue
        parts = source_ref.split(".")
        if len(parts) == 3 and parts[0] == provider_name and parts[2]:
            mapped.append(parts[2])
    return mapped


def _composite_source_field_candidates(
    payload: dict[str, object],
    *,
    pipeline_name: str,
    field_name: str,
    provider_name: str,
) -> tuple[str, ...]:
    composite = payload.get("composite")
    if not isinstance(composite, dict):
        return (field_name,)
    candidates: list[str] = [field_name]
    alias = _lineage_field_alias(
        composite, field_name=field_name, provider_name=provider_name
    )
    if alias is not None:
        candidates.append(alias)
    candidates.extend(
        _mapped_source_fields(
            composite.get("merge"), field_name=field_name, provider_name=provider_name
        )
    )
    candidates.extend(
        COMPOSITE_SOURCE_FIELD_TYPE_ALIAS_HINTS.get((pipeline_name, field_name), ())
    )
    return tuple(dict[str, object].fromkeys(candidate for candidate in candidates if candidate))


def _first_known_source_field_type(
    *,
    source_pipeline: str,
    pipeline_name: str,
    field_name: str,
    payload: dict[str, object],
    provider_name: str,
) -> str | None:
    for candidate_field in _composite_source_field_candidates(
        payload,
        pipeline_name=pipeline_name,
        field_name=field_name,
        provider_name=provider_name,
    ):
        field_type = _entity_schema_field_type(source_pipeline, candidate_field)
        if field_type != "unknown":
            return field_type
    return None


def _inherited_types_from_sources(
    *,
    pipeline_name: str,
    field_name: str,
    payload: dict[str, object],
    provider_order: tuple[str, ...],
    single_provider_field: bool,
) -> str | set[str]:
    inherited_types: set[str] = set()
    for source_pipeline in _composite_source_pipeline_names(payload):
        provider_name = source_pipeline.split("_", maxsplit=1)[0]
        if provider_order and provider_name not in provider_order:
            continue
        field_type = _first_known_source_field_type(
            source_pipeline=source_pipeline,
            pipeline_name=pipeline_name,
            field_name=field_name,
            payload=payload,
            provider_name=provider_name,
        )
        if field_type is None:
            continue
        if single_provider_field:
            return field_type
        inherited_types.add(field_type)
    return inherited_types


def _composite_inherited_field_type(
    *,
    pipeline_name: str,
    field_name: str,
    payload: dict[str, object],
) -> str:
    contract_type = _composite_field_type(pipeline_name, field_name)
    if contract_type != "unknown":
        return contract_type
    authority_override = _composite_schema_authority_override(
        pipeline_name,
        field_name,
    )
    if authority_override is not None:
        return authority_override["field_type"]
    provider_order = _composite_field_provider_order(payload, field_name)
    result = _inherited_types_from_sources(
        pipeline_name=pipeline_name,
        field_name=field_name,
        payload=payload,
        provider_order=provider_order,
        single_provider_field=len(provider_order) == 1,
    )
    if isinstance(result, str):
        return result
    result.discard("unknown")
    if len(result) == 1:
        return next(iter(result))
    return "unknown"


def _composite_schema_coverage(pipeline_name: str, field_name: str) -> str:
    if _composite_field_type(pipeline_name, field_name) != "unknown":
        return "gold_contract:explicit"
    authority_override = _composite_schema_authority_override(
        pipeline_name,
        field_name,
    )
    if authority_override is not None:
        return f"authority_registry:{authority_override['authority_id']}"
    return "gold_contract:inherited"


@cache
def _ensure_chembl_policy_registry_initialized() -> None:
    load_cache = initialize_bootstrap_chembl_policy_registry.__globals__.get(
        "_load_chembl_policy_registry_data"
    )
    if load_cache is not None:
        load_cache.cache_clear()
    initialize_bootstrap_chembl_policy_registry(Path("configs"))


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
    registered_source = _registered_controlled_vocabulary_source(
        provider=provider,
        entity=entity,
        field_name=field_name,
    )
    if registered_source is not None:
        return registered_source

    return _inferred_controlled_vocabulary_source(
        provider=provider,
        entity=entity,
        normalizer_name=normalizer_name,
        notes=notes,
    )


def _registered_controlled_vocabulary_source(
    *,
    provider: str,
    entity: str,
    field_name: str,
) -> str | None:
    if field_name == "oa_status" and provider != "chembl":
        return _OA_STATUS_SOURCE
    if entity == "publication" and _is_publication_taxonomy_field(field_name):
        return _PUBLICATION_TYPE_CLASSIFICATION_SOURCE
    configured_source = ENUM_CONFIG_SOURCES.get((provider, entity, field_name))
    if configured_source is not None:
        return configured_source
    reference_source = REFERENCE_ID_SOURCES.get((provider, entity, field_name))
    if reference_source is not None:
        return reference_source
    structured_policy = _publication_structured_policy(
        provider=provider,
        entity=entity,
        field_name=field_name,
    )
    if structured_policy is not None and structured_policy.identifier_family:
        return _REFERENCE_ID_SOURCE

    semantic_sensitive_policy = structured_payload_policy(
        f"{provider}.{entity}",
        field_name,
    )
    if semantic_sensitive_policy is not None:
        controlled_vocabulary_source = (
            semantic_sensitive_policy.controlled_vocabulary_source
        )
        if controlled_vocabulary_source is not None:
            return controlled_vocabulary_source

    if provider == "chembl":
        policy_surface = chembl_policy_surface(entity, field_name)
        if policy_surface is not None:
            return policy_surface.registry_source
    return None


def _inferred_controlled_vocabulary_source(
    *,
    provider: str,
    entity: str,
    normalizer_name: str,
    notes: str,
) -> str:
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
    if normalizer_name in {"normalize_profile_oa_status", "normalize_oa_status"}:
        return _OA_STATUS_SOURCE
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


_registry_values = cache(_registry_values)


@cache
def _load_entity_config(provider: str, entity: str) -> dict[str, object]:
    path = Path("configs") / "entities" / provider / f"{entity}.yaml"
    if not path.exists():
        return {}
    return _load_yaml(path)


@cache
def _load_non_chembl_observed_value_inventory() -> dict[str, object]:
    return _load_yaml(NON_CHEMBL_OBSERVED_VALUES_FIXTURE)


def _non_chembl_pipeline_inventory(pipeline_name: str) -> dict[str, object]:
    payload = _load_non_chembl_observed_value_inventory()
    pipelines = payload.get("pipelines")
    if not isinstance(pipelines, dict):
        return {}
    pipeline_payload = pipelines.get(pipeline_name)
    return pipeline_payload if isinstance(pipeline_payload, dict) else {}


def _inventory_mapping(
    pipeline_name: str,
    section_name: str,
) -> dict[str, object]:
    payload = _non_chembl_pipeline_inventory(pipeline_name)
    section = payload.get(section_name)
    return section if isinstance(section, dict) else {}


def _classification_spec(pipeline_name: str, field_name: str) -> dict[str, str]:
    payload = _inventory_mapping(pipeline_name, "classification").get(field_name)
    if isinstance(payload, dict):
        return {
            str(key): str(value) for key, value in payload.items() if value is not None
        }
    if payload is None:
        return {}
    return {"category": str(payload)}


def _inventory_section_fragments(pipeline_name: str, field_name: str) -> list[str]:
    fragments: list[str] = []
    for section_name in _NON_CHEMBL_INVENTORY_SECTIONS:
        if field_name in _inventory_mapping(pipeline_name, section_name):
            fragments.append(
                f"{NON_CHEMBL_OBSERVED_VALUES_FIXTURE.as_posix()}#pipelines."
                f"{pipeline_name}.{section_name}.{field_name}"
            )
    if field_name in _inventory_mapping(pipeline_name, "structured_json_shapes"):
        fragments.append(
            f"{NON_CHEMBL_OBSERVED_VALUES_FIXTURE.as_posix()}#pipelines."
            f"{pipeline_name}.structured_json_shapes.{field_name}"
        )
    if field_name in _inventory_mapping(pipeline_name, "classification"):
        fragments.append(
            f"{NON_CHEMBL_OBSERVED_VALUES_FIXTURE.as_posix()}#pipelines."
            f"{pipeline_name}.classification.{field_name}"
        )
    return fragments


def _default_observed_source(pipeline_name: str, field_name: str) -> str:
    return ",".join(_inventory_section_fragments(pipeline_name, field_name))


def _default_identifier_family(
    *,
    provider: str,
    entity: str,
    field_name: str,
) -> str:
    structured_policy = _publication_structured_policy(
        provider=provider,
        entity=entity,
        field_name=field_name,
    )
    if structured_policy is not None and structured_policy.identifier_family:
        return structured_policy.identifier_family
    return _NON_CHEMBL_IDENTIFIER_FAMILIES.get((provider, entity, field_name), "")


def _default_collection_semantics(
    *,
    provider: str,
    entity: str,
    field_name: str,
) -> str:
    semantic_policy = structured_payload_policy(f"{provider}.{entity}", field_name)
    if semantic_policy is not None:
        return semantic_policy.collection_semantics.value
    structured_policy = _publication_structured_policy(
        provider=provider,
        entity=entity,
        field_name=field_name,
    )
    if structured_policy is not None:
        return structured_policy.collection_semantics.value
    return "scalar"


def _is_publication_taxonomy_field(field_name: str) -> bool:
    return field_name in _PUBLICATION_TAXONOMY_FIELDS


def _default_non_chembl_classification(
    *,
    provider: str,
    entity: str,
    field_name: str,
    semantic_category: str,
    strictness: str,
) -> str:
    if _is_publication_taxonomy_field(field_name):
        return "derived_vocabulary"
    if strictness in {"strict_boolean", "strict_flag"}:
        return "strict_boolean"
    if strictness == "strict_enum":
        return "strict_enum"
    if strictness == "controlled_unit" or semantic_category == "controlled_vocabulary":
        return "controlled_vocabulary"
    if _default_identifier_family(
        provider=provider, entity=entity, field_name=field_name
    ):
        return "identifier_namespace"
    semantic_policy = structured_payload_policy(f"{provider}.{entity}", field_name)
    if semantic_policy is not None:
        return (
            "structured_json_sidecar"
            if semantic_policy.requires_raw_sidecar_before_semantic_transform
            else "structured_json_canonical_only"
        )
    if (
        _publication_structured_policy(
            provider=provider,
            entity=entity,
            field_name=field_name,
        )
        is not None
    ):
        return "structured_json_collection"
    return semantic_category


def _non_chembl_row_metadata(row: dict[str, str]) -> dict[str, str]:
    metadata = {
        "classification": "",
        "identifier_family": "",
        "collection_semantics": "scalar",
        "raw_sidecar": "",
        "canonical_sidecar": "",
        "dq_rule": row.get("dq_coverage", ""),
        "composite_usage": "",
        "observed_source": "",
    }
    if (
        row.get("pipeline_kind") != ENTITY_PIPELINE_KIND
        or row.get("pipeline_name") not in NON_CHEMBL_PIPELINES
    ):
        return metadata

    pipeline_name = row["pipeline_name"]
    provider = row["provider"]
    entity = row["entity"]
    field_name = row["field_name"]
    classification = _classification_spec(pipeline_name, field_name)
    semantic_policy = structured_payload_policy(f"{provider}.{entity}", field_name)
    publication_policy = _publication_structured_policy(
        provider=provider,
        entity=entity,
        field_name=field_name,
    )
    metadata["classification"] = classification.get("category", "") or (
        _default_non_chembl_classification(
            provider=provider,
            entity=entity,
            field_name=field_name,
            semantic_category=row.get("semantic_category", ""),
            strictness=row.get("strictness", ""),
        )
    )
    metadata["identifier_family"] = classification.get("identifier_family", "") or (
        _default_identifier_family(
            provider=provider,
            entity=entity,
            field_name=field_name,
        )
    )
    metadata["collection_semantics"] = classification.get(
        "collection_semantics",
        "",
    ) or _default_collection_semantics(
        provider=provider,
        entity=entity,
        field_name=field_name,
    )
    metadata["raw_sidecar"] = classification.get("raw_sidecar", "")
    if not metadata["raw_sidecar"]:
        if semantic_policy is not None and semantic_policy.raw_sidecar_field:
            metadata["raw_sidecar"] = semantic_policy.raw_sidecar_field
        elif publication_policy is not None and publication_policy.raw_sidecar_field:
            metadata["raw_sidecar"] = publication_policy.raw_sidecar_field
        else:
            metadata["raw_sidecar"] = ""
    metadata["canonical_sidecar"] = classification.get("canonical_sidecar", "") or (
        semantic_policy.canonical_sidecar_field if semantic_policy is not None else ""
    )
    metadata["composite_usage"] = classification.get("composite_usage", "")
    metadata["observed_source"] = classification.get("observed_source", "") or (
        _default_observed_source(pipeline_name, field_name)
    )
    return metadata


def _augment_row_with_inventory_metadata(row: dict[str, str]) -> dict[str, str]:
    augmented = dict[str, object](row)
    augmented.update(_non_chembl_row_metadata(augmented))
    return augmented


def _inventory_fields_for_pipeline(pipeline_name: str) -> set[str]:
    fields: set[str] = set()
    for section_name in _NON_CHEMBL_INVENTORY_SECTIONS + (
        "structured_json_shapes",
        "classification",
    ):
        fields.update(_inventory_mapping(pipeline_name, section_name))
    primary_key = _non_chembl_pipeline_inventory(pipeline_name).get("primary_key")
    if isinstance(primary_key, str) and primary_key:
        fields.add(primary_key)
    return fields


def _non_chembl_inventory_row(
    rows_by_key: dict[tuple[str, str], dict[str, str]],
    *,
    pipeline_name: str,
    field_name: str,
) -> dict[str, str]:
    row = rows_by_key.get((pipeline_name, field_name))
    if row is None:
        raise ValueError(
            f"Missing non-ChEMBL normalization evidence row for "
            f"{pipeline_name}.{field_name}"
        )
    return row


def _validate_non_chembl_row_required_evidence(
    row: dict[str, str], *, pipeline_name: str, field_name: str
) -> None:
    if not row.get("classification"):
        raise ValueError(
            f"Missing classification evidence for {pipeline_name}.{field_name}"
        )
    if not row.get("observed_source"):
        raise ValueError(
            f"Missing observed-source evidence for {pipeline_name}.{field_name}"
        )


def _validate_non_chembl_row_structured_evidence(
    row: dict[str, str], *, pipeline_name: str, field_name: str
) -> None:
    if row.get("raw_sidecar") and row.get("canonical_sidecar"):
        return
    if row.get("classification") == "structured_json_canonical_only" and row.get(
        "canonical_sidecar"
    ):
        return
    raise ValueError(
        f"Missing structured sidecar evidence for {pipeline_name}.{field_name}"
    )


def _validate_non_chembl_inventory_field(
    rows_by_key: dict[tuple[str, str], dict[str, str]],
    *,
    pipeline_name: str,
    field_name: str,
    structured_fields: set[str],
) -> None:
    row = _non_chembl_inventory_row(
        rows_by_key,
        pipeline_name=pipeline_name,
        field_name=field_name,
    )
    _validate_non_chembl_row_required_evidence(
        row, pipeline_name=pipeline_name, field_name=field_name
    )
    if field_name in structured_fields:
        _validate_non_chembl_row_structured_evidence(
            row, pipeline_name=pipeline_name, field_name=field_name
        )


def _validate_non_chembl_inventory_rows(rows: list[dict[str, str]]) -> None:
    rows_by_key = {(row["pipeline_name"], row["field_name"]): row for row in rows}
    for pipeline_name in sorted(NON_CHEMBL_PIPELINES):
        structured_fields = set(
            _inventory_mapping(pipeline_name, "structured_json_shapes")
        )
        for field_name in sorted(_inventory_fields_for_pipeline(pipeline_name)):
            _validate_non_chembl_inventory_field(
                rows_by_key,
                pipeline_name=pipeline_name,
                field_name=field_name,
                structured_fields=structured_fields,
            )


def _dq_allowed_values(
    *,
    provider: str,
    entity: str,
    field_name: str,
) -> frozenset[str]:
    dq_config = _load_dq_config(provider, entity)
    if dq_config is None:
        return frozenset()
    matches = _matching_dq_enum_rules(
        dq_config.field_validations, field_name=field_name
    )
    if len(matches) != 1:
        return frozenset()
    return frozenset(str(value) for value in matches[0].allowed)


_dq_allowed_values = cache(_dq_allowed_values)


def _matching_dq_enum_rules(
    field_validations: list[object], *, field_name: str
) -> list[object]:
    return [
        rule
        for rule in field_validations
        if rule.field == field_name and rule.validation_type == "enum"
    ]


def _csv_filter_values(raw: str) -> frozenset[str]:
    result: set[str] = set()
    for part in raw.split(","):
        stripped = part.strip()
        if stripped:
            result.add(stripped)
    return frozenset(result)


def _sequence_filter_values(raw: list | tuple | set) -> frozenset[str]:
    result: set[str] = set()
    for item in raw:
        stripped = str(item).strip()
        if stripped:
            result.add(stripped)
    return frozenset(result)


def _filter_value_set(raw_values: object) -> frozenset[str]:
    if raw_values is None:
        return frozenset()
    if isinstance(raw_values, str):
        return _csv_filter_values(raw_values)
    if isinstance(raw_values, (list, tuple, set)):
        return _sequence_filter_values(raw_values)
    stripped = str(raw_values).strip()
    if not stripped:
        return frozenset()
    return frozenset({stripped})


def _filter_mapping(config: dict[str, object]) -> dict[str, object]:
    filters = config.get("filters") or {}
    return filters if isinstance(filters, dict) else {}


def _extraction_param_values(
    filters: dict[str, object], *, field_name: str
) -> frozenset[str]:
    extraction_params = filters.get("extraction_params") or {}
    if not isinstance(extraction_params, dict):
        return frozenset()
    return _filter_value_set(extraction_params.get(field_name)) | _filter_value_set(
        extraction_params.get(f"{field_name}__in")
    )


def _column_filter_values(
    filters: dict[str, object], *, filter_key: str, field_name: str
) -> frozenset[str]:
    filter_config = filters.get(filter_key) or {}
    if not isinstance(filter_config, dict):
        return frozenset()
    columns = filter_config.get("columns") or {}
    if not isinstance(columns, dict):
        return frozenset()
    return _filter_value_set(columns.get(field_name))


def _filter_values(
    *,
    provider: str,
    entity: str,
    field_name: str,
) -> frozenset[str]:
    config = _load_entity_config(provider, entity)
    if not config:
        return frozenset()
    filters = _filter_mapping(config)
    if not filters:
        return frozenset()

    return (
        _extraction_param_values(filters, field_name=field_name)
        | _column_filter_values(
            filters, filter_key="silver_filters", field_name=field_name
        )
        | _column_filter_values(
            filters, filter_key="gold_filters", field_name=field_name
        )
    )


_filter_values = cache(_filter_values)


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


_STRICTNESS_TO_SEMANTIC_CATEGORY: dict[str, str] = {
    "strict_enum": "strict_enum",
    "strict_operator": "strict_enum",
    "strict_boolean": "strict_enum",
    "strict_flag": "strict_enum",
    "strict_json": "structured_json",
    "canonical_ontology_id": "ontology_reference_identifier",
    "controlled_unit": "controlled_vocabulary",
    "normalization_only": "free_text",
}


def _chembl_semantic_category(entity: str, field_name: str) -> str | None:
    policy_surface = chembl_policy_surface(entity, field_name)
    if policy_surface is not None:
        return policy_surface.category
    if field_name in chembl_json_fields(f"chembl_{entity}"):
        return "structured_json"
    return None


def _structured_policy_semantic_category(
    *,
    provider: str,
    entity: str,
    field_name: str,
) -> str | None:
    structured_policy = _publication_structured_policy(
        provider=provider,
        entity=entity,
        field_name=field_name,
    )
    if structured_policy is None:
        return None
    if structured_policy.identifier_family:
        return "ontology_reference_identifier"
    return "structured_json"


def _semantic_category(
    *,
    provider: str,
    entity: str,
    field_name: str,
    strictness: str,
) -> str:
    if entity == "publication" and _is_publication_taxonomy_field(field_name):
        return "derived_vocabulary"
    if provider == "chembl":
        chembl_category = _chembl_semantic_category(entity, field_name)
        if chembl_category is not None:
            return chembl_category
    if REFERENCE_ID_SOURCES.get((provider, entity, field_name)) is not None:
        return "ontology_reference_identifier"
    structured_category = _structured_policy_semantic_category(
        provider=provider,
        entity=entity,
        field_name=field_name,
    )
    if structured_category is not None:
        return structured_category
    return _STRICTNESS_TO_SEMANTIC_CATEGORY.get(strictness, strictness)


def _governed_hash_ordering(
    *,
    provider: str,
    entity: str,
    field_name: str,
) -> str | None:
    semantic_policy = structured_payload_policy(f"{provider}.{entity}", field_name)
    if semantic_policy is not None:
        if semantic_policy.collection_semantics.value == "unordered_set":
            return "set_like"
        return "order_sensitive"

    publication_policy = _publication_structured_policy(
        provider=provider,
        entity=entity,
        field_name=field_name,
    )
    if publication_policy is not None:
        return publication_policy.hash_ordering
    return None


def _hash_ordering(
    *,
    provider: str,
    entity: str,
    field_name: str,
    include_in_hash: bool | None,
    set_like: bool,
) -> str:
    governed_ordering = _governed_hash_ordering(
        provider=provider,
        entity=entity,
        field_name=field_name,
    )
    if governed_ordering is not None:
        return governed_ordering
    if include_in_hash is False:
        return "not_hashed"
    if set_like:
        return "set_like"
    return "order_sensitive"


def _publication_structured_policy(
    *,
    provider: str,
    entity: str,
    field_name: str,
) -> Any | None:
    if entity != "publication":
        return None
    return publication_structured_field_policy(f"{provider}.{entity}", field_name)


def _strictness(
    *,
    field_name: str,
    normalization_source: str,
    normalizer_name: str,
    notes: str,
) -> str:
    normalized_notes = notes.casefold()
    if field_name in {"relation", "activity_relation", "parameter_relation"}:
        return "strict_operator"
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
        "normalize_profile_pubchem_cid",
    }:
        return "canonical_identifier"
    if normalizer_name == "normalize_profile_json_string":
        return "canonical_json"
    if normalizer_name == "normalize_profile_json_string_strict":
        return "strict_json"
    if normalizer_name == "normalize_profile_boolean":
        return "strict_boolean"
    if normalizer_name in {"normalize_profile_oa_status", "normalize_oa_status"}:
        return "strict_enum"
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
    if (
        "reviewed_flag_code" in normalizer_name
        or "flag-like provider code" in normalized_notes
    ):
        return "strict_flag"
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
    if semantic_category == "free_text" and "controlled-vocabulary" in notes.casefold():
        semantic_category = "controlled_vocabulary"
    if (
        controlled_vocabulary_source == _CHEMBL_REFERENCE_SOURCES_CONFIG
        and semantic_category == "canonical_identifier"
    ):
        semantic_category = "reference_identifier"
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
    domain_coverage = _resolve_field_value(
        pipeline_name=pipeline_name,
        field_name=field_name,
        available_values=_domain_schema_field_coverage_by_pipeline(pipeline_name),
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
    pipeline_name: str,
    provider: str,
    entity: str,
    field_name: str,
    strictness: str,
) -> str:
    if provider != "composite" and _load_dq_config(provider, entity) is None:
        return "dq_config:unavailable"
    coverage = _resolve_field_value(
        pipeline_name=pipeline_name,
        field_name=field_name,
        available_values=_dq_rule_coverage_by_field(provider, entity),
    )
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
    if key == "inchi_key":
        return (
            "Validate InChIKey through the canonical domain value-object contract, "
            "then emit uppercase join-canonical text."
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
    if key == "title":
        return (
            "Normalize fallback title join text through canonical title cleanup "
            "while preserving case."
        )
    if key == "target_id":
        return (
            "Validate ChEMBL target identifier through the canonical domain value-"
            "object contract, then emit uppercase join-canonical text."
        )
    if key == "uniprot_accession":
        return (
            "Validate UniProt accession through the canonical domain value-object "
            "contract, then emit uppercase join-canonical text."
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
        profile_rule = _resolve_profile_rule(
            profile=profile,
            pipeline_name=pipeline_name,
            field_name=field_name,
        )
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
        else:
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
        for alias_field_name in _alias_field_names(
            pipeline_name=pipeline_name,
            field_name=field_name,
            schema_field_names=schema.names,
        ):
            alias_profile_rule = _resolve_profile_rule(
                profile=profile,
                pipeline_name=pipeline_name,
                field_name=alias_field_name,
            )
            if alias_profile_rule is not None:
                rows.append(
                    _entity_profile_row(
                        provider=provider,
                        entity=entity,
                        pipeline_name=pipeline_name,
                        field_name=alias_field_name,
                        field_type=field_type,
                        arrow_nullable=field.nullable,
                        profile_rule=alias_profile_rule,
                    )
                )
            else:
                source, normalizer, summary = _fallback_contract(
                    rule_set,
                    field_name=alias_field_name,
                    field_type=field_type,
                )
                rows.append(
                    _entity_fallback_row(
                        provider=provider,
                        entity=entity,
                        pipeline_name=pipeline_name,
                        field_name=alias_field_name,
                        field_type=field_type,
                        arrow_nullable=field.nullable,
                        source=source,
                        normalizer=normalizer,
                        summary=summary,
                    )
                )
    return rows


def _alias_field_names(
    *,
    pipeline_name: str,
    field_name: str,
    schema_field_names: list[str],
) -> tuple[str, ...]:
    """Return reviewed alias rows that should also be emitted for one Silver field."""
    aliases = ENTITY_PROFILE_FIELD_ALIASES.get(pipeline_name, {})
    reverse_aliases = {alias: source for source, alias in aliases.items()}
    candidates = [
        aliases.get(field_name),
        reverse_aliases.get(field_name),
    ]
    return tuple(
        candidate
        for candidate in dict[str, object].fromkeys(candidates)
        if candidate is not None and candidate not in schema_field_names
    )


def _field_lookup_candidates(*, pipeline_name: str, field_name: str) -> tuple[str, ...]:
    """Try the shipped field name first, then any reviewed alias seam in either direction."""
    aliases = ENTITY_PROFILE_FIELD_ALIASES.get(pipeline_name, {})
    reverse_aliases = {alias: source for source, alias in aliases.items()}
    candidates = [field_name]
    alias_name = aliases.get(field_name)
    if alias_name is not None:
        candidates.append(alias_name)
    source_name = reverse_aliases.get(field_name)
    if source_name is not None:
        candidates.append(source_name)
    return tuple(dict[str, object].fromkeys(candidates))


def _resolve_profile_rule(
    *, profile: Any | None, pipeline_name: str, field_name: str
) -> Any | None:
    if profile is None:
        return None
    for candidate in _field_lookup_candidates(
        pipeline_name=pipeline_name,
        field_name=field_name,
    ):
        rule = profile.rule_for(candidate)
        if rule is not None:
            return rule
    return None


def _resolve_field_value(
    *, pipeline_name: str, field_name: str, available_values: dict[str, str]
) -> str | None:
    for candidate in _field_lookup_candidates(
        pipeline_name=pipeline_name,
        field_name=field_name,
    ):
        value = available_values.get(candidate)
        if value is not None:
            return value
    return None


def _profile_lookup_field_name(*, pipeline_name: str, field_name: str) -> str:
    """Resolve reviewed Silver legacy aliases to canonical profile/schema fields."""
    return _field_lookup_candidates(
        pipeline_name=pipeline_name,
        field_name=field_name,
    )[0]


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
    notes = _augment_structured_payload_policy_notes(
        provider=provider,
        entity=entity,
        field_name=field_name,
        notes=notes,
    )
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
            provider=provider,
            entity=entity,
            field_name=field_name,
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
            pipeline_name=pipeline_name,
            provider=provider,
            entity=entity,
            field_name=field_name,
            strictness=strictness,
        ),
        "notes": notes,
    }


def _augment_structured_payload_policy_notes(
    *,
    provider: str,
    entity: str,
    field_name: str,
    notes: str,
) -> str:
    """Append raw/canonical sidecar governance notes for semantic-sensitive JSON."""
    policy = structured_payload_policy(f"{provider}.{entity}", field_name)
    if policy is None:
        return notes

    semantics = policy.collection_semantics.value.replace("_", " ")
    if policy.requires_raw_sidecar_before_semantic_transform:
        governance_note = (
            f"Semantic-sensitive {semantics} payload: canonical JSON is not a raw "
            f"provider substitute; semantic transforms must materialize "
            f"{policy.raw_sidecar_field} and {policy.canonical_sidecar_field} before "
            f"replacing or deriving provider payload semantics."
        )
    else:
        governance_note = (
            f"Semantic-sensitive {semantics} payload: the persisted canonical JSON "
            f"field {policy.canonical_sidecar_field} is the ratified evidence surface; "
            f"future semantic transforms must not assume an implicit raw sidecar or "
            f"replace provider semantics without an explicit contract change."
        )
    if not notes:
        return governance_note
    return f"{notes} {governance_note}"


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
            pipeline_name=pipeline_name,
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
        rows.append(_composite_row(pipeline_name, field_name, join_keys, payload))
    return rows


def _composite_row(
    pipeline_name: str,
    field_name: str,
    join_keys: set[str],
    payload: dict[str, object],
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
        "field_type": _composite_inherited_field_type(
            pipeline_name=pipeline_name,
            field_name=field_name,
            payload=payload,
        ),
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
        "schema_coverage": _composite_schema_coverage(pipeline_name, field_name),
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
    _ensure_chembl_policy_registry_initialized()
    rows: list[dict[str, str]] = []
    rows.extend(_entity_field_matrix_rows())
    rows.extend(_composite_field_matrix_rows())
    augmented_rows = [_augment_row_with_inventory_metadata(row) for row in rows]
    _validate_non_chembl_inventory_rows(augmented_rows)
    return augmented_rows


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
        contract=(CANONICAL_CONTRACT_REF_RAW, " v2 "),
        normalization_profile=(
            CANONICAL_NORMALIZATION_PROFILE_REF_RAW,
            CANONICAL_NORMALIZATION_PROFILE_VERSION_RAW,
            CANONICAL_NORMALIZATION_PROFILE_HASH_RAW,
        ),
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
    if _is_governed_raw_structured_sidecar(provider, entity, field_name, rule):
        stats.non_meta_total += 1
        stats.non_meta_ok += 1
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


def _is_governed_raw_structured_sidecar(
    provider: str,
    entity: str,
    field_name: str,
    rule: Any,
) -> bool:
    """Return whether passthrough is an intentional raw-sidecar policy seam."""
    if rule.normalizer is not normalize_profile_passthrough:
        return False
    profile_name = f"{provider}.{entity}"
    return any(
        policy.profile_name == profile_name and field_name == policy.raw_sidecar_field
        for policy in semantic_sensitive_structured_payload_policies()
    )


def _is_json_string_normalizer(rule: Any) -> bool:
    """Return whether a rule uses the effective JSON-string normalizer family."""
    normalizer_name = getattr(rule.normalizer, "__name__", "")
    normalized_notes = str(getattr(rule, "notes", "")).casefold()
    return (
        rule.normalizer is normalize_profile_json_string
        or normalizer_name == "normalize_profile_json_string"
        or normalizer_name == "normalize_profile_json_string_unordered_collection"
        or rule.normalizer is normalize_profile_json_string_strict
        or normalizer_name == "normalize_profile_json_string_strict"
        or rule.normalizer is normalize_profile_target_component_types
        or normalizer_name == "normalize_profile_target_component_types"
        or rule.normalizer is normalize_profile_target_component_relationships
        or normalizer_name == "normalize_profile_target_component_relationships"
        or normalizer_name == "normalize_profile_json_string_list_vocabulary_strict"
        or "canonical json array" in normalized_notes
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


def render_markdown(
    rows: list[dict[str, str]],
    *,
    surface_kpis: list[dict[str, object]] | None = None,
    semantic_kpis: list[dict[str, object]] | None = None,
) -> str:
    headers = list(CSV_COLUMNS)
    effective_surface_kpis = (
        build_surface_coverage_kpis(rows) if surface_kpis is None else surface_kpis
    )
    effective_semantic_kpis = (
        build_profile_semantic_invariants() if semantic_kpis is None else semantic_kpis
    )
    lines = _markdown_intro_lines()
    lines.extend(_surface_kpi_lines(effective_surface_kpis))
    lines.extend(_semantic_kpi_lines(effective_semantic_kpis))
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


def build_artifacts(
    rows: list[dict[str, str]] | None = None,
    *,
    surface_kpis: list[dict[str, object]] | None = None,
    semantic_kpis: list[dict[str, object]] | None = None,
) -> dict[str, str]:
    matrix_rows = build_field_matrix_rows() if rows is None else rows
    effective_surface_kpis = (
        build_surface_coverage_kpis(matrix_rows)
        if surface_kpis is None
        else surface_kpis
    )
    effective_semantic_kpis = (
        build_profile_semantic_invariants() if semantic_kpis is None else semantic_kpis
    )
    non_chembl_rows = [
        row
        for row in matrix_rows
        if row["pipeline_kind"] == ENTITY_PIPELINE_KIND
        and row["pipeline_name"] in NON_CHEMBL_PIPELINES
    ]
    return {
        CSV_NAME: render_csv(matrix_rows),
        MD_NAME: render_markdown(
            matrix_rows,
            surface_kpis=effective_surface_kpis,
            semantic_kpis=effective_semantic_kpis,
        ),
        NON_CHEMBL_MD_NAME: render_markdown(
            non_chembl_rows,
            surface_kpis=effective_surface_kpis,
            semantic_kpis=effective_semantic_kpis,
        ),
    }


def _normalize_newlines(payload: str) -> str:
    """Normalize line endings for deterministic cross-platform comparisons."""
    return payload.replace("\r\n", "\n").replace("\r", "\n")


def write_artifacts(out_dir: Path) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = build_field_matrix_rows()
    surface_kpis = build_surface_coverage_kpis(rows)
    semantic_kpis = build_profile_semantic_invariants()
    artifacts = build_artifacts(
        rows,
        surface_kpis=surface_kpis,
        semantic_kpis=semantic_kpis,
    )
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
    return _build_arg_parser()


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
