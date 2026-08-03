"""Infrastructure loader for publication controlled-vocabulary registries."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml

from bioetl.domain.mapping.publication_controlled_vocabulary import (
    PublicationControlledVocabularyRegistry,
)
from bioetl.domain.normalization.text import normalize_string
from bioetl.domain.ports import PublicationVocabularyPort
from bioetl.domain.types import JsonDict

__all__ = ["PublicationControlledVocabularyLoader"]


class PublicationControlledVocabularyLoader(PublicationVocabularyPort):
    """Load provider-facing publication vocabulary from the config tree."""

    def __init__(self, configs_root: Path) -> None:
        self._path = configs_root / "vocab" / "publication_controlled.yaml"

    def load(self) -> PublicationControlledVocabularyRegistry:
        """Return the normalized provider/field registry from YAML."""
        payload = self._load_payload()
        providers = payload.get("providers")
        if not isinstance(providers, dict):
            return PublicationControlledVocabularyRegistry(allowed_values_by_field={})

        registry: dict[tuple[str, str], frozenset[str]] = {}
        for provider_name, field_name, field_payload in self._iter_fields(providers):
            if not self._preserve_unknown(field_payload):
                continue
            registry[(provider_name.lower(), field_name)] = frozenset(
                self._field_values(payload, field_payload)
            )
        return PublicationControlledVocabularyRegistry(allowed_values_by_field=registry)

    def _load_payload(self) -> JsonDict:
        try:
            payload = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            return {}
        return cast(JsonDict, payload) if isinstance(payload, dict) else {}

    @staticmethod
    def _iter_fields(
        providers: dict[object, object],
    ) -> tuple[tuple[str, str, JsonDict], ...]:
        fields: list[tuple[str, str, JsonDict]] = []
        for provider_name, provider_payload in providers.items():
            if not isinstance(provider_name, str) or not isinstance(
                provider_payload, dict
            ):
                continue
            for field_name, field_payload in provider_payload.items():
                if not isinstance(field_name, str) or not isinstance(
                    field_payload, dict
                ):
                    continue
                fields.append(
                    (provider_name, field_name, cast(JsonDict, field_payload))
                )
        return tuple(fields)

    @staticmethod
    def _preserve_unknown(field_payload: JsonDict) -> bool:
        preserve_unknown = field_payload.get("preserve_unknown")
        return preserve_unknown is None or bool(preserve_unknown)

    def _field_values(
        self,
        root_payload: JsonDict,
        field_payload: JsonDict,
    ) -> set[str]:
        values = {
            cleaned
            for value in field_payload.get("values", [])
            if isinstance(value, str)
            for cleaned in [self._normalize_token(value)]
            if cleaned is not None
        }
        inherits = field_payload.get("inherits")
        if isinstance(inherits, str):
            values.update(self._resolve_inherited_values(root_payload, inherits))
        return values

    def _resolve_inherited_values(
        self,
        root_payload: JsonDict,
        dotted_path: str,
    ) -> set[str]:
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
            for cleaned in [self._normalize_token(value)]
            if cleaned is not None
        }

    @staticmethod
    def _normalize_token(value: str) -> str | None:
        return normalize_string(value)
