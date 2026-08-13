"""Static registries and runtime bindings for the normalization matrix."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any
import pyarrow as pa
import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from scripts.docs.common.bootstrap import ensure_repo_imports
else:
    from scripts.docs.common.bootstrap import ensure_repo_imports

ensure_repo_imports(include_src=True)

from bioetl.application.composite.checkpoint import (
    ExpectedCheckpointContext,
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
from bioetl.domain.config import FieldValidation
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

CSV_COLUMNS: tuple[str, ...] = (
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


