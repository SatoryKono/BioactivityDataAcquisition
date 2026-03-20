"""Architecture guard: registered pipelines must use non-empty external schema files."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bioetl.composition.factories.pipeline.registry_manifest import PIPELINE_CONFIGS


def _find_pipeline_config(provider: str, entity_type: str) -> Path | None:
    """Find pipeline config in canonical unified location."""
    unified = Path("configs/entities") / provider / f"{entity_type}.yaml"
    if unified.exists():
        return unified
    return None


@pytest.mark.architecture
class TestPipelineExternalSchemaNotEmpty:
    """Ensure external schema files are not empty placeholders."""

    def test_registered_pipeline_schema_files_are_not_empty(self) -> None:
        """Every PIPELINE_CONFIGS entry must resolve to a non-empty external schema file."""
        failures: list[str] = []

        for pipeline in PIPELINE_CONFIGS:
            config_path = _find_pipeline_config(pipeline.provider, pipeline.entity_type)
            if config_path is None:
                failures.append(
                    f"{pipeline.pipeline_name}: missing pipeline config in "
                    "configs/entities/"
                )
                continue

            raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            schema_section = raw.get("schema")
            if not isinstance(schema_section, dict):
                failures.append(
                    f"{pipeline.pipeline_name}: no 'schema' section in {config_path}"
                )
                continue
            groups = schema_section.get("column_groups")
            if not isinstance(groups, list) or not groups:
                failures.append(
                    f"{pipeline.pipeline_name}: empty/missing column_groups "
                    f"in {config_path}"
                )

        assert not failures, "\n".join(failures)
