"""Infrastructure loader for the run-report reason catalog YAML asset."""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

import yaml

from bioetl.domain.run_reports.reason_catalog import (
    REASON_CATALOG_VERSION,
    UNKNOWN_REASON,
    ReasonCatalog,
    ReasonCatalogEntry,
    default_reason_catalog,
)
from bioetl.infrastructure.config.config_root import get_default_repo_root

_DEFAULT_CATALOG_RELATIVE = Path("configs/contracts/reports/reason_catalog.v1.yaml")

__all__ = [
    "DEFAULT_REASON_CATALOG_RELATIVE",
    "load_default_reason_catalog",
    "load_reason_catalog_from_path",
    "load_reason_catalog_from_text",
]

DEFAULT_REASON_CATALOG_RELATIVE = _DEFAULT_CATALOG_RELATIVE


def _text_default(value: object, default: str) -> str:
    return default if value in (None, "") else str(value)


def _entry_from_mapping(item: Mapping[str, object]) -> ReasonCatalogEntry:
    code = _text_default(item.get("code"), "").strip()
    return ReasonCatalogEntry(
        code=code,
        family=_text_default(item.get("family"), "system"),
        default_outcome=_text_default(item.get("default_outcome"), "other"),
        layer=_text_default(item.get("layer"), "silver"),
        description=_text_default(item.get("description"), ""),
    )


def _catalog_from_mapping(raw: Mapping[str, object]) -> ReasonCatalog:
    version = _text_default(raw.get("version"), REASON_CATALOG_VERSION)
    unknown = _text_default(raw.get("unknown_code"), UNKNOWN_REASON)
    raw_reasons = raw.get("reasons")
    reasons = raw_reasons if isinstance(raw_reasons, list) else []
    entries: dict[str, ReasonCatalogEntry] = {}
    for item in reasons:
        if not isinstance(item, dict):
            continue
        entry = _entry_from_mapping(item)
        if entry.code:
            entries[entry.code] = entry
    entries.setdefault(
        unknown,
        ReasonCatalogEntry(
            code=unknown,
            family="system",
            default_outcome="other",
            layer="silver",
        ),
    )
    return ReasonCatalog(version=version, entries=entries, unknown_code=unknown)


def load_reason_catalog_from_text(text: str) -> ReasonCatalog | None:
    """Parse catalog YAML text into a Domain ``ReasonCatalog``."""
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    if not isinstance(raw, dict):
        return None
    return _catalog_from_mapping(raw)


def load_reason_catalog_from_path(path: Path) -> ReasonCatalog | None:
    """Load catalog YAML from an explicit filesystem path."""
    if not path.is_file():
        return None
    return load_reason_catalog_from_text(path.read_text(encoding="utf-8"))


def _catalog_candidates() -> list[Path]:
    return [
        Path.cwd() / _DEFAULT_CATALOG_RELATIVE,
        get_default_repo_root() / _DEFAULT_CATALOG_RELATIVE,
    ]


@lru_cache(maxsize=1)
def load_default_reason_catalog() -> ReasonCatalog:
    """Load the shipped reason catalog YAML, else fall back to Domain default."""
    for candidate in _catalog_candidates():
        loaded = load_reason_catalog_from_path(candidate)
        if loaded is not None:
            return loaded
    return default_reason_catalog()
