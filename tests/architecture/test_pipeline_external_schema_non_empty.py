"""Architecture guard: registered pipelines must use non-empty external schema files."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from bioetl.composition.factories.pipeline_factories import PIPELINE_CONFIGS

_SCHEMA_REF_RE = re.compile(r"^\s*data_schema_file:\s*(.+?)\s*$", re.MULTILINE)
_EMPTY_COLUMN_GROUPS_RE = re.compile(r"^\s*column_groups:\s*\[\s*\]\s*$", re.MULTILINE)


def _find_pipeline_config(provider: str, entity_type: str) -> tuple[Path | None, str]:
    """Find pipeline config in legacy or unified location.

    Returns (path, format) where format is 'legacy' or 'unified'.
    """
    legacy = Path("configs/pipelines") / provider / f"{entity_type}.yaml"
    if legacy.exists():
        return legacy, "legacy"
    unified = Path("configs/entities") / provider / f"{entity_type}.yaml"
    if unified.exists():
        return unified, "unified"
    return None, ""


@pytest.mark.architecture
class TestPipelineExternalSchemaNotEmpty:
    """Ensure external schema files are not empty placeholders."""

    def test_registered_pipeline_schema_files_are_not_empty(self) -> None:
        """Every PIPELINE_CONFIGS entry must resolve to a non-empty external schema file."""
        failures: list[str] = []

        for pipeline in PIPELINE_CONFIGS:
            config_path, fmt = _find_pipeline_config(
                pipeline.provider, pipeline.entity_type
            )
            if config_path is None:
                failures.append(
                    f"{pipeline.pipeline_name}: missing pipeline config in "
                    f"configs/pipelines/ and configs/entities/"
                )
                continue

            text = config_path.read_text(encoding="utf-8")

            # Unified format: schema is inline under 'schema:' key
            if fmt == "unified":
                raw = yaml.safe_load(text) or {}
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
                continue

            # Legacy format: external schema file reference
            match = _SCHEMA_REF_RE.search(text)
            if match:
                raw_ref = match.group(1).strip().strip("\"'")
                schema_path = (config_path.parent / raw_ref).resolve()
            else:
                schema_path = (
                    config_path.parent
                    / f"../../schemas/{pipeline.provider}/{pipeline.entity_type}.yaml"
                ).resolve()

            if not schema_path.exists():
                failures.append(
                    f"{pipeline.pipeline_name}: schema file not found {schema_path}"
                )
                continue

            schema_text = schema_path.read_text(encoding="utf-8")
            if _EMPTY_COLUMN_GROUPS_RE.search(schema_text):
                failures.append(
                    f"{pipeline.pipeline_name}: schema {schema_path} has empty column_groups"
                )
                continue

            if "column_groups:" not in schema_text:
                failures.append(
                    f"{pipeline.pipeline_name}: schema {schema_path} misses column_groups"
                )

        assert not failures, "\n".join(failures)
