"""Lifecycle metadata for deprecated ENTITY_MAPPING compatibility alias.

Inventoried in configs/quality/chembl_entity_mapping_compatibility.yaml
and ratcheted by tests/architecture/test_chembl_entity_mapping_lifecycle.py (#7495).
"""

from __future__ import annotations

__all__ = ["ENTITY_MAPPING_LIFECYCLE"]

# Deprecated public alias retained for external compatibility only.
# First-party code MUST use ChemblEntityMapper / resolve_resource_name instead.
ENTITY_MAPPING_LIFECYCLE: dict[str, object] = {
    "symbol": "ENTITY_MAPPING",
    "module": "bioetl.infrastructure.adapters.chembl.entity_mapper",
    "status": "retained_external_compatibility",
    "owner": "bioetl.infrastructure.adapters.chembl",
    "consumer_class": "external_unspecified",
    "canonical_target": (
        "bioetl.infrastructure.adapters.chembl.entity_mapper.ChemblEntityMapper "
        "/ bioetl.infrastructure.adapters.chembl._entity_mapping_lookup."
        "build_legacy_entity_mapping / resolve_resource_name"
    ),
    "sunset_status": "retained_until_external_migration_evidence",
    "review_date": "2026-09-30",
    "external_breaking_change_required": True,
    "internal_callers_zero": True,
    "max_src_importer_count": 0,
    "migration_path": (
        "Replace ENTITY_MAPPING[entity] lookups with "
        "ChemblEntityMapper.get_resource_url(entity) or resolve_resource_name(entity)."
    ),
    "exit_criteria": (
        "Remove the alias only after importer census shows zero external consumers "
        "or a coordinated major-version breaking-change notice is published."
    ),
    "linked_issue": 7495,
}
