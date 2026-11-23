"""Field roles and version pins for the audited target classification.

These pins describe the new policy. They do not rewrite an already admitted
profile's normalization version.
"""

from __future__ import annotations

import hashlib

FIELD_ROLES: dict[str, str] = {
    "iuphar_target_id": "iuphar",
    "iuphar_class": "iuphar",
    "iuphar_match_status": "iuphar",
    "iuphar_annotation_status": "iuphar",
    "iuphar_type_raw": "iuphar",
    "iuphar_annotation_capability": "iuphar",
    "iuphar_family_ids": "iuphar",
    "iuphar_subclasses": "iuphar",
    "iuphar_paths": "iuphar",
    "local_class": "local",
    "local_status": "local",
    "local_subclasses": "local",
    "local_rule_ids": "local",
    "effective_class": "effective",
    "effective_source": "effective",
    "effective_subclasses": "effective",
    "decision_status": "effective",
    "conflict_codes": "effective",
    "classification_evidence_ids": "effective",
    "target_class_profile_sha256": "profile",
    "target_type": "chembl",
}

UNCERTAINTY_STATUSES = (
    "unknown",
    "partial",
    "ambiguous",
    "conflict",
    "source_unavailable",
    "not_found",
    "insufficient_input",
    "identity_conflict",
)

CAPABILITY_MATRIX = {
    "standalone": "identifiers_only",
    "composite_post_join": "full_features",
}

PATH_DIRECTION = "root_to_leaf"
LEGACY_OTHER_POLICY = "historical_label_only"
ANNOTATION_CAPABILITY = "family_only"

VERSIONS = {
    "normalization": "bioetl-iuphar-input-v2",
    "rules": "iuphar-local-rules-20261123",
    "classifier": "iuphar-classifier-20261123",
    "table_contracts": ("3.0.0", "3.1.0", "3.2.0"),
}


def build_input_manifest(payload: bytes) -> dict[str, object]:
    """Hash supplied bytes. The original payload is not rewritten."""
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "byte_length": len(payload),
        "mutated": False,
        "normalization_version": VERSIONS["normalization"],
    }


__all__ = [
    "ANNOTATION_CAPABILITY",
    "CAPABILITY_MATRIX",
    "FIELD_ROLES",
    "LEGACY_OTHER_POLICY",
    "PATH_DIRECTION",
    "UNCERTAINTY_STATUSES",
    "VERSIONS",
    "build_input_manifest",
]
