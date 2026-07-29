"""Tests for deterministic executable-unit passport projections."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from scripts.docs.passports.cli import main
from scripts.docs.passports.inventory import discover_units
from scripts.docs.passports.manual_sidecar import load_manual_sidecar
from scripts.docs.passports.projector import (
    DEFAULT_CONFIGS_ROOT,
    PROJECT_ROOT,
    build_all_outputs,
    check_outputs,
    write_outputs,
)

REVISION = "0123456789abcdef0123456789abcdef01234567"


def test_inventory_matches_canonical_executable_surfaces() -> None:
    units = discover_units(DEFAULT_CONFIGS_ROOT)
    assert sum(item.kind == "pipeline" for item in units) == 22
    assert sum(item.kind == "composite" for item in units) == 5
    assert sum(item.kind == "workflow" for item in units) == 27
    assert len({item.typed_id for item in units}) == 54


def test_generation_is_byte_deterministic(tmp_path: Path) -> None:
    first = build_all_outputs(output_root=tmp_path, source_revision=REVISION)
    second = build_all_outputs(output_root=tmp_path, source_revision=REVISION)
    assert first == second
    assert len(first) == 111
    write_outputs(first)
    assert check_outputs(second) == []


def test_workflow_operations_are_classified(tmp_path: Path) -> None:
    outputs = build_all_outputs(output_root=tmp_path, source_revision=REVISION)
    core = json.loads(
        outputs[tmp_path / "generated/workflows/chembl_core.json"]
    )
    operations = {
        item["transform_name"]: item["classification"]
        for item in core["external_data_operations"]
    }
    assert operations["reconcile_foreign_keys"] == [
        "data_plane_transformation",
        "dq_validation",
        "destructive_mutation",
    ]
    assert operations["summarize_upstream_outputs"] == [
        "control_plane_projection"
    ]


def test_generated_facts_validate_against_published_schemas(tmp_path: Path) -> None:
    outputs = build_all_outputs(output_root=tmp_path, source_revision=REVISION)
    schema_root = PROJECT_ROOT / "docs/04-reference/passports/schemas"
    pipeline_schema = json.loads(
        (schema_root / "pipeline-passport.schema.json").read_text(encoding="utf-8")
    )
    workflow_schema = json.loads(
        (schema_root / "workflow-passport.schema.json").read_text(encoding="utf-8")
    )
    for path, content in outputs.items():
        if path.suffix != ".json" or "generated" not in path.parts:
            continue
        facts = json.loads(content)
        schema = workflow_schema if facts["kind"] == "workflow" else pipeline_schema
        jsonschema.validate(facts, schema)


def test_manual_sidecar_is_strict_and_preserved(tmp_path: Path) -> None:
    sidecar = tmp_path / "manual.yaml"
    sidecar.write_text(
        "owner: BioETL Team\nowner_approved: true\npurpose: Explain facts.\n",
        encoding="utf-8",
    )
    before = sidecar.read_bytes()
    assert load_manual_sidecar(sidecar)["purpose"] == "Explain facts."
    assert sidecar.read_bytes() == before
    sidecar.write_text(
        "owner: BioETL Team\nowner_approved: true\nschema_hash: forbidden\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Unknown manual passport keys"):
        load_manual_sidecar(sidecar)


def test_cli_generate_and_check(tmp_path: Path) -> None:
    args = [
        "--output-root",
        str(tmp_path),
        "--source-revision",
        REVISION,
    ]
    assert main(["generate", *args]) == 0
    assert main(["check", *args]) == 0
    (tmp_path / "index.md").write_text("stale\n", encoding="utf-8")
    assert main(["check", *args]) == 1
