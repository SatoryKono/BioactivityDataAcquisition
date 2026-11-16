"""Explicit V31 normalization binding without changing the legacy registry."""

from __future__ import annotations

from dataclasses import replace

from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from bioetl.domain.normalization.profiles.base import FieldRule, NormalizationProfile
from bioetl.domain.normalization.profiles.chembl_target import CHEMBL_TARGET_PROFILE
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_passthrough,
)
from bioetl.domain.schemas.chembl.target import TargetSchemaV31

__all__ = ["target_v31_normalization_profile"]


def target_v31_normalization_profile() -> NormalizationProfile:
    """Preserve classifier output and admit its nine explicit hash fields.

    The original rules remain the same objects. Only enrich callers select this
    additive profile; off/shadow continue using the canonical V30 registry.
    """
    rules = dict(CHEMBL_TARGET_PROFILE.field_rules)
    rules.update(
        {
            name: FieldRule(
                field_name=name,
                normalizer=normalize_profile_passthrough,
                include_in_hash=True,
                notes="Preserve the frozen IUPHAR classifier decision verbatim.",
            )
            for name in TARGET_CLASSIFICATION_FIELDS
        }
    )
    profile = replace(CHEMBL_TARGET_PROFILE, field_rules=rules)
    profile.assert_covers_schema(tuple(TargetSchemaV31.to_schema().columns))
    return profile
