# Host attrs/methods provided by concrete composition.
"""Schema loading and extraction helpers for preflight validation."""

from __future__ import annotations

from importlib import import_module
from typing import Any, cast

from bioetl.application.composite._preflight_schema_field_extraction import (
    extract_fields_from_schema,
)
from bioetl.application.composite._preflight_types import (
    ProfileInfo,
    SchemaFields,
)
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.normalization.profiles import resolve_normalization_profile
from bioetl.domain.ports import LoggerPort


def _find_schema_class(module: object) -> type | None:
    """Return the first exported generated schema class from a module."""
    for exported in getattr(module, "__all__", ()):
        candidate = (
            getattr(module, exported, None) if isinstance(exported, str) else exported
        )
        if isinstance(candidate, type) and hasattr(candidate, "to_schema"):
            return candidate

    for candidate in vars(module).values():
        if isinstance(candidate, type) and hasattr(candidate, "to_schema"):
            return candidate
    return None


class PreflightSchemaOrchestrationMixin:
    """Schema discovery and dtype extraction helper methods."""

    _SCHEMA_REGISTRY: dict[str, type] | None = None
    _logger: LoggerPort = cast(Any, None)  # Any: host default (PD4)

    def _parse_pipeline_identity(self, pipeline_name: str) -> tuple[str, str] | None:
        """Return ``(provider, entity)`` for ``provider_entity`` pipelines."""
        if "_" not in pipeline_name:
            return None
        provider, entity = pipeline_name.split("_", 1)
        provider = provider.strip().lower()
        entity = entity.strip().lower()
        if not provider or not entity:
            return None
        return provider, entity

    def _register_source_aliases[AliasValueT](
        self,
        result: dict[str, AliasValueT],
        *,
        pipeline_name: str,
        fields: AliasValueT,
        is_seed: bool = False,
    ) -> None:
        """Register canonical and compatibility source aliases for a schema payload."""
        identity = self._parse_pipeline_identity(pipeline_name)
        if identity is None:
            return
        provider, entity = identity
        pipeline_key = f"{provider}_{entity}"
        provider_entity_key = f"{provider}.{entity}"

        if is_seed:
            result["seed"] = fields
            result[provider] = fields
        else:
            result.setdefault(provider, fields)

        result[pipeline_key] = fields
        result[provider_entity_key] = fields

    def _load_source_fields(self, config: CompositeConfig) -> dict[str, SchemaFields]:
        """Load field definitions from source schemas."""
        result: dict[str, SchemaFields] = {}

        seed_pipeline = config.seed.pipeline
        seed_fields = self._load_pipeline_schema_fields(seed_pipeline)
        if seed_fields:
            self._register_source_aliases(
                result,
                pipeline_name=seed_pipeline,
                fields=seed_fields,
                is_seed=True,
            )

        for dependency in config.dependencies:
            dependency_fields = self._load_pipeline_schema_fields(dependency.pipeline)
            if dependency_fields:
                self._register_source_aliases(
                    result,
                    pipeline_name=dependency.pipeline,
                    fields=dependency_fields,
                )

        for enricher in config.enrichers:
            enricher_fields = self._load_pipeline_schema_fields(enricher.pipeline)
            if enricher_fields:
                self._register_source_aliases(
                    result,
                    pipeline_name=enricher.pipeline,
                    fields=enricher_fields,
                )

        return result

    def _load_source_profiles(self, config: CompositeConfig) -> dict[str, ProfileInfo]:
        """Load deterministic normalization-profile identities for source pipelines."""
        result: dict[str, ProfileInfo] = {}

        seed_pipeline = config.seed.pipeline
        seed_profile = self._load_pipeline_profile(seed_pipeline)
        if seed_profile is not None:
            self._register_source_aliases(
                result,
                pipeline_name=seed_pipeline,
                fields=seed_profile,
                is_seed=True,
            )

        for dependency in config.dependencies:
            dependency_profile = self._load_pipeline_profile(dependency.pipeline)
            if dependency_profile is not None:
                self._register_source_aliases(
                    result,
                    pipeline_name=dependency.pipeline,
                    fields=dependency_profile,
                )

        for enricher in config.enrichers:
            enricher_profile = self._load_pipeline_profile(enricher.pipeline)
            if enricher_profile is not None:
                self._register_source_aliases(
                    result,
                    pipeline_name=enricher.pipeline,
                    fields=enricher_profile,
                )

        return result

    def _load_pipeline_schema_fields(self, pipeline_name: str) -> SchemaFields | None:
        """Load schema fields for a specific pipeline."""
        registry = self._get_schema_registry()
        identity = self._parse_pipeline_identity(pipeline_name)
        if identity is None:
            return None

        provider, entity = identity
        pipeline_key = f"{provider}_{entity}"
        schema_class = registry.get(pipeline_key)
        if schema_class is None:
            self._logger.debug(
                "No schema found for pipeline",
                provider=provider,
                entity=entity,
                pipeline_key=pipeline_key,
                pipeline=pipeline_name,
            )
            return None

        return extract_fields_from_schema(
            self, schema_class, source=f"{provider}.{entity}"
        )

    def _load_pipeline_profile(self, pipeline_name: str) -> ProfileInfo | None:
        """Load deterministic profile metadata for one pipeline."""
        identity = self._parse_pipeline_identity(pipeline_name)
        if identity is None:
            return None
        provider, entity = identity
        profile = resolve_normalization_profile(provider, entity)
        if profile is None:
            self._logger.debug(
                "No normalization profile found for pipeline",
                provider=provider,
                entity=entity,
                pipeline=pipeline_name,
            )
            return None

        profile_identity = profile.identity
        return ProfileInfo(
            source=f"{provider}.{entity}",
            profile_name=profile_identity.profile_name,
            profile_version=profile_identity.profile_version,
            profile_hash=profile_identity.profile_hash,
            field_hashes={
                field_name: rule_identity.compatibility_hash
                for field_name in sorted(profile.fields)
                for rule_identity in (profile.field_identity(field_name),)
                if rule_identity is not None
            },
        )

    @classmethod
    def _get_schema_registry(cls) -> dict[str, type]:
        """Get or create the schema registry keyed by ``provider_entity``."""
        if cls._SCHEMA_REGISTRY is not None:
            return cls._SCHEMA_REGISTRY

        module_aliases: dict[tuple[str, str], str] = {
            ("chembl", "protein_class"): "protein_classification",
        }
        registry: dict[str, type] = {}

        from bioetl.domain.schemas.generated.registry import CANONICAL_SCHEMA_REGISTRY

        for entry in CANONICAL_SCHEMA_REGISTRY:
            provider = entry.provider.lower()
            entity = entry.entity.lower()
            module_entity = module_aliases.get((provider, entity), entity)
            module_name = f"bioetl.domain.schemas.{provider}.{module_entity}"
            pipeline_key = f"{provider}_{entity}"

            try:
                module = import_module(module_name)
            except ImportError:
                continue

            schema_class = _find_schema_class(module)
            if schema_class is not None:
                registry[pipeline_key] = schema_class

        cls._SCHEMA_REGISTRY = registry
        return registry
