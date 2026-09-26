# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Governance checks for expanded UniProt semantic payload registry."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.structured_payload_policies import (
    structured_payload_policy,
)

pytestmark = pytest.mark.unit

_REGISTRY = {
    "structured_payload_fields": [
        "features_json",
        "alternative_products",
        "biophysicochemical_properties",
        "cofactors",
        "reactions",
    ],
    "comment_projection_fields": [
        "activity_regulation",
        "alternative_products",
        "biophysicochemical_properties",
        "catalytic_activity",
        "caution",
        "cofactors",
        "disease_involvement",
        "function_comment",
        "induction",
        "pathway",
        "pharmaceutical_use",
        "similarity_comment",
        "subcellular_location",
        "subunit",
        "tissue_specificity",
    ],
    "feature_projection_fields": [
        "active_sites",
        "binding_sites",
        "domains",
        "topology",
        "transmembrane",
        "intramembrane",
        "signal_peptide",
        "propeptide",
        "glycosylation",
        "lipidation",
        "disulfide_bond",
        "modified_residue",
        "phosphorylation",
        "acetylation",
        "ubiquitination",
    ],
    "reference_payload_fields": [
        "cellular_component",
        "go_terms",
        "interpro_xrefs",
        "molecular_function",
        "pdb_xrefs",
        "pfam_xrefs",
        "reactome_xrefs",
    ],
    "feature_types": ["Active site", "Binding site", "Domain", "Modified residue"],
    "comment_types": [
        "ALTERNATIVE PRODUCTS",
        "CATALYTIC ACTIVITY",
        "CAUTION",
        "COFACTOR",
        "DISEASE",
        "FUNCTION",
        "INDUCTION",
        "PATHWAY",
        "SIMILARITY",
        "SUBCELLULAR LOCATION",
        "SUBUNIT",
        "TISSUE SPECIFICITY",
    ],
    "keyword_categories": [
        "Biological process",
        "Cellular component",
        "Coding sequence diversity",
        "Disease",
        "Domain",
        "Ligand",
        "Molecular function",
        "PTM",
        "Technical term",
    ],
}
_BUSINESS_FIELDS = {
    "features_json",
    "alternative_products",
    "biophysicochemical_properties",
    "cofactors",
    "reactions",
    "activity_regulation",
    "catalytic_activity",
    "caution",
    "disease_involvement",
    "function_comment",
    "induction",
    "pathway",
    "pharmaceutical_use",
    "similarity_comment",
    "subcellular_location",
    "subunit",
    "tissue_specificity",
    "active_sites",
    "binding_sites",
    "domains",
    "topology",
    "transmembrane",
    "intramembrane",
    "signal_peptide",
    "propeptide",
    "glycosylation",
    "lipidation",
    "disulfide_bond",
    "modified_residue",
    "phosphorylation",
    "acetylation",
    "ubiquitination",
    "cellular_component",
    "go_terms",
    "interpro_xrefs",
    "molecular_function",
    "pdb_xrefs",
    "pfam_xrefs",
    "reactome_xrefs",
}
_OBSERVED_PAYLOADS = [
    {
        "features": [{"type": "Active site"}, {"type": "Domain"}],
        "comments": [
            {"commentType": "FUNCTION"},
            {"commentType": "SUBCELLULAR LOCATION"},
        ],
        "keywords": [
            {"category": "Biological process"},
            {"category": "Technical term"},
        ],
    },
    {
        "features": [{"type": "Modified residue"}],
        "comments": [{"commentType": "COFACTOR"}],
        "keywords": [{"category": "PTM"}],
    },
]


def _extract_uniprot_semantic_payload_vocab(
    payloads: list[dict[str, object]],
) -> dict[str, list[str]]:
    observed = {
        "feature_types": set(),
        "comment_types": set(),
        "keyword_categories": set(),
    }
    for payload in payloads:
        for feature in payload.get("features", []):
            if isinstance(feature, dict) and feature.get("type") is not None:
                observed["feature_types"].add(str(feature["type"]))
        for comment in payload.get("comments", []):
            if isinstance(comment, dict) and comment.get("commentType") is not None:
                observed["comment_types"].add(str(comment["commentType"]))
        for keyword in payload.get("keywords", []):
            if isinstance(keyword, dict) and keyword.get("category") is not None:
                observed["keyword_categories"].add(str(keyword["category"]))
    return {key: sorted(values) for key, values in observed.items() if values}


def test_uniprot_semantic_payload_registry_covers_observed_fixture_vocab() -> None:
    payload = _extract_uniprot_semantic_payload_vocab(_OBSERVED_PAYLOADS)

    assert set(payload["feature_types"]) <= set(_REGISTRY["feature_types"])
    assert set(payload["comment_types"]) <= set(_REGISTRY["comment_types"])
    assert set(payload["keyword_categories"]) <= set(_REGISTRY["keyword_categories"])


def test_uniprot_semantic_payload_registry_declares_profile_backed_field_groups() -> (
    None
):
    for key in (
        "structured_payload_fields",
        "comment_projection_fields",
        "feature_projection_fields",
        "reference_payload_fields",
    ):
        assert set(_REGISTRY[key]) <= _BUSINESS_FIELDS


def test_uniprot_features_policy_points_to_expanded_semantic_registry() -> None:
    policy = structured_payload_policy("uniprot.protein", "features_json")

    assert policy is not None
    assert policy.controlled_vocabulary_source == (
        "configs/vocab/uniprot_semantic_payloads.yaml"
    )
