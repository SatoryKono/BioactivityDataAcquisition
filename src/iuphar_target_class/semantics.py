"""RF-001 classification semantics: field layers, statuses, and capability matrix.

This module is the immutable contract baseline for issue #13309. It records
vocabulary and decision boundaries only; it does not reclassify rows or admit
biological accuracy. Historical stage-0/policy artifacts remain the provenance
sources. New rule, normalization, classifier, or table versions are published
separately and must not rewrite originals.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

# Mirrored from policy.py (same literals) to avoid an import cycle.
# Tests assert equality with policy.WORKING_CLASSES / BASE_MISSING_MARKERS.
WORKING_CLASSES: tuple[str, ...] = (
    "Receptor",
    "Ion Channel",
    "Enzyme",
    "Transporter",
    "Other Protein Target",
)
BASE_MISSING_MARKERS: tuple[str, ...] = (
    "#n/a",
    "N/A",
    "n/a",
    "",
)
# Executing profile pin. ``plan-v1-r8`` is the previous baseline and stays on
# historical runs. This literal must match ``policy.LOCAL_CATALOG_VERSION``.
RULES_VERSION = "local-rules-2026.11.23"

RF001_CONTRACT_VERSION = "rf001-2026-11-23"
RF001_ISSUE = "https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13309"
RF001_EPIC = "https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13308"

# Profile / contract versioning surfaces that RF work may advance later.
NORMALIZATION_VERSION_APPROVED = None  # missing_markers version still unset
CLASSIFICATION_SCHEMA_V30 = "3.0.0"
CLASSIFICATION_SCHEMA_V31 = "3.1.0"
TABLE_CONTRACT_V30 = "chembl_target_v3.0"
TABLE_CONTRACT_V31 = "chembl_target_v3.1"

FIELD_LAYERS: Mapping[str, Mapping[str, str]] = MappingProxyType(
    {
        "target_type": MappingProxyType(
            {
                "layer": "chembl_object",
                "meaning": "ChEMBL object/target type; never overwritten by IUPHAR or local rules",
                "examples": "SINGLE PROTEIN, PROTEIN COMPLEX, ORGANISM, ...",
            }
        ),
        "iuphar_target_id": MappingProxyType(
            {
                "layer": "iuphar_reference",
                "meaning": "Matched GtoPdb/IUPHAR public target id from the pinned snapshot",
            }
        ),
        "iuphar_class": MappingProxyType(
            {
                "layer": "iuphar_reference",
                "meaning": "Direct-layer class from approved type/family mapping only",
            }
        ),
        "iuphar_match_status": MappingProxyType(
            {
                "layer": "iuphar_reference",
                "meaning": "Identity outcome against the snapshot catalog",
            }
        ),
        "iuphar_annotation_status": MappingProxyType(
            {
                "layer": "iuphar_reference",
                "meaning": "Availability/completeness of the direct class annotation",
            }
        ),
        "local_class": MappingProxyType(
            {
                "layer": "local_rules",
                "meaning": "Class proposed by versioned local rules (EC/annotation/prediction)",
            }
        ),
        "local_status": MappingProxyType(
            {
                "layer": "local_rules",
                "meaning": "Support level of the local layer for the row",
            }
        ),
        "effective_class": MappingProxyType(
            {
                "layer": "effective",
                "meaning": "Final class after the resolution table; may be null",
            }
        ),
        "effective_source": MappingProxyType(
            {
                "layer": "effective",
                "meaning": (
                    "Provenance of effective_class; live tokens are "
                    "iuphar_normalized, local_rule, or none "
                    "(resolution maps takes=iuphar → iuphar_normalized)"
                ),
            }
        ),
        "decision_status": MappingProxyType(
            {
                "layer": "effective",
                "meaning": "Resolution completeness and review requirement",
            }
        ),
        "target_class_profile_sha256": MappingProxyType(
            {
                "layer": "effective",
                "meaning": "SHA-256 of the pinned classification profile envelope",
            }
        ),
        "legacy_iuphar_class": MappingProxyType(
            {
                "layer": "legacy_comparison",
                "meaning": "Historical M/Excel class retained for comparison only; not a live write path",
            }
        ),
    }
)

MATCH_STATUSES: Mapping[str, str] = MappingProxyType(
    {
        "matched": "Exactly one catalog identity agreed across exact channels",
        "ambiguous": "Multiple compatible catalog candidates remain",
        "identity_conflict": "Exact channels disagree on identity",
        "insufficient_input": "Searchable identity input is missing or species-gapped",
        "source_unavailable": "Required snapshot sources are incomplete; absence is not confirmed",
        "not_found": "Snapshot is complete and searchable channels yield no catalog hit",
        "contract_error": "Internal identity/status inconsistency; processing must not invent a class",
    }
)

ANNOTATION_STATUSES: Mapping[str, str] = MappingProxyType(
    {
        "available": "Approved type mapping supplies a direct class",
        "partial": "Only family_only / family mapping supplies a coarse class",
        "unmapped_type": "Provider type/family present but outside approved mappings",
        "conflicting": "Family mappings disagree on class",
        "not_available": "Matched identity without usable direct annotation",
    }
)

LOCAL_STATUSES: Mapping[str, str] = MappingProxyType(
    {
        "supported": "At least one explicit local rule supports a class",
        "not_supported": "No local support; local_class stays empty",
        "candidate_only": "Hints exist but cannot write a supported local class",
        "conflicting": "Supported local rules disagree",
    }
)

DECISION_STATUSES: Mapping[str, str] = MappingProxyType(
    {
        "resolved": "Resolution table selected an outcome without mandatory review",
        "requires_review": "Outcome needs human/process review or has conflict codes",
        "unresolved": "No effective class; incomplete rather than conflicting",
    }
)

COMPLETENESS_STATUSES: Mapping[str, str] = MappingProxyType(
    {
        "family_only": "Snapshot/export can supply family paths but not a direct target type",
        "admission_complete": "Declared independently reviewed scope is complete for admission",
        "complete": "Global identity/absence coverage of the declared snapshot scope",
        "incomplete": "Required snapshot sources or scope receipts are missing",
    }
)

UNCERTAINTY_TOKENS: Mapping[str, str] = MappingProxyType(
    {
        "unknown": "Value not computed or not applicable for the row state",
        "partial": "Coarse or incomplete annotation; not a full direct type proof",
        "ambiguous": "Multiple candidates remain; do not collapse silently",
        "conflict": "Disagreement between layers or channels; retain conflict codes",
        "source_unavailable": "Source/snapshot gap; distinct from confirmed not_found",
        "not_found": "Confirmed absence under a complete searchable snapshot",
    }
)

# Priority: lower number wins when selecting where full classification may run.
CAPABILITY_MATRIX: Mapping[str, Mapping[str, object]] = MappingProxyType(
    {
        "standalone_chembl_target": MappingProxyType(
            {
                "priority": 2,
                "surface": "configs/entities/chembl/target.yaml",
                "may_write_v31_columns": True,
                "full_features_available": False,
                "available_inputs": (
                    "target_id",
                    "target_type",
                    "pref_name",
                    "taxonomy_id",
                    "organism",
                    "target_ec_numbers",
                    "target_xref_uniprot_ids",
                    "component_accessions",
                    "target_protein_synonyms",
                    "target_gene_synonyms",
                ),
                "unavailable_until_joins": (
                    "uniprot_protein annotations/keywords",
                    "normalized primary UniProt accession from idmapping",
                    "chembl_target_protein_classification L1-L5 summary",
                    "full target_component protein_classifications",
                ),
                "limits": (
                    "Early standalone call cannot use post-join UniProt/protein-class "
                    "features; matched counts on partial inputs are not biological accuracy"
                ),
            }
        ),
        "enriched_composite_target": MappingProxyType(
            {
                "priority": 1,
                "surface": "configs/composites/target.yaml",
                "may_write_v31_columns": True,
                "full_features_available": True,
                "available_after_dependency_joins": (
                    "chembl_target_component",
                    "chembl_protein_class",
                    "chembl_target_protein_classification",
                    "uniprot_idmapping",
                    "uniprot_protein",
                ),
                "limits": (
                    "Full classification for RF-003+ runs after dependency joins; "
                    "seed-only projection remains V30 unless enrich is admitted"
                ),
            }
        ),
    }
)

PATH_POLICY: Mapping[str, object] = MappingProxyType(
    {
        "canonical_direction": "root_to_leaf",
        "structure": "tuple of family ids from root ancestor to leaf family",
        "legacy_text_field": "leaf_to_root",
        "legacy_text_usage": "migration/comparison only; never used to choose a class",
        "multiple_parents_allowed": True,
        "graph_defect_policy": (
            "cycle, missing parent, depth/visited limits, or truncated walk "
            "do not invent a class from a cut path"
        ),
        "table_distinct_policy": (
            "Power Query Table.Distinct / unordered collapse is not an identity "
            "decision; ambiguous multi-parent or multi-candidate rows stay ambiguous"
        ),
    }
)

MISSING_MARKER_POLICY: Mapping[str, object] = MappingProxyType(
    {
        "base_markers": BASE_MISSING_MARKERS,
        "treat_null_as_missing": True,
        "treat_whitespace_only_as_missing": True,
        "version": NORMALIZATION_VERSION_APPROVED,
        "version_status": "не утверждено",
        "change_rule": (
            "A new missing_markers version is a new normalization_version; "
            "historical results keep their recorded provenance and are not rewritten"
        ),
    }
)

LEGACY_OTHER_POLICY: Mapping[str, object] = MappingProxyType(
    {
        "working_class_name": "Other Protein Target",
        "allowed_when": (
            "approved direct mapping type other_protein",
            "approved family mapping whose class is Other Protein Target",
            "explicit local rule with marks_direct_layer=false supporting that class",
            "legacy_iuphar_class comparison field carrying a historical M/Excel value",
        ),
        "forbidden_when": (
            "unmapped_type or name/path text containing 'Other'",
            "L1/L2 or free-text prediction alone without an explicit local rule",
            "filling iuphar_class from local_* output",
            "defaulting unknown/partial/ambiguous rows to Other",
        ),
    }
)

PROFILE_CHANGE_RULES: Mapping[str, str] = MappingProxyType(
    {
        "rules_version": (
            "New or edited local/direct rules publish a new rules_version; "
            f"current baseline is {RULES_VERSION}"
        ),
        "normalization_version": (
            "Missing-marker or identifier normalization changes publish a new "
            "normalization_version; current approved value is unset"
        ),
        "classification_schema_version": (
            f"Profile envelope field for enabled modes (shadow and enrich): "
            f"{CLASSIFICATION_SCHEMA_V31}. Distinct from the table/business "
            f"contract; the adapter rejects a profile that is not "
            f"{CLASSIFICATION_SCHEMA_V31}"
        ),
        "table_contract": (
            f"Business-row / Gold hash scope: off and shadow keep "
            f"{TABLE_CONTRACT_V30} (TargetClassificationConfig.contract_version "
            f"{CLASSIFICATION_SCHEMA_V30}); enrich alone advances to "
            f"{TABLE_CONTRACT_V31} / {CLASSIFICATION_SCHEMA_V31} and the nine "
            "additive columns"
        ),
        "profile_envelope": (
            "snapshot_manifest points at the profile envelope; digest is SHA-256 of "
            "exact profile bytes; acceptance and biological_accuracy_accepted stay "
            "false unless independently proven"
        ),
        "immutability": (
            "Originals, historical results, and stage-0 copies are preserved; "
            "recomputes are separate runs with new digests"
        ),
    }
)

AUDIT_COUNTEREXAMPLES: Mapping[str, str] = MappingProxyType(
    {
        "local_into_iuphar": "local_* must not be written into iuphar_* fields",
        "lost_parents": "multi-parent family paths must retain every intact root_to_leaf path",
        "false_other": "unmapped/unknown must not become Other Protein Target",
        "table_distinct": "Table.Distinct-style collapse must not pick an arbitrary class",
        "matched_counts": "matched counts are not biological_accuracy_accepted",
    }
)


def semantics_document() -> dict[str, object]:
    """Serializable RF-001 contract for manifests, docs, and policy embedding."""
    return {
        "artifact": "iuphar_rf001_semantics",
        "biological_accuracy_accepted": False,
        "contract_version": RF001_CONTRACT_VERSION,
        "epic": RF001_EPIC,
        "issue": RF001_ISSUE,
        "field_layers": {key: dict(value) for key, value in FIELD_LAYERS.items()},
        "statuses": {
            "match": dict(MATCH_STATUSES),
            "annotation": dict(ANNOTATION_STATUSES),
            "local": dict(LOCAL_STATUSES),
            "decision": dict(DECISION_STATUSES),
            "completeness": dict(COMPLETENESS_STATUSES),
            "uncertainty": dict(UNCERTAINTY_TOKENS),
        },
        "capability_matrix": {
            key: dict(value) for key, value in CAPABILITY_MATRIX.items()
        },
        "path_policy": dict(PATH_POLICY),
        "missing_marker_policy": dict(MISSING_MARKER_POLICY),
        "legacy_other_policy": dict(LEGACY_OTHER_POLICY),
        "profile_change_rules": dict(PROFILE_CHANGE_RULES),
        "audit_counterexamples": dict(AUDIT_COUNTEREXAMPLES),
        "working_classes": list(WORKING_CLASSES),
        "source_unavailable_vs_not_found": {
            "source_unavailable": MATCH_STATUSES["source_unavailable"],
            "not_found": MATCH_STATUSES["not_found"],
            "must_remain_distinct": True,
        },
    }


__all__ = [
    "ANNOTATION_STATUSES",
    "AUDIT_COUNTEREXAMPLES",
    "CAPABILITY_MATRIX",
    "CLASSIFICATION_SCHEMA_V30",
    "CLASSIFICATION_SCHEMA_V31",
    "COMPLETENESS_STATUSES",
    "DECISION_STATUSES",
    "FIELD_LAYERS",
    "LEGACY_OTHER_POLICY",
    "LOCAL_STATUSES",
    "MATCH_STATUSES",
    "MISSING_MARKER_POLICY",
    "NORMALIZATION_VERSION_APPROVED",
    "PATH_POLICY",
    "PROFILE_CHANGE_RULES",
    "RF001_CONTRACT_VERSION",
    "RF001_EPIC",
    "RF001_ISSUE",
    "RULES_VERSION",
    "TABLE_CONTRACT_V30",
    "TABLE_CONTRACT_V31",
    "UNCERTAINTY_TOKENS",
    "semantics_document",
]
