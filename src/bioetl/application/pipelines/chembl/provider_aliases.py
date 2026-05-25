"""Provider-native ChEMBL field alias normalization."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.types import BronzeRecord

__all__ = ["normalize_provider_aliases"]


def normalize_provider_aliases(
    record: BronzeRecord,
    aliases: Mapping[str, str],
) -> BronzeRecord:
    """Copy provider-native fields to canonical internal fields when needed."""
    updates = {
        canonical: record[provider_native]
        for canonical, provider_native in aliases.items()
        if canonical not in record and record.get(provider_native) is not None
    }
    if not updates:
        return record
    normalized = dict(record)
    normalized.update(updates)
    return normalized
