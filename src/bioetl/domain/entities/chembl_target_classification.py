"""Additive target entities for the opt-in IUPHAR 3.1.0 and 3.2.0 contracts."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.chembl_structures_foundation import Target


@dataclass(frozen=True, kw_only=True)
class TargetV31(Target):
    """Keep the legacy Target entity unchanged for off and shadow profiles."""

    iuphar_target_id: str | None = None
    iuphar_class: str | None = None
    iuphar_match_status: str | None = None
    iuphar_annotation_status: str | None = None
    local_class: str | None = None
    effective_class: str | None = None
    effective_source: str | None = None
    decision_status: str | None = None
    target_class_profile_sha256: str | None = None


@dataclass(frozen=True, kw_only=True)
class TargetV32(TargetV31):
    """Persist classifier detail without changing the nine V31 columns."""

    iuphar_type_raw: str | None = None
    iuphar_source_completeness: str | None = None
    iuphar_family_ids: str | None = None
    iuphar_subclasses: str | None = None
    iuphar_family_paths: str | None = None
    local_status: str | None = None
    local_subclasses: str | None = None
    local_rule_ids: str | None = None
    effective_subclasses: str | None = None
    conflict_codes: str | None = None
    classification_evidence_refs: str | None = None


__all__ = ["TargetV31", "TargetV32"]
