"""Pure domain transformations (no I/O, deterministic, side-effect free).

Implements RULES.md §2.8 — Entity ID Generation and Content Hashing.
REQ-ARCH-003, REQ-ID-001..008, REQ-SCHEMA-001..004.

Sub-modules:
    hashing  — Content hash generation and entity ID derivation.
    drift    — Schema drift detection.
    quality  — Data quality scoring and threshold checks.
    coercion — Safe type coercion utilities (safe_float, safe_int, safe_str).
"""

from __future__ import annotations

from bioetl.domain.constants import META_FIELDS

from .coercion import safe_float, safe_int, safe_str
from .drift import detect_schema_drift
from .hashing import (
    canonical_json_dumps,
    generate_content_hash,
    generate_entity_id,
    normalize_for_hash,
)
from .quality import calculate_dq_score, detect_hash_collision, exceeds_threshold

__all__ = [
    "META_FIELDS",
    "calculate_dq_score",
    "canonical_json_dumps",
    "detect_hash_collision",
    "detect_schema_drift",
    "exceeds_threshold",
    "generate_content_hash",
    "generate_entity_id",
    "normalize_for_hash",
    "safe_float",
    "safe_int",
    "safe_str",
]
