"""Configuration migration utilities (infrastructure layer).

Handles migration of legacy pipeline configuration formats to the current structure.

Supported versions:
- v1 (flat legacy): entity, provider at root + sources section -> current nested format
- v2 (nested): identity section already present -> minimal migration

The migrator is idempotent: running it multiple times produces the same result.

Note:
    This module was moved from domain/configs/migration.py to infrastructure
    as configuration format migration is a technical concern (infrastructure),
    not a business rule (domain).
"""

from __future__ import annotations

import warnings
from typing import Any


class ConfigMigrator:
    """Migrates legacy pipeline configs to the current decomposed structure.

    This class handles backward compatibility by converting:
    - Flat fields (id, provider, entity) -> identity section
    - Flat fields (input_mode, input_path, batch_size) -> source section
    - Flat fields (output_path, dry_run) -> sink section
    - Legacy pipeline dict -> stages section
    - Flat observability fields -> observability section
    - Flat quality fields -> quality section
    - Flat feature fields -> features section
    - Legacy sources section -> provider_config
    - Legacy client config keys (timeout -> timeout_sec, etc.)
    """

    # Fields belonging to each section
    IDENTITY_FIELDS = ("id", "provider", "entity", "primary_key")
    SOURCE_FIELDS = ("input_mode", "input_path", "batch_size")
    SINK_FIELDS = ("output_path", "dry_run")
    STAGES_FIELDS = ("extract", "transform", "load")
    RUNTIME_FIELDS = ("pagination", "client", "http", "storage")
    OBSERVABILITY_FIELDS = ("logging", "metrics")
    QUALITY_FIELDS = ("determinism", "qc", "hashing", "normalization")
    FEATURE_FIELDS = ("features", "interface_features", "interfaces")

    @classmethod
    def migrate(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Migrate legacy config format to current decomposed structure.

        Args:
            data: Raw configuration dictionary (possibly in legacy format).

        Returns:
            Migrated configuration with decomposed sections.
        """
        if not isinstance(data, dict):
            return data

        migrated = dict(data)
        version = cls._detect_version(migrated)

        if version == 1:
            warnings.warn(
                "Legacy v1 config format detected. "
                "Please update to v2 format with identity/source/sink sections. "
                "See docs/migration.md",
                DeprecationWarning,
                stacklevel=4,
            )
            cls._migrate_v1_to_v2(migrated)

        # Always apply current format normalization (idempotent)
        cls._normalize_current_format(migrated)

        return migrated

    @classmethod
    def _detect_version(cls, data: dict[str, Any]) -> int:
        """Detect configuration format version.

        Returns:
            1 for legacy flat format (entity/provider at root without identity section)
            2 for current nested format (identity section present)
        """
        # v2: has identity section
        if "identity" in data:
            return 2

        # v1: has flat entity/provider or legacy sources section
        if "entity" in data or "entity_name" in data:
            if "provider" in data or "sources" in data:
                return 1

        # Default to v2 (assume current format)
        return 2

    @classmethod
    def _migrate_v1_to_v2(cls, data: dict[str, Any]) -> None:
        """Migrate v1 (flat legacy) format to v2 (nested) format.

        This handles the original flat config format with:
        - entity_name as alias for entity
        - sources section with provider configs
        - storage section with output_path
        - pipeline section with name and stages
        """
        # Step 1: Handle entity_name -> entity alias
        cls._migrate_entity_name_alias(data)

        # Step 2: Generate id from pipeline.name or provider.entity
        cls._generate_pipeline_id(data)

        # Step 3: Extract output_path from storage section
        cls._migrate_storage_output_path(data)

        # Step 4: Extract batch_size from sources section
        cls._migrate_batch_size_from_sources(data)

        # Step 5: Extract provider_config from sources section
        cls._migrate_provider_config_from_sources(data)

        # Step 6: Remove legacy sources section
        data.pop("sources", None)

        # Step 7: Migrate api_base_url to provider_config
        cls._migrate_api_base_url(data)

    @classmethod
    def _normalize_current_format(cls, data: dict[str, Any]) -> None:
        """Normalize current format (idempotent operations).

        These transformations are safe to run multiple times.
        """
        # Handle entity_name alias (can appear in both v1 and v2)
        cls._migrate_entity_name_alias(data)

        # Pack identity section
        cls._pack_identity(data)

        # Pack source section
        cls._pack_source(data)

        # Pack sink section
        cls._pack_sink(data)

        # Pack stages from pipeline dict
        cls._pack_stages(data)

        # Pack section configs (runtime, observability, quality, features)
        cls._pack_section("runtime", cls.RUNTIME_FIELDS, data)
        cls._pack_section("observability", cls.OBSERVABILITY_FIELDS, data)
        cls._pack_section("quality", cls.QUALITY_FIELDS, data)
        cls._pack_section("features", cls.FEATURE_FIELDS, data)

        # Fix legacy client config keys in runtime section
        cls._migrate_runtime_client_keys(data)

    # =========================================================================
    # V1 -> V2 migration helpers
    # =========================================================================

    @classmethod
    def _migrate_entity_name_alias(cls, data: dict[str, Any]) -> None:
        """Handle entity_name as alias for entity."""
        if "entity_name" in data and "entity" not in data:
            data["entity"] = data.pop("entity_name")
        elif "entity_name" in data:
            data.pop("entity_name")

    @classmethod
    def _generate_pipeline_id(cls, data: dict[str, Any]) -> None:
        """Generate pipeline id from pipeline.name or provider.entity."""
        if "id" in data:
            return

        pipeline_section = data.get("pipeline")
        if isinstance(pipeline_section, dict) and pipeline_section.get("name"):
            data["id"] = pipeline_section["name"]
        elif data.get("provider") and data.get("entity"):
            data["id"] = f"{data['provider']}.{data['entity']}"

    @classmethod
    def _migrate_storage_output_path(cls, data: dict[str, Any]) -> None:
        """Extract output_path from storage section."""
        if "output_path" in data:
            return

        storage_section = data.get("storage")
        if isinstance(storage_section, dict) and "output_path" in storage_section:
            data["output_path"] = storage_section["output_path"]

    @classmethod
    def _migrate_batch_size_from_sources(cls, data: dict[str, Any]) -> None:
        """Extract batch_size from legacy sources section."""
        if "batch_size" in data:
            return

        sources_section = data.get("sources")
        if not isinstance(sources_section, dict):
            return

        provider = data.get("provider")
        source_entry: Any | None = None
        if provider and provider in sources_section:
            source_entry = sources_section[provider]
        elif len(sources_section) == 1:
            source_entry = next(iter(sources_section.values()))

        if isinstance(source_entry, dict):
            batch_size = source_entry.get("batch_size")
            if isinstance(batch_size, int):
                data["batch_size"] = batch_size

    @classmethod
    def _migrate_provider_config_from_sources(cls, data: dict[str, Any]) -> None:
        """Extract provider_config from legacy sources section."""
        if "provider_config" in data:
            return

        sources_section = data.get("sources")
        if not isinstance(sources_section, dict):
            return

        provider = data.get("provider")
        source_entry: Any | None = None
        if provider and provider in sources_section:
            source_entry = sources_section[provider]
        elif len(sources_section) == 1:
            source_entry = next(iter(sources_section.values()))

        if not isinstance(source_entry, dict):
            return

        provider_config = dict(source_entry)
        if "provider" not in provider_config and provider:
            provider_config["provider"] = provider
        data["provider_config"] = provider_config

    @classmethod
    def _migrate_api_base_url(cls, data: dict[str, Any]) -> None:
        """Migrate api_base_url to provider_config.base_url."""
        if "api_base_url" not in data:
            return

        provider_conf = data.get("provider_config")
        if isinstance(provider_conf, dict):
            provider_conf["base_url"] = data.pop("api_base_url")
        else:
            data.pop("api_base_url")

    @classmethod
    def _migrate_runtime_client_keys(cls, data: dict[str, Any]) -> None:
        """Fix legacy client config keys in runtime section."""
        runtime = data.get("runtime")
        if not isinstance(runtime, dict):
            return

        client = runtime.get("client")
        if not isinstance(client, dict):
            return

        # Legacy key mappings
        legacy_mappings = {
            "timeout": "timeout_sec",
            "rate_limit": "rate_limit_per_sec",
            "backoff": "backoff_factor",
        }

        for old_key, new_key in legacy_mappings.items():
            if old_key in client and new_key not in client:
                client[new_key] = client.pop(old_key)
            elif old_key in client:
                client.pop(old_key)

    # =========================================================================
    # Section packing helpers (v2 normalization)
    # =========================================================================

    @classmethod
    def _pack_identity(cls, data: dict[str, Any]) -> None:
        """Pack identity fields into identity section."""
        if "identity" in data:
            return

        identity_fields: dict[str, Any] = {}
        for field in cls.IDENTITY_FIELDS:
            if field in data:
                value = data.pop(field)
                # Map 'id' to 'pipeline_id' for PipelineIdentityConfig
                if field == "id":
                    identity_fields["pipeline_id"] = value
                elif field == "primary_key":
                    # Coerce primary_key to list if string
                    if isinstance(value, str):
                        identity_fields["primary_key"] = [value] if value else []
                    elif value is None:
                        identity_fields["primary_key"] = []
                    else:
                        identity_fields["primary_key"] = list(value)
                else:
                    identity_fields[field] = value

        if identity_fields:
            data["identity"] = identity_fields

    @classmethod
    def _pack_source(cls, data: dict[str, Any]) -> None:
        """Pack source fields into source section."""
        if "source" in data:
            return

        source_fields: dict[str, Any] = {}
        for field in cls.SOURCE_FIELDS:
            if field in data:
                source_fields[field] = data.pop(field)

        # Handle csv_options -> csv
        if "csv_options" in data:
            source_fields["csv"] = data.pop("csv_options")
        elif "csv" in data and "runtime" not in data:
            # csv at root level goes to source if no runtime section
            source_fields["csv"] = data.pop("csv")

        if source_fields:
            data["source"] = source_fields

    @classmethod
    def _pack_sink(cls, data: dict[str, Any]) -> None:
        """Pack sink fields into sink section."""
        if "sink" in data:
            return

        sink_fields: dict[str, Any] = {}
        for field in cls.SINK_FIELDS:
            if field in data:
                sink_fields[field] = data.pop(field)

        # Handle output section
        if "output" in data:
            output_val = data.pop("output")
            if isinstance(output_val, dict):
                sink_fields["output"] = output_val

        if sink_fields:
            data["sink"] = sink_fields

    @classmethod
    def _pack_stages(cls, data: dict[str, Any]) -> None:
        """Pack stages from legacy pipeline dict."""
        if "pipeline" not in data:
            return

        pipeline_dict = data.pop("pipeline")
        if not isinstance(pipeline_dict, dict):
            return

        # Extract primary_key from pipeline dict -> identity
        if "primary_key" in pipeline_dict:
            pk_from_pipeline = pipeline_dict.pop("primary_key")
            identity = data.setdefault("identity", {})
            if isinstance(identity, dict) and identity.get("primary_key") is None:
                # Coerce to list
                if isinstance(pk_from_pipeline, str):
                    identity["primary_key"] = (
                        [pk_from_pipeline] if pk_from_pipeline else []
                    )
                elif pk_from_pipeline is None:
                    identity["primary_key"] = []
                else:
                    identity["primary_key"] = list(pk_from_pipeline)

        # Extract stages
        if "stages" not in data:
            stages_fields: dict[str, Any] = {}
            for field in cls.STAGES_FIELDS:
                if field in pipeline_dict:
                    stages_fields[field] = pipeline_dict[field]
            if stages_fields:
                data["stages"] = stages_fields

    @classmethod
    def _pack_section(
        cls, section_key: str, keys: tuple[str, ...], data: dict[str, Any]
    ) -> None:
        """Pack flat fields into a section.

        Args:
            section_key: Name of the target section.
            keys: Field names that belong to this section.
            data: Configuration dictionary to modify.
        """
        existing_section = (
            data.get(section_key) if isinstance(data.get(section_key), dict) else None
        )
        keys_to_collect = list(keys)
        if section_key in keys_to_collect and existing_section is not None:
            keys_to_collect.remove(section_key)

        collected = {key: data.pop(key) for key in keys_to_collect if key in data}
        if not collected and existing_section is None:
            return

        target_section: dict[str, Any] = dict(existing_section or {})
        nested_from_collected = collected.pop(section_key, None)
        if isinstance(nested_from_collected, dict):
            target_section |= nested_from_collected

        for key, value in collected.items():
            if (
                key in target_section
                and isinstance(target_section[key], dict)
                and isinstance(value, dict)
            ):
                target_section[key] = {**target_section[key], **value}
            else:
                target_section[key] = value

        if target_section:
            data[section_key] = target_section


__all__ = ["ConfigMigrator"]
