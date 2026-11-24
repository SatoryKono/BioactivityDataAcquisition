"""Explicit V31 and V32 normalization bindings without changing the legacy registry."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.domain.config.target_classification import (
    TARGET_CLASSIFICATION_DETAIL_FIELDS,
    TARGET_CLASSIFICATION_FIELDS,
)
from bioetl.domain.normalization.profiles.base import FieldRule, NormalizationProfile
from bioetl.domain.normalization.profiles.chembl_target import CHEMBL_TARGET_PROFILE
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_passthrough,
)
from bioetl.domain.normalization.target_classification_values import (
    canonical_persisted_text,
)
from bioetl.domain.schemas.chembl.target import TargetSchemaV31, TargetSchemaV32

__all__ = ["target_v31_normalization_profile", "target_v32_normalization_profile"]


def _detail_normalizer(field_name: str) -> Callable[[object], object]:
    def normalize(value: object) -> object:
        return canonical_persisted_text(field_name, value)

    normalize.__name__ = f"normalize_{field_name}"
    normalize.__qualname__ = f"normalize_{field_name}"
    normalize.__module__ = __name__
    return normalize


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
    profile = NormalizationProfile(
        profile_name=CHEMBL_TARGET_PROFILE.profile_name,
        field_rules=rules,
        profile_version=CHEMBL_TARGET_PROFILE.profile_version,
        meta_fields=CHEMBL_TARGET_PROFILE.meta_fields,
        field_aliases=CHEMBL_TARGET_PROFILE.field_aliases,
        description=CHEMBL_TARGET_PROFILE.description,
    )
    profile.assert_covers_schema(tuple(TargetSchemaV31.to_schema().columns))
    return profile


def target_v32_normalization_profile() -> NormalizationProfile:
    """Canonicalize detail columns and keep the nine V31 fields verbatim."""
    profile = target_v31_normalization_profile()
    rules = dict(profile.field_rules)
    rules.update(
        {
            name: FieldRule(
                field_name=name,
                normalizer=_detail_normalizer(name),
                include_in_hash=True,
                notes=(
                    "Canonical JSON or scalar. Null means not computed; "
                    "an empty array means computed and empty."
                ),
            )
            for name in TARGET_CLASSIFICATION_DETAIL_FIELDS
        }
    )
    detailed = NormalizationProfile(
        profile_name=profile.profile_name,
        field_rules=rules,
        profile_version=profile.profile_version,
        meta_fields=profile.meta_fields,
        field_aliases=profile.field_aliases,
        description=profile.description,
    )
    detailed.assert_covers_schema(tuple(TargetSchemaV32.to_schema().columns))
    return detailed
