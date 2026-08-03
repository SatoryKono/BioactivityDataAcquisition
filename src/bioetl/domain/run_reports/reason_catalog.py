"""Stable reason catalog for run-report removals."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

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
    "DEDUP_KEY_COLLISION": {
        "family": "dedup",
        "default_outcome": "deduplicated",
        "layer": "silver",
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
    entries: dict[str, ReasonCatalogEntry]
    unknown_code: str = UNKNOWN_REASON

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


def normalize_reason_code(
    code: str | None, catalog: ReasonCatalog | None = None
) -> str:
    """Normalize a free reason string to a catalog code."""
    active = _active_catalog(catalog)
    stripped = "" if code is None else str(code).strip()
    if not stripped:
        return active.unknown_code
    valid_codes = active.entries.keys() | _BUILTIN_REASONS.keys()
    return stripped if stripped in valid_codes else active.unknown_code


def _active_catalog(catalog: ReasonCatalog | None) -> ReasonCatalog:
    return default_reason_catalog() if catalog is None else catalog


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


def catalog_from_mapping(
    raw: Mapping[str, object],
) -> ReasonCatalog:
    """Build a catalog from an already-parsed mapping (no I/O)."""
    version = _text_default(raw.get("version"), REASON_CATALOG_VERSION)
    unknown = _text_default(raw.get("unknown_code"), UNKNOWN_REASON)
    entries = _parse_catalog_entries(raw.get("reasons"))
    entries.setdefault(unknown, _unknown_entry(unknown))
    return ReasonCatalog(version=version, entries=entries, unknown_code=unknown)


def _parse_catalog_entries(raw_reasons: object) -> dict[str, ReasonCatalogEntry]:
    reasons = raw_reasons if isinstance(raw_reasons, list) else []
    mappings = filter(lambda item: isinstance(item, dict), reasons)
    entries = map(_entry_from_object, mappings)
    return {entry.code: entry for entry in entries if entry.code}


def _entry_from_object(item: object) -> ReasonCatalogEntry:
    assert isinstance(item, dict)
    return _entry_from_mapping(item)


def _entry_from_mapping(
    item: Mapping[str, object],
) -> ReasonCatalogEntry:
    code = _text_default(item.get("code"), "").strip()
    return ReasonCatalogEntry(
        code=code,
        family=_text_default(item.get("family"), "system"),
        default_outcome=_text_default(item.get("default_outcome"), "other"),
        layer=_text_default(item.get("layer"), "silver"),
        description=_text_default(item.get("description"), ""),
    )


def _text_default(value: object, default: str) -> str:
    return default if value in (None, "") else str(value)


def _unknown_entry(code: str) -> ReasonCatalogEntry:
    return ReasonCatalogEntry(
        code=code,
        family="system",
        default_outcome="other",
        layer="silver",
    )


@lru_cache(maxsize=1)
def default_reason_catalog() -> ReasonCatalog:
    """Return the pure built-in catalog (no filesystem I/O).

    Shipped YAML catalogs are loaded by infrastructure
    (``bioetl.infrastructure.config.reason_catalog_loader``).
    """
    return _builtin_catalog()


def catalog_as_mapping(
    catalog: ReasonCatalog | None = None,
) -> dict[str, Any]:  # Any: report/json payload shape is dynamic
    """Return a JSON-serializable catalog projection."""
    active = catalog or default_reason_catalog()
    return {
        "version": active.version,
        "unknown_code": active.unknown_code,
        "reasons": [
            {
                "code": entry.code,
                "family": entry.family,
                "default_outcome": entry.default_outcome,
                "layer": entry.layer,
                "description": entry.description,
            }
            for entry in sorted(active.entries.values(), key=lambda item: item.code)
        ],
    }
