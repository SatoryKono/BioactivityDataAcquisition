"""Canonical hashing helpers for effective-config source references."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import PurePath
from typing import Literal

import yaml

ConfigSourceHashStrategy = Literal["canonical_yaml", "raw_bytes"]

_YAML_SUFFIXES = frozenset({".yaml", ".yml"})


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """PyYAML safe loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: yaml.SafeLoader,
    node: yaml.Node,
    deep: bool = False,
) -> object:
    if not isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node, deep=deep)

    seen: set[object] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            already_seen = key in seen
        except TypeError as exc:
            raise ValueError(f"YAML mapping key must be hashable: {key!r}") from exc
        if already_seen:
            raise ValueError(f"Duplicate YAML mapping key: {key!r}")
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True)
class ConfigSourceHashes:
    """Semantic and raw hashes for one file-backed config source."""

    semantic_hash: str
    raw_hash: str
    hash_strategy: ConfigSourceHashStrategy


def compute_raw_sha256(raw_bytes: bytes) -> str:
    """Compute the forensic raw byte SHA-256 digest."""
    return hashlib.sha256(raw_bytes).hexdigest()


def compute_canonical_yaml_sha256(raw_bytes: bytes) -> str:
    """Compute a SHA-256 digest from YAML semantics, ignoring formatting."""
    text = raw_bytes.decode("utf-8")
    payload = yaml.load(text, Loader=_UniqueKeySafeLoader)
    canonical_payload = _to_canonical_jsonable(payload)
    serialized = json.dumps(
        canonical_payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_config_source_hashes(
    *,
    source_path: str,
    raw_bytes: bytes,
) -> ConfigSourceHashes:
    """Compute semantic identity and raw integrity hashes for a config source."""
    raw_hash = compute_raw_sha256(raw_bytes)
    if PurePath(source_path).suffix.lower() in _YAML_SUFFIXES:
        return ConfigSourceHashes(
            semantic_hash=compute_canonical_yaml_sha256(raw_bytes),
            raw_hash=raw_hash,
            hash_strategy="canonical_yaml",
        )
    return ConfigSourceHashes(
        semantic_hash=raw_hash,
        raw_hash=raw_hash,
        hash_strategy="raw_bytes",
    )


def _to_canonical_jsonable(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if key in normalized:
                raise ValueError(
                    f"Canonical YAML key collision after string coercion: {key!r}"
                )
            normalized[key] = _to_canonical_jsonable(raw_value)
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, (list, tuple)):
        return [_to_canonical_jsonable(item) for item in value]
    return value
