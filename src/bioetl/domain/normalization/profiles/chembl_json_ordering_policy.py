"""Reviewed ChEMBL JSON ordering semantics for content hashes."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

__all__ = [
    "CHEMBL_JSON_ORDERING_POLICY",
    "ChemblJsonOrderingPolicy",
    "chembl_json_fields",
    "chembl_set_like_json_fields",
]


@dataclass(frozen=True, slots=True)
class ChemblJsonOrderingPolicy:
    """Content-hash ordering decision for one ChEMBL JSON-bearing field."""

    pipeline_name: str
    field_name: str
    order_semantics: str
    rationale: str

    @property
    def is_set_like(self) -> bool:
        """Return whether JSON array item order is irrelevant for hashing."""
        return self.order_semantics == "set_like"


CHEMBL_JSON_ORDERING_POLICY: tuple[ChemblJsonOrderingPolicy, ...] = (
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_activity",
        field_name="activity_properties",
        order_semantics="set_like",
        rationale="Activity property bags are provider attribute collections, not ordered sequences.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_assay",
        field_name="assay_classifications",
        order_semantics="order_sensitive",
        rationale="Classification payload order is retained until provider semantics prove it is unordered.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_assay",
        field_name="assay_parameters",
        order_semantics="order_sensitive",
        rationale="Assay parameters may represent provider sequence/context and keep source order.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_assay",
        field_name="variant_sequence_json",
        order_semantics="order_sensitive",
        rationale="Variant payload is a structured object/sequence sidecar and keeps source order.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_molecule",
        field_name="atc_classifications",
        order_semantics="order_sensitive",
        rationale="Molecule classification payloads keep provider order pending field-level evidence.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_molecule",
        field_name="cross_references",
        order_semantics="order_sensitive",
        rationale="Reference payloads keep provider order pending a reviewed identifier-set model.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_molecule",
        field_name="molecule_hierarchy",
        order_semantics="order_sensitive",
        rationale="Hierarchy payloads encode relationships where order must not be collapsed implicitly.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_molecule",
        field_name="molecule_properties",
        order_semantics="order_sensitive",
        rationale="Property payloads keep source structure without array-order reinterpretation.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_molecule",
        field_name="molecule_structures",
        order_semantics="order_sensitive",
        rationale="Structure payloads keep source structure without array-order reinterpretation.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_molecule",
        field_name="molecule_synonyms",
        order_semantics="order_sensitive",
        rationale="Synonym payload order is retained until a synonym-set model is explicitly approved.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_publication",
        field_name="affiliation_list",
        order_semantics="set_like",
        rationale="Affiliation collections are order-insensitive contributor metadata for hash identity.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_publication",
        field_name="author_orcids",
        order_semantics="set_like",
        rationale="ORCID collections are identifier sets and are order-insensitive for hash identity.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_publication",
        field_name="authors",
        order_semantics="order_sensitive",
        rationale="Author order carries publication semantics and must remain order-sensitive.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_target",
        field_name="component_relationships",
        order_semantics="set_like",
        rationale="Component relationship vocab lists are derived unordered controlled-vocabulary sets.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_target",
        field_name="component_types",
        order_semantics="set_like",
        rationale="Component type vocab lists are derived unordered controlled-vocabulary sets.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_target",
        field_name="component_accessions",
        order_semantics="order_sensitive",
        rationale="Component-derived parallel arrays must keep source alignment.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_target",
        field_name="component_descriptions",
        order_semantics="order_sensitive",
        rationale="Component-derived parallel arrays must keep source alignment.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_target",
        field_name="component_ids",
        order_semantics="order_sensitive",
        rationale="Component-derived parallel arrays must keep source alignment.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_target",
        field_name="cross_references",
        order_semantics="order_sensitive",
        rationale="Reference payloads keep provider order pending a reviewed identifier-set model.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_target",
        field_name="pipeline_stages",
        order_semantics="order_sensitive",
        rationale="Pipeline stages are ordered process metadata.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_target",
        field_name="target_component_synonyms",
        order_semantics="order_sensitive",
        rationale="Component-derived parallel arrays must keep source alignment.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_target",
        field_name="target_components",
        order_semantics="order_sensitive",
        rationale="Target component payloads keep provider component ordering/alignment.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_target_component",
        field_name="protein_classification_ids",
        order_semantics="order_sensitive",
        rationale="Classification parallel arrays must keep source alignment.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_target_component",
        field_name="protein_classifications",
        order_semantics="order_sensitive",
        rationale="Classification payload order is retained for source alignment.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_target_component",
        field_name="target_component_synonyms",
        order_semantics="order_sensitive",
        rationale="Synonym payload order is retained pending a synonym-set model.",
    ),
    ChemblJsonOrderingPolicy(
        pipeline_name="chembl_target_component",
        field_name="target_component_xrefs",
        order_semantics="order_sensitive",
        rationale="Reference payloads keep provider order pending a reviewed identifier-set model.",
    ),
)


def chembl_json_fields(pipeline_name: str) -> frozenset[str]:
    """Return reviewed JSON-bearing fields for one ChEMBL pipeline."""
    return _fields_for_policy(
        policy
        for policy in CHEMBL_JSON_ORDERING_POLICY
        if policy.pipeline_name == pipeline_name
    )


def chembl_set_like_json_fields(pipeline_name: str) -> frozenset[str]:
    """Return reviewed order-insensitive JSON fields for one ChEMBL pipeline."""
    return _fields_for_policy(
        policy
        for policy in CHEMBL_JSON_ORDERING_POLICY
        if policy.pipeline_name == pipeline_name and policy.is_set_like
    )


def _fields_for_policy(
    policies: Iterable[ChemblJsonOrderingPolicy],
) -> frozenset[str]:
    return frozenset(policy.field_name for policy in policies)
