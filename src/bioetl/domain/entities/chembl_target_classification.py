"""Additive target entity for the opt-in IUPHAR 3.1.0 contract."""

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


__all__ = ["TargetV31"]
