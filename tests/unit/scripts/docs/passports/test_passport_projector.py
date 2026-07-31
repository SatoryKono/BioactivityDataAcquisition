"""Tests for deterministic executable-unit passport projections."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import jsonschema
import pytest

from bioetl.infrastructure.config.workflow_config_api import load_workflow_config
from scripts.docs.passports.cli import main
from scripts.docs.passports.inventory import discover_units
from scripts.docs.passports.manual_sidecar import load_manual_sidecar
from scripts.docs.passports.duplicate_audit import audit_markdown_texts
from scripts.docs.passports.projector import (
    DEFAULT_CONFIGS_ROOT,
    PROJECT_ROOT,
    _source_revision,
    build_all_outputs,
    check_outputs,
    write_outputs,
)
from scripts.docs.passports.validation import validate_composite_payload

pytestmark = pytest.mark.unit

REVISION = "0123456789abcdef0123456789abcdef01234567"


@dataclass(frozen=True)
class _RegistryEntry:
    pipeline_name: str
    provider: str
    entity_type: str
    data_source_provider: str | None = None


def _write_entity_config(root: Path, name: str, provider: str, entity: str) -> None:
    path = root / "entities" / provider / f"{entity}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "pipeline:\n"
        f"  pipeline_name: {name}\n"
        f"  provider: {provider}\n"
        f"  entity_type: {entity}\n",
        encoding="utf-8",
    )


def test_inventory_matches_canonical_executable_surfaces() -> None:
    units = discover_units(DEFAULT_CONFIGS_ROOT)
    assert sum(item.kind == "pipeline" for item in units) == 22
    assert sum(item.kind == "composite" for item in units) == 5
    assert sum(item.kind == "workflow" for item in units) == 27
    assert len({item.typed_id for item in units}) == 54


def test_inventory_is_registry_owned_ordered_and_alias_safe(tmp_path: Path) -> None:
    _write_entity_config(tmp_path, "zeta_item", "zeta", "item")
    _write_entity_config(tmp_path, "alpha_item", "alpha", "item")
    entries = (
        _RegistryEntry("zeta_item", "zeta", "item"),
        _RegistryEntry("alpha_item", "alpha", "item", "alpha_lookup"),
    )
    units = discover_units(tmp_path, registry_entries=entries)
    assert [item.typed_id for item in units] == [
        "pipeline:alpha_item",
        "pipeline:zeta_item",
    ]
    assert units[0].aliases == ("data-source:alpha_lookup",)


def test_inventory_rejects_registry_config_mismatch_and_duplicate_alias(
    tmp_path: Path,
) -> None:
    _write_entity_config(tmp_path, "alpha_item", "alpha", "item")
    with pytest.raises(ValueError, match="registry/config mismatch"):
        discover_units(
            tmp_path,
            registry_entries=(_RegistryEntry("missing_item", "alpha", "item"),),
        )
    _write_entity_config(tmp_path, "beta_item", "beta", "item")
    with pytest.raises(ValueError, match="aliases must resolve exactly once"):
        discover_units(
            tmp_path,
            registry_entries=(
                _RegistryEntry("alpha_item", "alpha", "item", "shared"),
                _RegistryEntry("beta_item", "beta", "item", "shared"),
            ),
        )


def test_generation_is_byte_deterministic(tmp_path: Path) -> None:
    first = build_all_outputs(output_root=tmp_path, source_revision=REVISION)
    second = build_all_outputs(output_root=tmp_path, source_revision=REVISION)
    assert first == second
    assert len(first) == 112
    write_outputs(first)
    assert check_outputs(second) == []


def test_source_revision_excludes_ephemeral_merge_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    def _run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        captured.extend(command)
        return subprocess.CompletedProcess(command, 0, stdout=f"{REVISION}\n")

    monkeypatch.delenv("BIOETL_PASSPORT_SOURCE_REVISION", raising=False)
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setattr(subprocess, "run", _run)

    assert _source_revision() == REVISION
    assert captured[:4] == ["git", "log", "--no-merges", "-1"]
    assert captured[4:6] == ["--format=%H", "HEAD^2"]


def test_generation_is_subprocess_environment_invariant(tmp_path: Path) -> None:
    baseline_root = tmp_path / "first"
    baseline_outputs = build_all_outputs(
        output_root=baseline_root,
        source_revision=REVISION,
    )
    baseline = {
        path.relative_to(baseline_root): content
        for path, content in baseline_outputs.items()
    }
    output_root = tmp_path / "second"
    alternate_tmp = tmp_path / "alternate-tmp"
    alternate_tmp.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.docs",
            "passports",
            "generate",
            "--output-root",
            str(output_root),
            "--source-revision",
            REVISION,
        ],
        cwd=PROJECT_ROOT,
        env={
            **os.environ,
            "TZ": "Pacific/Auckland",
            "PYTHONHASHSEED": "8675309",
            "TMPDIR": str(alternate_tmp),
        },
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    alternate = {
        path.relative_to(output_root): path.read_bytes()
        for path in sorted(output_root.rglob("*"))
        if path.is_file()
    }
    assert baseline == alternate


def test_workflow_operations_are_classified(tmp_path: Path) -> None:
    outputs = build_all_outputs(output_root=tmp_path, source_revision=REVISION)
    core = json.loads(outputs[tmp_path / "generated/workflows/chembl_core.json"])
    operations = {
        item["transform_name"]: item["classification"]
        for item in core["external_data_operations"]
    }
    assert operations["reconcile_foreign_keys"] == [
        "data_plane_transformation",
        "dq_validation",
        "destructive_mutation",
    ]
    assert operations["summarize_upstream_outputs"] == ["control_plane_projection"]
    workflow = load_workflow_config("chembl_core")
    assert core["dag"]["topological_order"] == list(workflow.topological_step_ids)
    assert core["dag"]["mermaid"].startswith("flowchart TD\n")
    assert " --> " in core["dag"]["mermaid"]


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
        assert jsonschema.validate(facts, schema) is None


def test_representative_pipeline_projection_profiles_are_explicit(
    tmp_path: Path,
) -> None:
    outputs = build_all_outputs(output_root=tmp_path, source_revision=REVISION)

    def profiles(pipeline: str) -> set[str]:
        facts = json.loads(outputs[tmp_path / f"generated/pipelines/{pipeline}.json"])
        return set(facts["execution"]["projection_profiles"])

    assert {"http", "batch"} <= profiles("pubmed_publication")
    assert {"http", "batch", "async_mapping"} <= profiles("uniprot_idmapping")
    assert {"derived", "local_snapshot", "batch"} <= profiles(
        "chembl_target_protein_classification"
    )


def test_schema_rejects_unknown_nested_keys_and_incompatible_version(
    tmp_path: Path,
) -> None:
    outputs = build_all_outputs(output_root=tmp_path, source_revision=REVISION)
    facts = json.loads(outputs[tmp_path / "generated/pipelines/chembl_activity.json"])
    schema = json.loads(
        (
            PROJECT_ROOT
            / "docs/04-reference/passports/schemas/pipeline-passport.schema.json"
        ).read_text(encoding="utf-8")
    )
    unknown = deepcopy(facts)
    unknown["identity"]["manual_override"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(unknown, schema)
    incompatible = deepcopy(facts)
    incompatible["passport_schema_version"] = "2.0.0"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(incompatible, schema)


def test_composite_validation_fails_closed_for_invalid_invariants() -> None:
    invalid = {
        "composite": {
            "seed": {"output_keys": ["entity_id"]},
            "dependencies": [
                {
                    "pipeline": "upstream",
                    "join_keys": ["missing_key"],
                    "cardinality": "many_to_many",
                }
            ],
            "enrichers": [],
            "merge": {
                "strategy": "guess",
                "conflict_resolution": "explicit_rules",
                "field_priorities": {},
                "aggregation": "arbitrary",
            },
        }
    }
    codes = {item["code"] for item in validate_composite_payload(invalid)}
    assert codes == {
        "COMPOSITE_AGGREGATION_UNSUPPORTED",
        "COMPOSITE_CARDINALITY_UNSUPPORTED",
        "COMPOSITE_EXPLICIT_PRIORITIES_INCOMPLETE",
        "COMPOSITE_JOIN_KEY_NOT_IN_SEED_OUTPUT",
        "COMPOSITE_MERGE_STRATEGY_INVALID",
    }


def test_source_refs_exist_and_metric_labels_are_bounded(tmp_path: Path) -> None:
    outputs = build_all_outputs(output_root=tmp_path, source_revision=REVISION)
    prohibited = {
        "run_id",
        "manifest_id",
        "workflow_run_id",
        "payload_hash",
        "record_id",
    }
    for path, content in outputs.items():
        if path.suffix != ".json" or "generated" not in path.parts:
            continue
        facts = json.loads(content)
        for source_ref in facts["source_references"]:
            assert (PROJECT_ROOT / source_ref["path"]).exists(), source_ref
        assert prohibited.isdisjoint(facts["observability"]["metric_labels"])


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


def test_pipeline_markdown_is_compact_complete_and_not_a_json_dump(
    tmp_path: Path,
) -> None:
    outputs = build_all_outputs(output_root=tmp_path, source_revision=REVISION)
    path = tmp_path / "pipelines/chembl_assay.md"
    markdown = outputs[path].decode("utf-8")
    facts = json.loads(outputs[tmp_path / "generated/pipelines/chembl_assay.json"])
    assert 2 <= len(facts["summary"]["sentences"]) <= 5
    assert facts["extraction"]["filters"]
    assert facts["extraction"]["selected_fields"]
    assert facts["operator_commands"][0]["command"] == (
        "bioetl run --pipeline chembl_assay"
    )
    assert facts["diagrams"][0]["mermaid"].startswith("flowchart LR\n")
    assert "## Назначение и обработка данных" in markdown
    assert "## Операторские команды" in markdown
    assert "## Диаграммы" in markdown
    assert "## Generated facts" not in markdown
    assert "```json" not in markdown
    assert "## Diagnostics" not in markdown
    assert len(markdown.splitlines()) < 120


def test_composite_commands_and_diagram_use_real_composite_cli_options(
    tmp_path: Path,
) -> None:
    outputs = build_all_outputs(output_root=tmp_path, source_revision=REVISION)
    facts = json.loads(
        outputs[tmp_path / "generated/pipelines/composite_publication.json"]
    )
    commands = [item["command"] for item in facts["operator_commands"]]
    assert "bioetl run-composite --composite publication" in commands
    assert "bioetl run-composite --composite publication --seed-limit 100" in commands
    diagram = facts["diagrams"][0]["mermaid"]
    assert "chembl_publication" in diagram
    assert "crossref_publication · doi, title" in diagram
    assert "Merge: left_outer / seed_priority" in diagram
    assert "Quarantine / nullification" in diagram


def test_duplicate_audit_reports_compaction(tmp_path: Path) -> None:
    outputs = build_all_outputs(output_root=tmp_path, source_revision=REVISION)
    markdown = [
        content.decode("utf-8")
        for path, content in outputs.items()
        if path.parent == tmp_path / "pipelines" and path.suffix == ".md"
    ]
    report = audit_markdown_texts(markdown)
    assert report["passport_count"] == 27
    assert report["total_markdown_lines"] < 3000
    assert report["empty_section_count"] == 0
    assert report["identity_duplicate_count"] == 0
