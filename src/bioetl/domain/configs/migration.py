"""Configuration migration utilities.

Handles migration of legacy pipeline configuration formats to the new decomposed structure.
"""

from __future__ import annotations

from typing import Any


class ConfigMigrator:
    """Migrates legacy flat pipeline configs to the new decomposed structure.

    This class handles backward compatibility by converting:
    - Flat fields (id, provider, entity) -> identity section
    - Flat fields (input_mode, input_path, batch_size) -> source section
    - Flat fields (output_path, dry_run) -> sink section
    - Legacy pipeline dict -> stages section
    - Flat observability fields -> observability section
    - Flat quality fields -> quality section
    - Flat feature fields -> features section
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
        """Migrate legacy config format to new decomposed structure.

        Args:
            data: Raw configuration dictionary (possibly in legacy format).

        Returns:
            Migrated configuration with decomposed sections.
        """
        if not isinstance(data, dict):
            return data

        migrated = dict(data)

        # Step 1: Handle entity_name -> entity alias
        cls._migrate_entity_name_alias(migrated)

        # Step 2: Pack identity section
        cls._pack_identity(migrated)

        # Step 3: Pack source section
        cls._pack_source(migrated)

        # Step 4: Pack sink section
        cls._pack_sink(migrated)

        # Step 5: Pack stages from pipeline dict
        cls._pack_stages(migrated)

        # Step 6: Pack section configs (runtime, observability, quality, features)
        cls._pack_section("runtime", cls.RUNTIME_FIELDS, migrated)
        cls._pack_section("observability", cls.OBSERVABILITY_FIELDS, migrated)
        cls._pack_section("quality", cls.QUALITY_FIELDS, migrated)
        cls._pack_section("features", cls.FEATURE_FIELDS, migrated)

        return migrated

    @classmethod
    def _migrate_entity_name_alias(cls, data: dict[str, Any]) -> None:
        """Handle entity_name as alias for entity."""
        if "entity_name" in data and "entity" not in data:
            data["entity"] = data.pop("entity_name")
        elif "entity_name" in data:
            data.pop("entity_name")

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
