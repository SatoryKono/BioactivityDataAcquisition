"""Private unit and QUDT normalization helpers for ChEMBL fields."""

from __future__ import annotations

from urllib.parse import urlparse

from bioetl.domain.normalization.text import normalize_string

QUDT_ONTOLOGY_VERSION = "3.2.1"
QUDT_UNIT_IRI_TEMPLATE = "https://qudt.org/vocab/unit/{identifier}"
_QUDT_UNIT_IDENTIFIER_BY_UNIT: dict[str, str] = {
    "nM": "NanoMOL-PER-L",
    "µM": "MicroMOL-PER-L",
    "mM": "MilliMOL-PER-L",
    "pM": "PicoMOL-PER-L",
    "fM": "FemtoMOL-PER-L",
    "M": "MOL-PER-L",
    "%": "PERCENT",
    "ug.mL-1": "MicroGM-PER-MilliL",
    "mg.kg-1": "MilliGM-PER-KiloGM",
}
_UNIT_ALIASES: dict[str, str] = {
    "um": "µM",
    "μm": "µM",
    "µm": "µM",
    "micromolar": "µM",
    "nm": "nM",
    "nanomolar": "nM",
    "pm": "pM",
    "picomolar": "pM",
    "fm": "fM",
    "femtomolar": "fM",
    "mm": "mM",
    "millimolar": "mM",
    "m": "M",
    "molar": "M",
}
CHEMBL_STANDARD_UNIT_CANONICALS: frozenset[str] = frozenset(
    _QUDT_UNIT_IDENTIFIER_BY_UNIT.keys()
)


def _normalize_unit_alias_key(value: str) -> str:
    """Normalize unicode-variant unit tokens before alias lookup."""
    return value.replace("μ", "µ").lower()


def normalize_standard_unit(value: str | None) -> str | None:
    """Normalize standard unit names using shared activity-unit aliases."""
    normalized = normalize_string(value)
    if normalized is None:
        return None
    canonical = _UNIT_ALIASES.get(_normalize_unit_alias_key(normalized))
    return canonical if canonical is not None else normalized.replace("μ", "µ")


def normalize_qudt_unit(value: str | None) -> str | None:
    """Normalize QUDT values by trimming only."""
    return normalize_string(value)


def resolve_qudt_unit_identifier(value: str) -> str | None:
    """Resolve a canonical QUDT unit identifier from token or URI."""
    identifier = _qudt_identifier_from_uri(value)
    if identifier is not None:
        return identifier

    normalized_unit = normalize_standard_unit(value)
    if normalized_unit is not None:
        mapped_identifier = _QUDT_UNIT_IDENTIFIER_BY_UNIT.get(normalized_unit)
        if mapped_identifier is not None:
            return mapped_identifier

    return _legacy_qudt_identifier_from_uri(value)


def _qudt_identifier_from_uri(value: str) -> str | None:
    parsed = urlparse(value.strip())
    hostname = parsed.hostname.casefold() if parsed.hostname is not None else None
    if hostname == "qudt.org" and parsed.path.startswith("/vocab/unit/"):
        return parsed.path.rsplit("/", maxsplit=1)[-1]
    return None


def _legacy_qudt_identifier_from_uri(value: str) -> str | None:
    parsed = urlparse(value.strip())
    hostname = parsed.hostname.casefold() if parsed.hostname is not None else None
    if hostname != "www.openphacts.org":
        return None
    if parsed.path.casefold() == "/units/nanomolar":
        return "NanoMOL-PER-L"
    return None
