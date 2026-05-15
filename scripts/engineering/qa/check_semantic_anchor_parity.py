#!/usr/bin/env python3
"""Validate DQ, Gold, and composite parity for semantic join anchors."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]

if __package__ in {None, ""}:
    sys.path.insert(0, str(REPO_ROOT))
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bioetl.domain.normalization.join_keys import (  # noqa: E402
    get_join_key_normalization_policy,
)


@dataclass(frozen=True, slots=True)
class CompositeRequirement:
    """One expected composite usage for a semantic anchor field."""

    composite_path: str
    kind: str
    field: str | None = None
    pipeline: str | None = None
    group: str | None = None


@dataclass(frozen=True, slots=True)
class AnchorSpec:
    """Expected DQ, Gold, and composite parity for one anchor field."""

    anchor_id: str
    field: str
    entity_config: str
    gold_contract: str
    expected_gold_required: bool
    normalization_key: str | None = None
    require_field_validation: bool = False
    require_cross_field_validation: bool = False
    require_conditional_validation: bool = False
    require_key_nullability: bool = False
    require_silver_required_filter: bool = False
    require_gold_required_filter: bool = False
    require_primary_key: bool = False
    require_merge_key: bool = False
    require_join_key_normalization_policy: bool = False
    composite_requirements: tuple[CompositeRequirement, ...] = ()


@dataclass(frozen=True, slots=True)
class AnchorParityFinding:
    """One semantic anchor parity validation finding."""

    kind: str
    anchor_id: str
    path: str
    field: str
    message: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serializable finding payload."""
        return {
            "kind": self.kind,
            "anchor_id": self.anchor_id,
            "path": self.path,
            "field": self.field,
            "message": self.message,
        }


ANCHOR_SPECS: tuple[AnchorSpec, ...] = (
    AnchorSpec(
        anchor_id="crossref_doi_publication_anchor",
        field="doi",
        entity_config="configs/entities/crossref/publication.yaml",
        gold_contract="docs/04-reference/contracts/gold/crossref_publication_v1.0.json",
        expected_gold_required=True,
        require_join_key_normalization_policy=True,
        require_field_validation=True,
        require_cross_field_validation=True,
        require_key_nullability=True,
        require_silver_required_filter=True,
        require_gold_required_filter=True,
        require_primary_key=True,
        require_merge_key=True,
        composite_requirements=(
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "publication_primary_join_key",
            ),
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "enricher_join_key",
                pipeline="crossref_publication",
            ),
        ),
    ),
    AnchorSpec(
        anchor_id="pubmed_pmid_publication_anchor",
        field="pmid",
        entity_config="configs/entities/pubmed/publication.yaml",
        gold_contract="docs/04-reference/contracts/gold/pubmed_publication_v1.0.json",
        expected_gold_required=True,
        require_join_key_normalization_policy=True,
        require_field_validation=True,
        require_cross_field_validation=True,
        require_key_nullability=True,
        require_silver_required_filter=True,
        require_gold_required_filter=True,
        require_primary_key=True,
        require_merge_key=True,
        composite_requirements=(
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "publication_primary_join_key",
            ),
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "enricher_join_key",
                pipeline="pubmed_publication",
            ),
        ),
    ),
    AnchorSpec(
        anchor_id="pubmed_title_publication_fallback_anchor",
        field="title",
        entity_config="configs/entities/pubmed/publication.yaml",
        gold_contract="docs/04-reference/contracts/gold/pubmed_publication_v1.0.json",
        expected_gold_required=True,
        require_join_key_normalization_policy=True,
        require_field_validation=True,
        require_cross_field_validation=True,
        require_silver_required_filter=True,
        require_gold_required_filter=True,
        composite_requirements=(
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "publication_fallback_join_key",
            ),
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "field_priority",
            ),
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "seed_output_key",
            ),
        ),
    ),
    AnchorSpec(
        anchor_id="crossref_title_publication_fallback_anchor",
        field="title",
        entity_config="configs/entities/crossref/publication.yaml",
        gold_contract="docs/04-reference/contracts/gold/crossref_publication_v1.0.json",
        expected_gold_required=True,
        require_join_key_normalization_policy=True,
        require_field_validation=True,
        require_cross_field_validation=True,
        require_silver_required_filter=True,
        require_gold_required_filter=True,
        composite_requirements=(
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "publication_fallback_join_key",
            ),
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "field_priority",
            ),
        ),
    ),
    AnchorSpec(
        anchor_id="openalex_title_publication_fallback_anchor",
        field="title",
        entity_config="configs/entities/openalex/publication.yaml",
        gold_contract="docs/04-reference/contracts/gold/openalex_publication_v1.0.json",
        expected_gold_required=True,
        require_join_key_normalization_policy=True,
        require_field_validation=True,
        require_cross_field_validation=True,
        require_silver_required_filter=True,
        require_gold_required_filter=True,
        composite_requirements=(
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "publication_fallback_join_key",
            ),
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "field_priority",
            ),
        ),
    ),
    AnchorSpec(
        anchor_id="semanticscholar_title_publication_fallback_anchor",
        field="title",
        entity_config="configs/entities/semanticscholar/publication.yaml",
        gold_contract=(
            "docs/04-reference/contracts/gold/semanticscholar_publication_v1.0.json"
        ),
        expected_gold_required=True,
        require_join_key_normalization_policy=True,
        require_field_validation=True,
        require_cross_field_validation=True,
        require_silver_required_filter=True,
        require_gold_required_filter=True,
        composite_requirements=(
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "publication_fallback_join_key",
            ),
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "field_priority",
            ),
        ),
    ),
    AnchorSpec(
        anchor_id="pubmed_pmc_publication_reference_anchor",
        field="pmc_id",
        entity_config="configs/entities/pubmed/publication.yaml",
        gold_contract="docs/04-reference/contracts/gold/pubmed_publication_v1.0.json",
        expected_gold_required=False,
        require_join_key_normalization_policy=True,
        require_cross_field_validation=True,
        composite_requirements=(
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "seed_output_key",
            ),
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "column_group_field",
                group="provider_ids",
            ),
        ),
    ),
    AnchorSpec(
        anchor_id="chembl_publication_identifier_anchor",
        field="publication_id",
        entity_config="configs/entities/chembl/publication.yaml",
        gold_contract="docs/04-reference/contracts/gold/chembl_publication_v1.0.json",
        expected_gold_required=True,
        require_join_key_normalization_policy=True,
        require_field_validation=True,
        require_cross_field_validation=True,
        require_key_nullability=True,
        require_silver_required_filter=True,
        require_gold_required_filter=True,
        require_primary_key=True,
        require_merge_key=True,
        composite_requirements=(
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "seed_output_key",
            ),
            CompositeRequirement(
                "configs/composites/publication.yaml",
                "column_group_field",
                group="provider_ids",
            ),
        ),
    ),
    AnchorSpec(
        anchor_id="chembl_activity_publication_lineage_anchor",
        field="publication_id",
        entity_config="configs/entities/chembl/activity.yaml",
        gold_contract="docs/04-reference/contracts/gold/chembl_activity_v1.0.json",
        expected_gold_required=False,
        require_join_key_normalization_policy=True,
        require_silver_required_filter=True,
        composite_requirements=(
            CompositeRequirement("configs/composites/activity.yaml", "seed_output_key"),
            CompositeRequirement(
                "configs/composites/activity.yaml",
                "dependency_join_key",
                pipeline="chembl_compound_record",
            ),
            CompositeRequirement("configs/composites/activity.yaml", "field_priority"),
        ),
    ),
    AnchorSpec(
        anchor_id="chembl_assay_identifier_anchor",
        field="assay_id",
        entity_config="configs/entities/chembl/assay.yaml",
        gold_contract="docs/04-reference/contracts/gold/chembl_assay_v1.0.json",
        expected_gold_required=True,
        require_field_validation=True,
        require_cross_field_validation=True,
        require_key_nullability=True,
        require_silver_required_filter=True,
        require_primary_key=True,
        require_merge_key=True,
        composite_requirements=(
            CompositeRequirement("configs/composites/assay.yaml", "seed_output_key"),
            CompositeRequirement("configs/composites/activity.yaml", "seed_output_key"),
        ),
    ),
    AnchorSpec(
        anchor_id="chembl_molecule_identifier_anchor",
        field="molecule_id",
        entity_config="configs/entities/chembl/molecule.yaml",
        gold_contract="docs/04-reference/contracts/gold/chembl_molecule_v1.0.json",
        expected_gold_required=True,
        require_join_key_normalization_policy=True,
        require_field_validation=True,
        require_key_nullability=True,
        require_silver_required_filter=True,
        require_gold_required_filter=True,
        require_primary_key=True,
        require_merge_key=True,
        composite_requirements=(
            CompositeRequirement("configs/composites/molecule.yaml", "seed_output_key"),
            CompositeRequirement("configs/composites/activity.yaml", "seed_output_key"),
        ),
    ),
    AnchorSpec(
        anchor_id="chembl_inchi_key_structure_join_anchor",
        field="inchi_key",
        entity_config="configs/entities/chembl/molecule.yaml",
        gold_contract="docs/04-reference/contracts/gold/chembl_molecule_v1.0.json",
        expected_gold_required=False,
        require_join_key_normalization_policy=True,
        require_cross_field_validation=True,
        composite_requirements=(
            CompositeRequirement("configs/composites/molecule.yaml", "seed_output_key"),
            CompositeRequirement(
                "configs/composites/molecule.yaml",
                "molecule_active_join_key",
            ),
            CompositeRequirement("configs/composites/molecule.yaml", "field_priority"),
        ),
    ),
    AnchorSpec(
        anchor_id="pubchem_inchi_key_structure_join_anchor",
        field="inchi_key",
        entity_config="configs/entities/pubchem/compound.yaml",
        gold_contract="docs/04-reference/contracts/gold/pubchem_compound_v1.0.json",
        expected_gold_required=False,
        require_join_key_normalization_policy=True,
        require_cross_field_validation=True,
        composite_requirements=(
            CompositeRequirement(
                "configs/composites/molecule.yaml",
                "molecule_active_join_key",
            ),
            CompositeRequirement(
                "configs/composites/molecule.yaml",
                "enricher_join_key",
                pipeline="pubchem_compound",
            ),
        ),
    ),
    AnchorSpec(
        anchor_id="chembl_canonical_smiles_structure_join_anchor",
        field="canonical_smiles",
        entity_config="configs/entities/chembl/molecule.yaml",
        gold_contract="docs/04-reference/contracts/gold/chembl_molecule_v1.0.json",
        expected_gold_required=False,
        require_join_key_normalization_policy=True,
        require_field_validation=True,
        require_cross_field_validation=True,
        composite_requirements=(
            CompositeRequirement("configs/composites/molecule.yaml", "seed_output_key"),
            CompositeRequirement(
                "configs/composites/molecule.yaml",
                "molecule_active_join_key",
            ),
            CompositeRequirement("configs/composites/molecule.yaml", "field_priority"),
        ),
    ),
    AnchorSpec(
        anchor_id="pubchem_canonical_smiles_structure_join_anchor",
        field="canonical_smiles",
        entity_config="configs/entities/pubchem/compound.yaml",
        gold_contract="docs/04-reference/contracts/gold/pubchem_compound_v1.0.json",
        expected_gold_required=False,
        require_join_key_normalization_policy=True,
        require_field_validation=True,
        require_cross_field_validation=True,
        composite_requirements=(
            CompositeRequirement(
                "configs/composites/molecule.yaml",
                "molecule_active_join_key",
            ),
            CompositeRequirement(
                "configs/composites/molecule.yaml",
                "enricher_join_key",
                pipeline="pubchem_compound",
            ),
        ),
    ),
    AnchorSpec(
        anchor_id="chembl_target_identifier_anchor",
        field="target_id",
        entity_config="configs/entities/chembl/target.yaml",
        gold_contract="docs/04-reference/contracts/gold/chembl_target_v1.0.json",
        expected_gold_required=True,
        require_join_key_normalization_policy=True,
        require_field_validation=True,
        require_cross_field_validation=True,
        require_key_nullability=True,
        require_silver_required_filter=True,
        require_primary_key=True,
        require_merge_key=True,
        composite_requirements=(
            CompositeRequirement("configs/composites/target.yaml", "seed_output_key"),
            CompositeRequirement("configs/composites/target.yaml", "field_priority"),
            CompositeRequirement(
                "configs/composites/target.yaml", "target_source_anchor"
            ),
        ),
    ),
    AnchorSpec(
        anchor_id="chembl_activity_target_lineage_anchor",
        field="target_id",
        entity_config="configs/entities/chembl/activity.yaml",
        gold_contract="docs/04-reference/contracts/gold/chembl_activity_v1.0.json",
        expected_gold_required=False,
        require_join_key_normalization_policy=True,
        require_conditional_validation=True,
        require_silver_required_filter=True,
        require_gold_required_filter=True,
        composite_requirements=(
            CompositeRequirement("configs/composites/activity.yaml", "seed_output_key"),
        ),
    ),
    AnchorSpec(
        anchor_id="uniprot_idmapping_target_anchor",
        field="target_id",
        entity_config="configs/entities/uniprot/idmapping.yaml",
        gold_contract="docs/04-reference/contracts/gold/uniprot_idmapping_v1.0.json",
        expected_gold_required=True,
        require_join_key_normalization_policy=True,
        require_field_validation=True,
        require_key_nullability=True,
        require_silver_required_filter=True,
        require_gold_required_filter=True,
        require_primary_key=True,
        require_merge_key=True,
        composite_requirements=(
            CompositeRequirement(
                "configs/composites/target.yaml",
                "dependency_join_key",
                pipeline="uniprot_idmapping",
            ),
            CompositeRequirement(
                "configs/composites/target.yaml", "target_source_anchor"
            ),
        ),
    ),
    AnchorSpec(
        anchor_id="uniprot_accession_chained_join_anchor",
        field="uniprot_accession",
        entity_config="configs/entities/uniprot/idmapping.yaml",
        gold_contract="docs/04-reference/contracts/gold/uniprot_idmapping_v1.0.json",
        expected_gold_required=False,
        require_join_key_normalization_policy=True,
        require_field_validation=True,
        require_conditional_validation=True,
        composite_requirements=(
            CompositeRequirement(
                "configs/composites/target.yaml",
                "dependency_join_key",
                pipeline="uniprot_protein",
            ),
            CompositeRequirement(
                "configs/composites/target.yaml",
                "target_normalized_output_anchor",
            ),
            CompositeRequirement(
                "configs/composites/target.yaml",
                "column_group_field",
                group="identifiers",
            ),
        ),
    ),
    AnchorSpec(
        anchor_id="uniprot_protein_accession_identifier_anchor",
        field="accession",
        normalization_key="uniprot_accession",
        entity_config="configs/entities/uniprot/protein.yaml",
        gold_contract="docs/04-reference/contracts/gold/uniprot_protein_v1.0.json",
        expected_gold_required=True,
        require_join_key_normalization_policy=True,
        require_field_validation=True,
        require_cross_field_validation=True,
        require_key_nullability=True,
        require_silver_required_filter=True,
        require_gold_required_filter=True,
        require_primary_key=True,
        require_merge_key=True,
        composite_requirements=(
            CompositeRequirement(
                "configs/composites/target.yaml",
                "dependency_join_key",
                field="uniprot_accession",
                pipeline="uniprot_protein",
            ),
        ),
    ),
)


def _load_mapping(path: Path) -> dict[str, Any]:
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Expected mapping payload in {path}")


def _field_set(items: object) -> set[str]:
    fields: set[str] = set()
    if not isinstance(items, list):
        return fields
    for item in items:
        if isinstance(item, str):
            fields.add(item)
        elif isinstance(item, dict) and isinstance(item.get("field"), str):
            fields.add(item["field"])
    return fields


def _quality_section(entity_config: dict[str, Any]) -> dict[str, Any]:
    quality = entity_config.get("quality", {})
    return quality if isinstance(quality, dict) else {}


def _quality_field_validations(entity_config: dict[str, Any]) -> set[str]:
    return _field_set(_quality_section(entity_config).get("entity_field_validations"))


def _quality_cross_field_validations(entity_config: dict[str, Any]) -> set[str]:
    fields: set[str] = set()
    entries = _quality_section(entity_config).get("entity_cross_field_validations")
    if not isinstance(entries, list):
        return fields
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        field_names = entry.get("fields")
        if isinstance(field_names, list):
            fields.update(field for field in field_names if isinstance(field, str))
    return fields


def _quality_conditional_validations(entity_config: dict[str, Any]) -> set[str]:
    fields: set[str] = set()
    entries = _quality_section(entity_config).get("entity_conditional_validations")
    if not isinstance(entries, list):
        return fields
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        condition_field = entry.get("condition_field")
        if isinstance(condition_field, str):
            fields.add(condition_field)
        then_validations = entry.get("then_validations")
        if isinstance(then_validations, list):
            fields.update(_field_set(then_validations))
    return fields


def _nonnull_key_fields(entity_config: dict[str, Any]) -> set[str]:
    fields: set[str] = set()
    entries = _quality_section(entity_config).get("key_nullability")
    if not isinstance(entries, list):
        return fields
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        field = entry.get("field")
        if isinstance(field, str) and entry.get("nullable") is False:
            fields.add(field)
    return fields


def _required_filter_fields(
    entity_config: dict[str, Any], filter_name: str
) -> set[str]:
    filters = entity_config.get("filters", {})
    if not isinstance(filters, dict):
        return set()
    filter_config = filters.get(filter_name, {})
    if not isinstance(filter_config, dict):
        return set()
    return _field_set(filter_config.get("required_fields"))


def _contract_fields(entity_config: dict[str, Any], key: str) -> set[str]:
    contracts = entity_config.get("contracts", {})
    if not isinstance(contracts, dict):
        return set()
    return _field_set(contracts.get(key))


def _gold_field_required(gold_contract: dict[str, Any], field: str) -> bool | None:
    properties = gold_contract.get("properties")
    if not isinstance(properties, dict) or field not in properties:
        return None
    required = gold_contract.get("required", [])
    return isinstance(required, list) and field in required


def _gold_field_nullable(gold_contract: dict[str, Any], field: str) -> bool | None:
    properties = gold_contract.get("properties")
    if not isinstance(properties, dict):
        return None
    field_schema = properties.get(field)
    if not isinstance(field_schema, dict):
        return None
    nullable = field_schema.get("nullable")
    if isinstance(nullable, bool):
        return nullable
    field_type = field_schema.get("type")
    return isinstance(field_type, list) and "null" in field_type


def _composite_root(payload: dict[str, Any]) -> dict[str, Any]:
    composite = payload.get("composite", {})
    return composite if isinstance(composite, dict) else {}


def _find_pipeline_entry(
    entries: object,
    *,
    pipeline: str | None,
) -> dict[str, Any] | None:
    if not isinstance(entries, list) or pipeline is None:
        return None
    for entry in entries:
        if isinstance(entry, dict) and entry.get("pipeline") == pipeline:
            return entry
    return None


def _has_composite_requirement(
    composite_payload: dict[str, Any],
    requirement: CompositeRequirement,
    *,
    field: str,
) -> bool:
    composite = _composite_root(composite_payload)
    check_field = requirement.field or field

    if requirement.kind == "seed_output_key":
        seed = composite.get("seed", {})
        return isinstance(seed, dict) and check_field in _field_set(
            seed.get("output_keys")
        )

    if requirement.kind == "field_priority":
        merge = composite.get("merge", {})
        priorities = (
            merge.get("field_priorities", {}) if isinstance(merge, dict) else {}
        )
        return isinstance(priorities, dict) and check_field in priorities

    if requirement.kind == "column_group_field":
        merge = composite.get("merge", {})
        column_groups = (
            merge.get("column_groups", {}) if isinstance(merge, dict) else {}
        )
        if not isinstance(column_groups, list):
            return False
        for group in column_groups:
            if not isinstance(group, dict):
                continue
            if requirement.group is not None and group.get("name") != requirement.group:
                continue
            if check_field in _field_set(group.get("fields")):
                return True
        return False

    if requirement.kind == "enricher_join_key":
        entry = _find_pipeline_entry(
            composite.get("enrichers"),
            pipeline=requirement.pipeline,
        )
        return entry is not None and check_field in _field_set(entry.get("join_keys"))

    if requirement.kind == "dependency_join_key":
        entry = _find_pipeline_entry(
            composite.get("dependencies"),
            pipeline=requirement.pipeline,
        )
        return entry is not None and check_field in _field_set(entry.get("join_keys"))

    if requirement.kind == "publication_primary_join_key":
        policy = composite.get("normalized_join_key_policy", {})
        identity = (
            policy.get("publication_identity", {}) if isinstance(policy, dict) else {}
        )
        return isinstance(identity, dict) and check_field in _field_set(
            identity.get("primary_join_keys")
        )

    if requirement.kind == "publication_fallback_join_key":
        policy = composite.get("normalized_join_key_policy", {})
        identity = (
            policy.get("publication_identity", {}) if isinstance(policy, dict) else {}
        )
        return isinstance(identity, dict) and check_field in _field_set(
            identity.get("fallback_join_keys")
        )

    if requirement.kind == "molecule_active_join_key":
        policy = composite.get("normalized_anchor_policy", {})
        pubchem = policy.get("pubchem_compound", {}) if isinstance(policy, dict) else {}
        boundary = pubchem.get("join_boundary", {}) if isinstance(pubchem, dict) else {}
        return isinstance(boundary, dict) and check_field in _field_set(
            boundary.get("active_join_keys")
        )

    if requirement.kind == "target_source_anchor":
        policy = composite.get("normalized_anchor_policy", {})
        idmapping = (
            policy.get("uniprot_idmapping", {}) if isinstance(policy, dict) else {}
        )
        boundary = (
            idmapping.get("join_boundary", {}) if isinstance(idmapping, dict) else {}
        )
        return (
            isinstance(boundary, dict) and boundary.get("source_anchor") == check_field
        )

    if requirement.kind == "target_normalized_output_anchor":
        policy = composite.get("normalized_anchor_policy", {})
        idmapping = (
            policy.get("uniprot_idmapping", {}) if isinstance(policy, dict) else {}
        )
        boundary = (
            idmapping.get("join_boundary", {}) if isinstance(idmapping, dict) else {}
        )
        return (
            isinstance(boundary, dict)
            and boundary.get("normalized_output_anchor") == check_field
        )

    raise ValueError(f"Unsupported composite requirement kind: {requirement.kind}")


def _finding(
    *,
    spec: AnchorSpec,
    kind: str,
    path: str,
    message: str,
) -> AnchorParityFinding:
    return AnchorParityFinding(
        kind=kind,
        anchor_id=spec.anchor_id,
        path=path,
        field=spec.field,
        message=message,
    )


def _validate_entity_surface(
    spec: AnchorSpec,
    *,
    entity_config: dict[str, Any],
) -> list[AnchorParityFinding]:
    findings: list[AnchorParityFinding] = []
    field = spec.field
    path = spec.entity_config

    entity_requirements = (
        (
            spec.require_field_validation,
            "missing_field_validation",
            _quality_field_validations(entity_config),
            "DQ entity_field_validations",
        ),
        (
            spec.require_cross_field_validation,
            "missing_cross_field_validation",
            _quality_cross_field_validations(entity_config),
            "DQ entity_cross_field_validations",
        ),
        (
            spec.require_conditional_validation,
            "missing_conditional_validation",
            _quality_conditional_validations(entity_config),
            "DQ entity_conditional_validations",
        ),
        (
            spec.require_key_nullability,
            "missing_key_nullability",
            _nonnull_key_fields(entity_config),
            "DQ non-null key_nullability",
        ),
        (
            spec.require_silver_required_filter,
            "missing_silver_required_filter",
            _required_filter_fields(entity_config, "silver_filters"),
            "silver required_fields",
        ),
        (
            spec.require_gold_required_filter,
            "missing_gold_required_filter",
            _required_filter_fields(entity_config, "gold_filters"),
            "gold required_fields",
        ),
        (
            spec.require_primary_key,
            "missing_contract_primary_key",
            _contract_fields(entity_config, "primary_key"),
            "contract primary_key",
        ),
        (
            spec.require_merge_key,
            "missing_contract_merge_key",
            _contract_fields(entity_config, "merge_keys"),
            "contract merge_keys",
        ),
    )

    for required, kind, actual_fields, surface in entity_requirements:
        if not required or field in actual_fields:
            continue
        findings.append(
            _finding(
                spec=spec,
                kind=kind,
                path=path,
                message=f"{spec.anchor_id} expects {field!r} in {surface}",
            )
        )

    return findings


def _validate_normalization_surface(spec: AnchorSpec) -> list[AnchorParityFinding]:
    if not spec.require_join_key_normalization_policy:
        return []

    normalization_key = spec.normalization_key or spec.field
    if get_join_key_normalization_policy(normalization_key) is not None:
        return []

    return [
        _finding(
            spec=spec,
            kind="missing_join_key_normalization_policy",
            path="src/bioetl/domain/normalization/join_keys.py",
            message=(
                f"{spec.anchor_id} expects explicit join-key normalization policy "
                f"for {normalization_key!r}"
            ),
        )
    ]


def _validate_gold_surface(
    spec: AnchorSpec,
    *,
    gold_contract: dict[str, Any],
) -> list[AnchorParityFinding]:
    findings: list[AnchorParityFinding] = []
    required = _gold_field_required(gold_contract, spec.field)
    nullable = _gold_field_nullable(gold_contract, spec.field)

    if required is None:
        findings.append(
            _finding(
                spec=spec,
                kind="missing_gold_field",
                path=spec.gold_contract,
                message=f"{spec.gold_contract} does not define {spec.field!r}",
            )
        )
        return findings

    if required != spec.expected_gold_required:
        findings.append(
            _finding(
                spec=spec,
                kind="gold_requiredness_mismatch",
                path=spec.gold_contract,
                message=(
                    f"{spec.anchor_id} expects Gold required="
                    f"{spec.expected_gold_required} for {spec.field!r}, got {required}"
                ),
            )
        )

    expected_nullable = not spec.expected_gold_required
    if nullable is not None and nullable != expected_nullable:
        findings.append(
            _finding(
                spec=spec,
                kind="gold_nullability_mismatch",
                path=spec.gold_contract,
                message=(
                    f"{spec.anchor_id} expects Gold nullable={expected_nullable} "
                    f"for {spec.field!r}, got {nullable}"
                ),
            )
        )

    return findings


def _validate_composite_surface(
    spec: AnchorSpec,
    *,
    repo_root: Path,
) -> list[AnchorParityFinding]:
    findings: list[AnchorParityFinding] = []
    cache: dict[str, dict[str, Any]] = {}

    for requirement in spec.composite_requirements:
        if requirement.composite_path not in cache:
            cache[requirement.composite_path] = _load_mapping(
                repo_root / requirement.composite_path
            )
        if _has_composite_requirement(
            cache[requirement.composite_path],
            requirement,
            field=spec.field,
        ):
            continue
        qualifier = (
            f" for pipeline {requirement.pipeline!r}"
            if requirement.pipeline is not None
            else ""
        )
        findings.append(
            _finding(
                spec=spec,
                kind="missing_composite_anchor",
                path=requirement.composite_path,
                message=(
                    f"{spec.anchor_id} expects {spec.field!r} in composite "
                    f"{requirement.kind}{qualifier}"
                ),
            )
        )

    return findings


def validate_anchor_parity(
    repo_root: Path = REPO_ROOT,
    specs: tuple[AnchorSpec, ...] = ANCHOR_SPECS,
) -> tuple[AnchorParityFinding, ...]:
    """Return semantic anchor parity findings for the current repository."""
    findings: list[AnchorParityFinding] = []

    for spec in specs:
        entity_config = _load_mapping(repo_root / spec.entity_config)
        gold_contract = _load_mapping(repo_root / spec.gold_contract)
        findings.extend(_validate_entity_surface(spec, entity_config=entity_config))
        findings.extend(_validate_normalization_surface(spec))
        findings.extend(_validate_gold_surface(spec, gold_contract=gold_contract))
        findings.extend(_validate_composite_surface(spec, repo_root=repo_root))

    return tuple(findings)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate DQ, Gold, and composite parity for semantic anchors.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail with a non-zero exit code when findings are present",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable validation output",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="repository root containing configs, docs, and scripts",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    findings = validate_anchor_parity(args.repo_root)
    if args.json:
        payload = {
            "ok": not findings,
            "finding_count": len(findings),
            "findings": [finding.as_dict() for finding in findings],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif findings:
        print("[semantic-anchor-parity] validation failed")
        for finding in findings:
            print(f"- {finding.message} ({finding.path})")
    else:
        print("[semantic-anchor-parity] ok")

    return 1 if args.check and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
