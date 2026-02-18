"""Architecture guard: registered pipelines must use non-empty external schema files."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from bioetl.composition.factories.pipeline_factories import PIPELINE_CONFIGS

_SCHEMA_REF_RE = re.compile(r"^\s*data_schema_file:\s*(.+?)\s*$", re.MULTILINE)
_EMPTY_COLUMN_GROUPS_RE = re.compile(r"^\s*column_groups:\s*\[\s*\]\s*$", re.MULTILINE)


@pytest.mark.architecture
class TestPipelineExternalSchemaNotEmpty:
    """Ensure external schema files are not empty placeholders."""

    def test_registered_pipeline_schema_files_are_not_empty(self) -> None:
        """Every PIPELINE_CONFIGS entry must resolve to a non-empty external schema file."""
        failures: list[str] = []

        for pipeline in PIPELINE_CONFIGS:
            pipeline_path = (
                Path("configs")
                / "pipelines"
                / pipeline.provider
                / (f"{pipeline.entity_type}.yaml")
            )
            if not pipeline_path.exists():
                failures.append(
                    f"{pipeline.pipeline_name}: missing pipeline config {pipeline_path}"
                )
                continue

            text = pipeline_path.read_text(encoding="utf-8")
            match = _SCHEMA_REF_RE.search(text)
            if match:
                raw_ref = match.group(1).strip().strip("\"'")
                schema_path = (pipeline_path.parent / raw_ref).resolve()
            else:
                schema_path = (
                    pipeline_path.parent
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
