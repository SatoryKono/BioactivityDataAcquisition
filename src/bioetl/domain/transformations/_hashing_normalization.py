"""Shim for the canonical hash-identity normalization seam."""

from __future__ import annotations

from bioetl.domain.normalization.hash_identity import normalize_hash_identity_value


def _normalize_value_for_hash(
    value: object,
    *,
    sort_nested_sequences: bool,
) -> object:
    """Delegate to the canonical domain hash-identity normalization seam."""
    return normalize_hash_identity_value(
        value,
        sort_nested_sequences=sort_nested_sequences,
    )
