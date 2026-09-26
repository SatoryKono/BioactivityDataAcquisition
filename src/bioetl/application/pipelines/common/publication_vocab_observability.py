"""Bounded publication-vocabulary drift observability helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from bioetl.domain.mapping.publication_controlled_vocabulary import (
    publication_controlled_vocabulary_values,
)
from bioetl.domain.normalization.json import deserialize_json_value
from bioetl.domain.normalization.text import normalize_string

PUBLICATION_RAW_VOCAB_UNKNOWN_TOTAL = "bioetl_publication_raw_vocab_unknown_total"
_UNKNOWN_HANDLING = "preserved_unknown"
_PROVIDER_FIELD_SPECS: dict[str, tuple[str, ...]] = {
    "crossref": ("publication_type",),
    "openalex": ("publication_type", "type_crossref"),
    "pubmed": ("publication_types", "publication_status"),
    "semanticscholar": ("publication_types",),
}


def emit_unknown_publication_vocab_metrics(
    *,
    metrics: object,
    pipeline_name: str,
    provider: str,
    normalized_business_data: Mapping[str, object],
) -> None:
    """Emit bounded counters for unknown raw publication vocabulary drift."""
    increment_counter = getattr(metrics, "increment_counter", None)
    if not callable(increment_counter):
        return

    for field_name in _PROVIDER_FIELD_SPECS.get(provider, ()):
        allowed_values = _allowed_publication_vocab(provider, field_name)
        if not allowed_values:
            continue
        for token in _field_tokens(normalized_business_data.get(field_name)):
            if token in allowed_values:
                continue
            increment_counter(
                name=PUBLICATION_RAW_VOCAB_UNKNOWN_TOTAL,
                value=1,
                labels={
                    "pipeline": pipeline_name,
                    "provider": provider,
                    "field": field_name,
                    "handling": _UNKNOWN_HANDLING,
                },
            )


def _field_tokens(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return _tokens_from_string_value(value)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return _normalized_string_tokens(value)
    return ()


def _normalized_string_tokens(values: Sequence[object]) -> tuple[str, ...]:
    return tuple(
        cleaned
        for item in values
        if isinstance(item, str)
        for cleaned in [_normalize_token(item)]
        if cleaned is not None
    )


def _tokens_from_string_value(value: str) -> tuple[str, ...]:
    cleaned = normalize_string(value)
    if cleaned is None:
        return ()
    parsed = _parse_json_sequence(cleaned)
    if parsed is None:
        return (cleaned,)
    return _normalized_string_tokens(parsed)


def _parse_json_sequence(value: str) -> list[object] | None:
    try:
        parsed = deserialize_json_value(value)
    except ValueError:
        return None
    return parsed if isinstance(parsed, list) else None


def _normalize_token(value: str) -> str | None:
    return normalize_string(value)


def _allowed_publication_vocab(provider: str, field_name: str) -> frozenset[str]:
    return publication_controlled_vocabulary_values(provider, field_name)
