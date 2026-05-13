"""Bounded publication-vocabulary drift observability helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import cast

import yaml

from bioetl.domain.normalization.json import deserialize_json_value
from bioetl.domain.normalization.text import normalize_string
from bioetl.domain.types import JsonDict

PUBLICATION_RAW_VOCAB_UNKNOWN_TOTAL = "bioetl_publication_raw_vocab_unknown_total"
_REPO_ROOT = Path(__file__).resolve().parents[5]
_CONTROLLED_VOCAB_PATH = (
    _REPO_ROOT / "configs" / "vocab" / "publication_controlled.yaml"
)
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


def _build_vocab_registry_entry(
    payload: JsonDict,
    provider_name: str,
    field_name: str,
    field_payload: JsonDict,
) -> tuple[tuple[str, str], frozenset[str]] | None:
    """Build a single vocab registry entry if preserve_unknown is enabled."""
    if not _preserve_unknown(field_payload):
        return None
    values = _field_values(payload, field_payload)
    return ((provider_name, field_name), frozenset(values))


@lru_cache(maxsize=1)
def _publication_vocab_registry() -> dict[tuple[str, str], frozenset[str]]:
    payload = _load_publication_vocab_payload()
    providers = payload.get("providers")
    if not isinstance(providers, dict):
        return {}

    registry: dict[tuple[str, str], frozenset[str]] = {}
    for provider_name, field_name, field_payload in _iter_publication_vocab_fields(
        providers
    ):
        entry = _build_vocab_registry_entry(
            cast(JsonDict, payload), provider_name, field_name, field_payload
        )
        if entry:
            registry[entry[0]] = entry[1]
    return registry


def _load_publication_vocab_payload() -> JsonDict:
    try:
        payload = yaml.safe_load(_CONTROLLED_VOCAB_PATH.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return cast(JsonDict, payload) if isinstance(payload, dict) else {}


def _iter_publication_vocab_fields(
    providers: dict[object, object],
) -> tuple[tuple[str, str, JsonDict], ...]:
    fields: list[tuple[str, str, JsonDict]] = []
    for provider_name, provider_payload in providers.items():
        if not isinstance(provider_name, str) or not isinstance(provider_payload, dict):
            continue
        for field_name, field_payload in provider_payload.items():
            if not isinstance(field_name, str) or not isinstance(field_payload, dict):
                continue
            fields.append((provider_name, field_name, cast(JsonDict, field_payload)))
    return tuple(fields)


def _preserve_unknown(field_payload: JsonDict) -> bool:
    preserve_unknown = field_payload.get("preserve_unknown")
    return preserve_unknown is None or bool(preserve_unknown)


def _field_values(root_payload: JsonDict, field_payload: JsonDict) -> set[str]:
    values = {
        cleaned
        for value in field_payload.get("values", [])
        if isinstance(value, str)
        for cleaned in [_normalize_token(value)]
        if cleaned is not None
    }
    inherits = field_payload.get("inherits")
    if isinstance(inherits, str):
        values.update(_resolve_inherited_values(root_payload, inherits))
    return values


def _resolve_inherited_values(root_payload: JsonDict, dotted_path: str) -> set[str]:
    node: object = root_payload
    for segment in dotted_path.split("."):
        if not isinstance(node, dict):
            return set()
        node = node.get(segment)
    if not isinstance(node, dict):
        return set()
    return {
        cleaned
        for value in node.get("values", [])
        if isinstance(value, str)
        for cleaned in [_normalize_token(value)]
        if cleaned is not None
    }


def _allowed_publication_vocab(provider: str, field_name: str) -> frozenset[str]:
    return _publication_vocab_registry().get((provider, field_name), frozenset())
