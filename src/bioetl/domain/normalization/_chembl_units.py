"""Private unit and QUDT normalization helpers for ChEMBL fields."""

from __future__ import annotations

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
    "percent": "%",
    "percentage": "%",
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


def _uri_host_and_path(value: str) -> tuple[str, str] | None:
    """Extract a simple HTTP(S) host and path without an application-layer import."""
    candidate = value.strip()
    scheme, separator, remainder = candidate.partition("://")
    if not separator or scheme.casefold() not in {"http", "https"}:
        return None
    # Strip query/fragment before authority/path split so `/` inside query
    # cannot be treated as a path (e.g. `?ref=/vocab/unit/...`).
    remainder = remainder.split("?", maxsplit=1)[0].split("#", maxsplit=1)[0]
    authority, slash, suffix = remainder.partition("/")
    authority = authority.rsplit("@", maxsplit=1)[-1].casefold()
    host = authority.split(":", maxsplit=1)[0]
    path = f"/{suffix}" if slash else ""
    path_prefix, path_separator, last_segment = path.rpartition("/")
    path = (
        f"{path_prefix}/{last_segment.partition(';')[0]}"
        if path_separator
        else path.partition(";")[0]
    )
    return host, path


def _identifier_from_parsed_uri(hostname: str, path: str) -> str | None:
    """Map a parsed HTTP host/path pair to a QUDT unit identifier."""
    if hostname == "qudt.org" and path.startswith("/vocab/unit/"):
        return path.rsplit("/", maxsplit=1)[-1]
    if hostname == "www.openphacts.org" and path.casefold() == "/units/nanomolar":
        return "NanoMOL-PER-L"
    return None


def _identifier_from_unit_token(value: str) -> str | None:
    """Map a normalized activity-unit token to a QUDT unit identifier."""
    normalized_unit = normalize_standard_unit(value)
    if normalized_unit is None:
        return None
    return _QUDT_UNIT_IDENTIFIER_BY_UNIT.get(normalized_unit)


def resolve_qudt_unit_identifier(value: str) -> str | None:
    """Resolve a canonical QUDT unit identifier from token or URI."""
    parsed = _uri_host_and_path(value)
    if parsed is not None:
        from_uri = _identifier_from_parsed_uri(*parsed)
        if from_uri is not None:
            return from_uri
    return _identifier_from_unit_token(value)
