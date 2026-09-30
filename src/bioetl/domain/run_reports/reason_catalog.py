"""Stable reason catalog for run-report removals."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from bioetl.domain.run_reports.reason_catalog_data import (
    REASON_CATALOG_VERSION,
    UNKNOWN_REASON,
    ReasonCatalog,
    ReasonCatalogEntry,
    default_reason_catalog,
)

_FIELD_REASON_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _valid_field_suffix(field: str | None, stripped_base: str) -> str:
    """Return the field suffix when it may decorate the base code."""
    if field is None or ":" in stripped_base:
        return ""
    stripped_field = str(field).strip()
    if not stripped_field or _FIELD_REASON_TOKEN.fullmatch(stripped_field) is None:
        return ""
    return stripped_field


def compose_field_reason_code(base: str, field: str | None) -> str:
    """Attach a field suffix when the token is a valid catalog field identifier.

    Catalog entries keep the bare base code; reports may show ``BASE:field``
    (for example ``INVALID_DATA:units``) without expanding the YAML catalog.
    Invalid or empty field tokens leave ``base`` unchanged.
    """
    stripped_base = str(base).strip()
    if not stripped_base:
        return UNKNOWN_REASON
    suffix = _valid_field_suffix(field, stripped_base)
    if not suffix:
        return stripped_base
    return f"{stripped_base}:{suffix}"


def _strip_reason_code(code: str | None) -> str:
    """Strip a free reason string, tolerating a missing code."""
    if code is None:
        return ""
    return str(code).strip()


def _match_compound_code(stripped: str, active: ReasonCatalog) -> str | None:
    """Match a ``BASE:field`` code against catalog entries."""
    base, separator, field = stripped.partition(":")
    if (
        separator
        and base in active.entries
        and _FIELD_REASON_TOKEN.fullmatch(field) is not None
    ):
        return stripped
    return None


def normalize_reason_code(
    code: str | None, catalog: ReasonCatalog | None = None
) -> str:
    """Normalize a free reason string to a catalog code."""
    active = _active_catalog(catalog)
    stripped = _strip_reason_code(code)
    if not stripped:
        return active.unknown_code
    if stripped in active.entries:
        return stripped
    matched = _match_compound_code(stripped, active)
    if matched is None:
        return active.unknown_code
    return matched


def _active_catalog(catalog: ReasonCatalog | None) -> ReasonCatalog:
    return default_reason_catalog() if catalog is None else catalog


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
