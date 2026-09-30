"""Built-in reason catalog data and catalog construction."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from types import MappingProxyType

REASON_CATALOG_VERSION = "reason_catalog_v1"
UNKNOWN_REASON = "UNKNOWN_REASON"

# Built-in fallback when YAML is unavailable (tests / offline).
_BUILTIN_REASONS: dict[str, dict[str, str]] = {
    "FILTERED_OUT_SILVER": {
        "family": "structural",
        "default_outcome": "filtered_out",
        "layer": "silver",
    },
    "structural_policy_required_missing": {
        "family": "structural",
        "default_outcome": "filtered_out",
        "layer": "silver",
    },
    "structural_policy_null_optional_forbidden": {
        "family": "structural",
        "default_outcome": "filtered_out",
        "layer": "silver",
    },
    "structural_policy_type_mismatch": {
        "family": "structural",
        "default_outcome": "filtered_out",
        "layer": "silver",
    },
    "missing_publication_primary_id": {
        "family": "structural",
        "default_outcome": "filtered_out",
        "layer": "silver",
    },
    "missing_compound_identifier": {
        "family": "structural",
        "default_outcome": "filtered_out",
        "layer": "silver",
    },
    "SCHEMA_VALIDATION_FAILURE": {
        "family": "dq",
        "default_outcome": "quarantined",
        "layer": "silver",
    },
    "DQ_THRESHOLD_VIOLATION": {
        "family": "dq",
        "default_outcome": "quarantined",
        "layer": "silver",
    },
    "SCHEMA_VIOLATION": {
        "family": "dq",
        "default_outcome": "quarantined",
        "layer": "silver",
    },
    "INVALID_DATA": {
        "family": "dq",
        "default_outcome": "quarantined",
        "layer": "silver",
    },
    "MISSING_REQUIRED_FIELD": {
        "family": "dq",
        "default_outcome": "quarantined",
        "layer": "silver",
    },
    "DATA_QUALITY": {
        "family": "dq",
        "default_outcome": "quarantined",
        "layer": "silver",
    },
    "SCHEMA_REQUIRED_FIELD_MISSING": {
        "family": "dq",
        "default_outcome": "quarantined",
        "layer": "silver",
    },
    "SCHEMA_TYPE_MISMATCH": {
        "family": "dq",
        "default_outcome": "quarantined",
        "layer": "silver",
    },
    "DQ_SOFT_RULE_FAILED": {
        "family": "dq",
        "default_outcome": "filtered_out",
        "layer": "silver",
    },
    "DQ_HARD_RULE_FAILED": {
        "family": "dq",
        "default_outcome": "quarantined",
        "layer": "silver",
    },
    "QUARANTINE_POLICY": {
        "family": "dq",
        "default_outcome": "quarantined",
        "layer": "silver",
    },
    "DUPLICATE_PRIMARY_KEY": {
        "family": "dedup",
        "default_outcome": "deduplicated",
        "layer": "silver",
    },
    "OPERATOR_SKIPPED": {
        "family": "operator",
        "default_outcome": "skipped",
        "layer": "silver",
    },
    "SCHEMA_MISMATCH_GOLD": {
        "family": "contract",
        "default_outcome": "quarantined",
        "layer": "gold",
    },
    "CROSS_VALIDATION_NULLIFIED": {
        "family": "dq",
        "default_outcome": "quarantined",
        "layer": "silver",
    },
    "DEDUP_KEY_COLLISION": {
        "family": "dedup",
        "default_outcome": "deduplicated",
        "layer": "silver",
    },
    "gold_filter_exclusion": {
        "family": "semantic",
        "default_outcome": "excluded_by_contract",
        "layer": "gold",
    },
    "required_field_missing": {
        "family": "semantic",
        "default_outcome": "excluded_by_contract",
        "layer": "gold",
    },
    "exclude_if_present": {
        "family": "semantic",
        "default_outcome": "excluded_by_contract",
        "layer": "gold",
    },
    "column_filter_mismatch": {
        "family": "semantic",
        "default_outcome": "excluded_by_contract",
        "layer": "gold",
    },
    "range_filter_mismatch": {
        "family": "semantic",
        "default_outcome": "excluded_by_contract",
        "layer": "gold",
    },
    "list_length_filter_mismatch": {
        "family": "semantic",
        "default_outcome": "excluded_by_contract",
        "layer": "gold",
    },
    "list_contains_filter_mismatch": {
        "family": "semantic",
        "default_outcome": "excluded_by_contract",
        "layer": "gold",
    },
    "gold_contract_schema_failure": {
        "family": "contract",
        "default_outcome": "excluded_by_contract",
        "layer": "gold",
    },
    "gold_contract_required_failure": {
        "family": "contract",
        "default_outcome": "excluded_by_contract",
        "layer": "gold",
    },
    "gold_contract_reference_failure": {
        "family": "contract",
        "default_outcome": "excluded_by_contract",
        "layer": "gold",
    },
    "gold_semantic_business_exclusion": {
        "family": "semantic",
        "default_outcome": "quarantined",
        "layer": "gold",
    },
    "gold_semantic_profile_exclusion": {
        "family": "semantic",
        "default_outcome": "quarantined",
        "layer": "gold",
    },
    UNKNOWN_REASON: {
        "family": "system",
        "default_outcome": "other",
        "layer": "silver",
    },
}

__all__ = [
    "REASON_CATALOG_VERSION",
    "UNKNOWN_REASON",
    "ReasonCatalog",
    "ReasonCatalogEntry",
    "default_reason_catalog",
]


@dataclass(frozen=True, slots=True)
class ReasonCatalogEntry:
    """One catalog entry."""

    code: str
    family: str
    default_outcome: str
    layer: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class ReasonCatalog:
    """Immutable reason catalog projection."""

    version: str
    entries: Mapping[str, ReasonCatalogEntry]
    unknown_code: str = UNKNOWN_REASON

    def __post_init__(self) -> None:
        object.__setattr__(self, "entries", MappingProxyType(dict(self.entries)))

    def resolve(self, code: str | None) -> ReasonCatalogEntry:
        """Return catalog entry or UNKNOWN_REASON."""
        if code and code in self.entries:
            return self.entries[code]
        unknown = self.entries.get(self.unknown_code)
        if unknown is not None:
            return unknown
        return ReasonCatalogEntry(
            code=self.unknown_code,
            family="system",
            default_outcome="other",
            layer="silver",
        )

    def family_for(self, code: str | None) -> str:
        return self.resolve(code).family

    def default_outcome_for(self, code: str | None) -> str:
        return self.resolve(code).default_outcome


def _builtin_catalog() -> ReasonCatalog:
    entries = {
        code: ReasonCatalogEntry(
            code=code,
            family=meta["family"],
            default_outcome=meta["default_outcome"],
            layer=meta["layer"],
        )
        for code, meta in _BUILTIN_REASONS.items()
    }
    return ReasonCatalog(version=REASON_CATALOG_VERSION, entries=entries)


@lru_cache(maxsize=1)
def default_reason_catalog() -> ReasonCatalog:
    """Return the pure built-in catalog (no filesystem I/O).

    Shipped YAML catalogs are loaded by infrastructure
    (``bioetl.infrastructure.config.reason_catalog_loader``).
    """
    return _builtin_catalog()
