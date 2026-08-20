"""Build canonical passport facts and human-readable projections."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml

from bioetl.infrastructure.config.workflow_config_api import load_workflow_config

from .inventory import ExecutableUnit, discover_units
from .duplicate_audit import audit_markdown_texts
from .manual_sidecar import load_manual_sidecar
from .pipeline_projection import (
    build_ordinary_projection,
    composite_mermaid,
    operator_commands,
    ordinary_mermaid,
)
from .source_facts import load_effective_pipeline_facts
from .validation import (
    validate_composite_payload,
    validate_pipeline_publication,
    workflow_mermaid,
)

SCHEMA_VERSION = "1.0.0"
PROJECTOR_VERSION = "1.0.0"
PIPELINE_PROJECTOR_VERSION = "1.1.0"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIGS_ROOT = PROJECT_ROOT / "configs"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "docs/04-reference/passports"
JsonObject = dict[str, Any]
_DUPLICATION_BASELINE = {
    "passport_count": 27,
    "total_markdown_lines": 6511,
    "duplicate_line_groups": 250,
    "duplicate_paragraph_groups": 4,
    "duplicate_diagram_groups": 0,
    "identity_duplicate_count": 0,
    "empty_section_count": 0,
    "average_passport_lines": 241.1,
    "maximum_passport_lines": 665,
}


def passport_markdown_filename(unit_id: str) -> str:
    """Return the canonical kebab-case Markdown filename for an executable ID."""
    return f"{unit_id.replace('_', '-')}.md"


def _repo_path(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def _display_path(path: Path) -> str:
    try:
        return _repo_path(path)
    except ValueError:
        return path.as_posix()


def _load_yaml(path: Path) -> JsonObject:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return payload


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
        .encode("utf-8")
        .replace(b"\r\n", b"\n")
        + b"\n"
    )


def _sha(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_bytes(value)).hexdigest()}"


def _source_revision() -> str:
    """Resolve the latest revision touching canonical runtime/config inputs.

    Using the containing commit would make tracked generated output
    self-referential: committing the output changes HEAD again. Restricting the
    revision to canonical fact owners keeps `--check` reproducible while still
    identifying the source snapshot.
    """
    override = os.environ.get("BIOETL_PASSPORT_SOURCE_REVISION")
    if override:
        return override
    start_ref = (
        "HEAD^2" if os.environ.get("GITHUB_EVENT_NAME") == "pull_request" else "HEAD"
    )
    result = subprocess.run(
        [
            "git",
            "log",
            "--no-merges",
            "-1",
            "--format=%H",
            start_ref,
            "--",
            "configs/entities",
            "configs/providers",
            "configs/composites",
            "configs/workflows",
            "configs/contracts",
            "src/bioetl/composition/factories/pipeline",
            "src/bioetl/application/composite",
            "src/bioetl/application/services/workflow_runner_service.py",
            "src/bioetl/application/services/control_plane/workflow",
            "src/bioetl/application/workflow/transforms",
            "src/bioetl/infrastructure/config",
            "src/bioetl/domain/contracts",
            "src/bioetl/domain/workflow",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _contract_path(provider: str, entity: str) -> Path:
    return DEFAULT_CONFIGS_ROOT / "contracts" / provider / f"{entity}.yaml"


def _pipeline_facts(unit: ExecutableUnit, revision: str) -> JsonObject:
    payload = _load_yaml(unit.config_path)
    effective = load_effective_pipeline_facts(
        unit.unit_id,
        configs_root=DEFAULT_CONFIGS_ROOT,
    )
    pipeline = payload["pipeline"]
    assert isinstance(pipeline, dict)
    provider = unit.provider or str(
        pipeline.get("provider") or payload.get("provider") or ""
    )
    entity = unit.entity or str(
        pipeline.get("entity_type") or payload.get("entity") or ""
    )
    contract_path = _contract_path(provider, entity)
    contract = _load_yaml(contract_path) if contract_path.is_file() else {}
    source_refs = [
        {"role": "effective_entity_config", "path": _repo_path(unit.config_path)},
        {
            "role": "pipeline_registration",
            "path": "src/bioetl/composition/factories/pipeline/registry_manifest.py",
        },
        {
            "role": "run_cli",
            "path": "src/bioetl/interfaces/cli/commands/domains/run/command_entrypoint.py",
        },
        {
            "role": "quarantine_cli",
            "path": "src/bioetl/interfaces/cli/commands/quarantine.py",
        },
        {
            "role": "gold_validation_contract",
            "path": "docs/02-architecture/decisions/ADR-018-gold-strict-validation.md",
        },
        {
            "role": "observability_contract",
            "path": "src/bioetl/domain/_observability_contract_primitives.py",
        },
    ]
    if contract:
        source_refs.append({"role": "dq_contract", "path": _repo_path(contract_path)})
    provider_path = DEFAULT_CONFIGS_ROOT / "providers" / f"{provider}.yaml"
    if provider_path.is_file():
        source_refs.append(
            {"role": "provider_config", "path": _repo_path(provider_path)}
        )
    raw_schema = payload.get("schema")
    schema: JsonObject = raw_schema if isinstance(raw_schema, dict) else {}
    raw_sink = pipeline.get("sink")
    sink: JsonObject = raw_sink if isinstance(raw_sink, dict) else {}
    projection_profiles = ["batch"]
    if unit.unit_id == "chembl_target_protein_classification":
        projection_profiles.extend(["derived", "local_snapshot"])
    else:
        projection_profiles.append("http")
    if unit.unit_id == "uniprot_idmapping":
        projection_profiles.append("async_mapping")
    projection = build_ordinary_projection(
        payload,
        configs_root=DEFAULT_CONFIGS_ROOT,
        provider=provider,
        entity=entity,
    )
    facts = {
        "passport_schema_version": SCHEMA_VERSION,
        "kind": "pipeline",
        "identity": {
            "typed_id": unit.typed_id,
            "pipeline_id": unit.unit_id,
            "provider": provider,
            "entity": entity,
            "pipeline_type": "provider_entity",
            "status": "active",
            "aliases": list(unit.aliases),
            "derived_source_identity": {
                "provider": effective.get("provider"),
                "entity": effective.get("entity_type"),
                "data_source_provider": effective.get("data_source_provider"),
            },
        },
        "provenance": {
            "source_revision": revision,
            "projector_version": PIPELINE_PROJECTOR_VERSION,
            "semantic_content_hash": _sha(payload),
        },
        "source_references": source_refs,
        "summary": projection["summary"],
        "extraction": projection["extraction"],
        "bronze": {
            "capability": "append_only_snapshot",
            "content_hash": payload.get("schema", {}).get("content_hash", {})
            if isinstance(payload.get("schema"), dict)
            else {},
        },
        "silver": {
            "normalization_profile": projection["normalization_profile"],
            "column_projection": schema.get("silver", {}),
            "write": sink.get("silver", {}) if isinstance(sink, dict) else {},
            "dq_execution": {
                "strict_validation": contract.get("strict_dq_validation"),
                "soft_fail_threshold": contract.get("soft_fail_threshold"),
                "hard_fail_threshold": contract.get("hard_fail_threshold"),
                "invalid_record_policy": contract.get("invalid_record_policy"),
            },
        },
        "gold": {
            "column_projection": schema.get("gold", {}),
            "contract_ref": contract.get("contract_ref"),
            "contract_version": contract.get("contract_version"),
            "contract_validation": {
                "status": "resolved_by_adr_018",
                "strict": True,
            },
            "write": sink.get("gold", {}) if isinstance(sink, dict) else {},
        },
        "execution": {
            "projection_profiles": sorted(projection_profiles),
            "control_plane": {
                "run_manifest": True,
                "run_ledger": True,
                "checkpoints": True,
            },
            "cached_bronze_is_mode": True,
            "effective_config_hash": _sha(effective),
            "resilience": {
                "status": "runtime_resolved",
                "resolution_owner": "UnifiedHTTPClient and provider config",
                "source_refs": [
                    "src/bioetl/infrastructure/adapters/http/client.py",
                    f"configs/providers/{provider}.yaml",
                ],
            },
        },
        "operator_commands": operator_commands(unit.unit_id),
        "observability": {
            "metric_labels": ["provider", "pipeline", "run_type", "status"],
            "correlation_fields": ["run_id", "manifest_id"],
        },
        "diagnostics": [],
    }
    facts["diagrams"] = [
        {
            "diagram_id": "data_flow",
            "kind": "flowchart",
            "mermaid": ordinary_mermaid(facts),
        }
    ]
    return facts


def _composite_facts(unit: ExecutableUnit, revision: str) -> JsonObject:
    payload = _load_yaml(unit.config_path)
    composite = payload["composite"]
    assert isinstance(composite, dict)
    raw_seed = composite.get("seed")
    seed: JsonObject = raw_seed if isinstance(raw_seed, dict) else {}
    referenced_pipelines = [
        str(item["pipeline"])
        for role in ("dependencies", "enrichers")
        for item in composite.get(role, [])
        if isinstance(item, dict) and isinstance(item.get("pipeline"), str)
    ]
    pipeline_output_keys: dict[str, set[str]] = {}
    for pipeline_name in referenced_pipelines:
        effective = load_effective_pipeline_facts(
            pipeline_name,
            configs_root=DEFAULT_CONFIGS_ROOT,
        )
        data_schema = effective.get("data_schema")
        groups = (
            data_schema.get("column_groups", [])
            if isinstance(data_schema, dict)
            else []
        )
        pipeline_output_keys[pipeline_name] = {
            str(field)
            for group in groups
            if isinstance(group, dict)
            for field in group.get("fields", [])
            if isinstance(field, str)
        }
    diagnostics = validate_composite_payload(
        payload,
        pipeline_output_keys=pipeline_output_keys,
    )
    provider, entity = unit.unit_id.split("_", 1)
    contract_path = _contract_path(provider, entity)
    contract = _load_yaml(contract_path)
    entity_path = DEFAULT_CONFIGS_ROOT / "entities" / "composite" / f"{entity}.yaml"
    entity_payload = _load_yaml(entity_path)
    entity_pipeline_value = entity_payload.get("pipeline")
    entity_pipeline = (
        entity_pipeline_value if isinstance(entity_pipeline_value, dict) else {}
    )
    entity_sink_value = entity_pipeline.get("sink")
    entity_sink = entity_sink_value if isinstance(entity_sink_value, dict) else {}
    facts = {
        "passport_schema_version": SCHEMA_VERSION,
        "kind": "pipeline",
        "identity": {
            "typed_id": unit.typed_id,
            "pipeline_id": unit.unit_id,
            "provider": provider,
            "entity": entity,
            "pipeline_type": "composite",
            "status": "active",
            "aliases": list(unit.aliases),
        },
        "provenance": {
            "source_revision": revision,
            "projector_version": PIPELINE_PROJECTOR_VERSION,
            "semantic_content_hash": _sha(payload),
        },
        "source_references": [
            {"role": "composite_config", "path": _repo_path(unit.config_path)},
            {"role": "effective_entity_config", "path": _repo_path(entity_path)},
            {"role": "gold_contract", "path": _repo_path(contract_path)},
            {
                "role": "composite_cli",
                "path": "src/bioetl/interfaces/cli/commands/run_composite.py",
            },
            {
                "role": "quarantine_cli",
                "path": "src/bioetl/interfaces/cli/commands/quarantine.py",
            },
        ],
        "summary": {
            "sentences": [
                (
                    f"Composite pipeline `{unit.unit_id}` использует seed "
                    f"`{seed.get('pipeline')}` и объединяет его с configured "
                    "dependencies/enrichers."
                ),
                (
                    "Join keys, cardinality и source tables берутся из composite "
                    "configuration; merge и conflict resolution выполняются общей "
                    "CompositePipelineRunner."
                ),
                (
                    "После merge применяется configured cross-validation; "
                    "исключённые значения направляются в quarantine или nullification "
                    "branch согласно composite policy."
                ),
                (
                    f"Результат проходит строгий Gold-контракт `{provider}.{entity}` "
                    "и публикует manifest/checkpoint evidence."
                ),
            ],
            "source_description": f"seed={seed.get('pipeline')}",
            "query_filter_summary": "composite join/filter conditions",
            "field_selection_summary": "seed outputs plus configured enrichers",
            "silver_processing_summary": "composite merge",
            "validation_summary": "cross-validation and strict Gold contract",
            "excluded_data_summary": "quarantine/nullification per composite policy",
        },
        "extraction": {
            "source_kind": "composite",
            "source_resource": seed.get("pipeline"),
            "method": None,
            "endpoint_template": None,
            "source_tables": [
                str(item.get("silver_table"))
                for item in [
                    seed,
                    *[
                        row
                        for role in ("dependencies", "enrichers")
                        for row in composite.get(role, [])
                        if isinstance(row, dict)
                    ],
                ]
                if item.get("silver_table")
            ],
            "source_collections": [],
            "filters": [
                {
                    "name": str(item.get("pipeline")),
                    "source": "dependency",
                    "required": bool(item.get("required")),
                    "description": str(item.get("filter_condition") or "no condition"),
                }
                for role in ("dependencies", "enrichers")
                for item in composite.get(role, [])
                if isinstance(item, dict)
            ],
            "selected_fields": [],
            "field_groups": [],
        },
        "composite": {
            "version": composite.get("version"),
            "seed": seed,
            "dependencies": composite.get("dependencies", []),
            "enrichers": composite.get("enrichers", []),
            "merge": composite.get("merge", {}),
            "cross_validation": composite.get("cross_validation", {}),
            "execution": composite.get("execution", {}),
            "invariants": {
                "join_keys_must_exist_in_seed_or_prior_key_source_output": True,
                "supported_cardinalities": ["one_to_one", "many_to_one"],
                "aggregation_is_explicit": True,
                "conflict_priorities_are_complete": True,
            },
        },
        "silver": {
            "normalization_profile": f"composite.{entity}",
            "write": entity_sink.get("silver", {}),
            "dq_execution": {
                "strict_validation": contract.get("strict_dq_validation"),
                "soft_fail_threshold": contract.get("soft_fail_threshold"),
                "hard_fail_threshold": contract.get("hard_fail_threshold"),
                "invalid_record_policy": contract.get("invalid_record_policy"),
            },
        },
        "gold": {
            "contract_ref": contract.get("contract_ref"),
            "contract_version": contract.get("contract_version"),
            "contract_validation": {"status": "resolved_by_adr_018", "strict": True},
            "write": entity_sink.get("gold", {}),
        },
        "execution": {"control_plane": {"run_manifest": True, "checkpoints": True}},
        "operator_commands": operator_commands(unit.unit_id, composite=True),
        "observability": {
            "metric_labels": ["pipeline", "run_type", "status"],
            "correlation_fields": ["run_id", "manifest_id"],
        },
        "diagnostics": diagnostics,
    }
    facts["diagrams"] = [
        {
            "diagram_id": "composite_flow",
            "kind": "flowchart",
            "mermaid": composite_mermaid(facts),
        }
    ]
    return facts


def _classify_transform(name: str) -> list[str]:
    if name == "reconcile_foreign_keys":
        return ["data_plane_transformation", "dq_validation", "destructive_mutation"]
    if name == "summarize_upstream_outputs":
        return ["control_plane_projection"]
    return ["unknown"]


def _workflow_facts(unit: ExecutableUnit, revision: str) -> JsonObject:
    payload = _load_yaml(unit.config_path)
    workflow = payload["workflow"]
    assert isinstance(workflow, dict)
    raw_steps = workflow.get("steps", [])
    steps = [step for step in raw_steps if isinstance(step, dict)]
    domain_workflow = load_workflow_config(
        unit.unit_id,
        config_dir=unit.config_path.parent,
    )
    edges = sorted(
        (str(dep), str(step.get("step_id")))
        for step in steps
        for dep in step.get("depends_on", [])
        if isinstance(dep, str)
    )
    operations = []
    diagnostics = []
    for step in steps:
        if step.get("kind") != "transform":
            continue
        transform_name = str(step.get("transform_name"))
        classification = _classify_transform(transform_name)
        operation = {
            "step_id": step.get("step_id"),
            "transform_name": transform_name,
            "classification": classification,
            "config": step.get("config", {}),
        }
        operations.append(operation)
        if classification == ["unknown"]:
            diagnostics.append(
                {
                    "code": "WORKFLOW_TRANSFORM_CLASSIFICATION_UNKNOWN",
                    "severity": "error",
                    "step_id": step.get("step_id"),
                }
            )
    return {
        "passport_schema_version": SCHEMA_VERSION,
        "kind": "workflow",
        "identity": {
            "typed_id": unit.typed_id,
            "workflow_id": unit.unit_id,
            "version": workflow.get("version"),
            "status": "active",
        },
        "provenance": {
            "source_revision": revision,
            "projector_version": PROJECTOR_VERSION,
            "semantic_content_hash": _sha(payload),
        },
        "source_references": [
            {"role": "workflow_config", "path": _repo_path(unit.config_path)},
            {
                "role": "workflow_control_plane",
                "path": "docs/02-architecture/decisions/ADR-047-workflow-control-plane.md",
            },
        ],
        "dag": {
            "step_count": len(steps),
            "edge_count": len(edges),
            "topological_order": list(domain_workflow.topological_step_ids),
            "steps": steps,
            "edges": [{"from": source, "to": target} for source, target in edges],
            "mermaid": workflow_mermaid(steps),
        },
        "external_data_operations": operations,
        "control_plane": {
            "workflow_manifest": True,
            "run_ledger_links": True,
            "resume_last": True,
            "repair_steps": True,
            "force_steps": True,
            "exclusive_lock": True,
            "commit_pending_confirmation": True,
        },
        "observability": {
            "metric_labels": [
                "workflow",
                "pipeline",
                "step_kind",
                "status",
                "run_type",
            ],
            "prohibited_metric_labels": [
                "run_id",
                "manifest_id",
                "workflow_run_id",
                "payload_hash",
                "record_id",
            ],
            "correlation_fields": ["run_id", "manifest_id", "workflow_run_id"],
        },
        "diagnostics": diagnostics,
    }


def _facts(unit: ExecutableUnit, revision: str) -> JsonObject:
    if unit.kind == "pipeline":
        return _pipeline_facts(unit, revision)
    if unit.kind == "composite":
        return _composite_facts(unit, revision)
    return _workflow_facts(unit, revision)


def _append_diagnostics(
    lines: list[str], diagnostics: object, *, empty_message: bool = False
) -> None:
    if isinstance(diagnostics, list) and diagnostics:
        for diagnostic in diagnostics:
            if isinstance(diagnostic, dict):
                lines.append(f"- `{diagnostic['severity']}` `{diagnostic['code']}`")
        return
    if empty_message:
        lines.append("- No blocking diagnostics.")


def _append_manual_context(lines: list[str], manual: dict[str, object]) -> None:
    if not manual:
        return
    lines.extend(["", "## Owner-approved context", ""])
    lines.append(f"- Owner: `{manual['owner']}`")
    for key in ("purpose", "business_context", "rationale"):
        value = manual.get(key)
        if isinstance(value, str) and value:
            lines.extend(["", f"### {key.replace('_', ' ').title()}", "", value])
    limitations = manual.get("known_limitations")
    if isinstance(limitations, list) and limitations:
        lines.extend(["", "### Known limitations", ""])
        lines.extend(f"- {item}" for item in limitations)


def _render_markdown(facts: JsonObject, manual: dict[str, object]) -> str:
    identity = facts["identity"]
    assert isinstance(identity, dict)
    name = str(identity.get("pipeline_id") or identity.get("workflow_id"))
    kind = str(facts["kind"])
    diagnostics = facts.get("diagnostics", [])
    refs = facts.get("source_references", [])
    if kind == "pipeline":
        return _render_pipeline_markdown(facts, manual)
    lines = [
        f"# {name} passport",
        "",
        "> Generated documentation projection. Do not edit manually.",
        "",
        f"- Kind: `{kind}`",
        f"- Typed identity: `{identity['typed_id']}`",
        f"- Schema: `{facts['passport_schema_version']}`",
        f"- Source revision: `{facts['provenance']['source_revision']}`",
        "",
        "## Evidence",
        "",
    ]
    for ref in refs:
        lines.append(f"- `{ref['role']}`: `{ref['path']}`")
    lines.extend(["", "## Generated facts", "", "```json"])
    lines.extend(_canonical_bytes(facts).decode("utf-8").rstrip().splitlines())
    lines.extend(["```", "", "## Diagnostics", ""])
    _append_diagnostics(lines, diagnostics, empty_message=True)
    _append_manual_context(lines, manual)
    lines.append("")
    return "\n".join(lines)


def _inline(value: object) -> str:
    if value is None or value == "" or value == []:
        return "—"
    if isinstance(value, list):
        return ", ".join(f"`{item}`" for item in value)
    if isinstance(value, dict):
        return "; ".join(f"{key}={item}" for key, item in sorted(value.items()))
    return f"`{value}`"


def _pipeline_extraction_lines(extraction: JsonObject) -> list[str]:
    filters = extraction.get("filters", [])
    filter_text = (
        "; ".join(
            f"`{item['name']}`: {item['description']}"
            for item in filters
            if isinstance(item, dict)
        )
        or "Нет статических filters; используется effective runtime scope"
    )
    lines = [
        "",
        "## Извлечение данных",
        "",
        "| Аспект | Значение |",
        "| --- | --- |",
        f"| Source | `{extraction.get('source_kind')}` · `{extraction.get('source_resource')}` |",
        (
            "| Method / endpoint | "
            f"{_inline(extraction.get('method'))} · "
            f"{_inline(extraction.get('endpoint_template'))} |"
        ),
        (
            "| Resource / tables | "
            f"{_inline([*extraction.get('source_tables', []), *extraction.get('source_collections', [])])} |"
        ),
        f"| Filters | {filter_text} |",
    ]
    groups = extraction.get("field_groups", [])
    if groups:
        lines.append(
            "| Selected fields | "
            + "; ".join(
                f"`{item['name']}` ({item['field_count']} fields)" for item in groups
            )
            + " |"
        )
    return lines


def _append_silver_and_gold(
    lines: list[str], *, silver: JsonObject, gold: JsonObject, contract_label: str
) -> None:
    lines.extend(["", "## Silver и Data Quality", ""])
    if silver:
        dq = silver.get("dq_execution", {})
        lines.extend(
            [
                f"- Normalization profile: `{silver.get('normalization_profile')}`.",
                f"- Partitioning: {_inline(silver.get('write', {}).get('partition_by'))}.",
                (
                    "- DQ thresholds: "
                    f"soft `{dq.get('soft_fail_threshold')}`, "
                    f"hard `{dq.get('hard_fail_threshold')}`; "
                    f"invalid policy `{dq.get('invalid_record_policy')}`."
                ),
            ]
        )
    else:
        lines.append(
            "- Composite Silver inputs and merge rules are listed in generated JSON."
        )
    lines.extend(["", "## Gold", ""])
    validation = gold.get("contract_validation", {})
    write = gold.get("write", {})
    lines.extend(
        [
            f"- Contract: `{contract_label}`; strict validation: `{validation.get('strict', True)}`.",
            f"- Write mode: `{write.get('mode', 'configured')}`.",
        ]
    )
    if write.get("scd_config"):
        lines.append(f"- SCD2: {_inline(write['scd_config'])}.")
    exclusions = gold.get("column_projection", {}).get("exclude_fields", [])
    if exclusions:
        lines.append(f"- Technical exclusions: {_inline(exclusions)}.")


def _append_commands_and_diagrams(lines: list[str], facts: JsonObject) -> None:
    lines.extend(
        [
            "",
            "## Операторские команды",
            "",
            "| Задача | Команда | Результат |",
            "| --- | --- | --- |",
        ]
    )
    for item in facts["operator_commands"]:
        lines.append(f"| {item['task']} | `{item['command']}` | {item['result']} |")
    lines.extend(["", "## Диаграммы", ""])
    for diagram in facts["diagrams"]:
        lines.extend(
            [
                f"### {diagram['diagram_id'].replace('_', ' ').title()}",
                "",
                "```mermaid",
                str(diagram["mermaid"]),
                "```",
                "",
            ]
        )


def _append_pipeline_tail(
    lines: list[str],
    *,
    facts: JsonObject,
    manual: dict[str, object],
    diagnostics: object,
) -> None:
    purpose = manual.get("purpose") if manual else None
    if isinstance(purpose, str) and purpose:
        lines.extend(["## Owner-approved context", "", purpose, ""])
    lines.extend(["## Evidence", ""])
    for ref in facts["source_references"]:
        lines.append(f"- `{ref['role']}`: `{ref['path']}`")
    if diagnostics:
        lines.extend(["", "## Diagnostics", ""])
        _append_diagnostics(lines, diagnostics)
    lines.append("")


def _render_pipeline_markdown(facts: JsonObject, manual: dict[str, object]) -> str:
    """Render the compact human view; complete facts remain in generated JSON."""
    identity = facts["identity"]
    summary = facts["summary"]
    extraction = facts["extraction"]
    silver = facts.get("silver", {})
    gold = facts.get("gold", {})
    diagnostics = facts.get("diagnostics", [])
    pipeline_id = str(identity["pipeline_id"])
    pipeline_type = str(identity["pipeline_type"])
    contract = gold.get("contract_ref") or pipeline_id
    contract_version = gold.get("contract_version")
    contract_label = (
        f"{contract} v{contract_version}" if contract_version else str(contract)
    )
    lines = [
        f"# `{pipeline_id}`",
        "",
        "> Generated documentation projection. Do not edit manually.",
        "",
        "## Обзор",
        "",
        "| Параметр | Значение |",
        "| --- | --- |",
        (f"| Typed identity `[type:{pipeline_type}]` | `{identity['typed_id']}` |"),
        f"| Status | `{identity['status']}` |",
        f"| Gold contract | `{contract_label}` |",
    ]
    aliases = identity.get("aliases", [])
    if aliases:
        lines.append(f"| Aliases | {_inline(aliases)} |")
    lines.extend(["", "## Назначение и обработка данных", ""])
    lines.extend(str(sentence) for sentence in summary["sentences"])
    lines.extend(_pipeline_extraction_lines(extraction))
    _append_silver_and_gold(
        lines, silver=silver, gold=gold, contract_label=contract_label
    )
    _append_commands_and_diagrams(lines, facts)
    _append_pipeline_tail(lines, facts=facts, manual=manual, diagnostics=diagnostics)
    return "\n".join(lines)


def _unit_projection(
    unit: ExecutableUnit,
    *,
    revision: str,
    sidecar_root: Path,
    output_root: Path,
) -> tuple[dict[Path, bytes], dict[str, object], int]:
    facts = _facts(unit, revision)
    errors = [
        item for item in facts.get("diagnostics", []) if item.get("severity") == "error"
    ]
    group = "workflows" if unit.kind == "workflow" else "pipelines"
    manual = load_manual_sidecar(sidecar_root / group / f"{unit.unit_id}.yaml")
    markdown = _render_markdown(facts, manual)
    if facts["kind"] == "pipeline":
        publication_errors = validate_pipeline_publication(
            facts,
            markdown,
            project_root=PROJECT_ROOT,
        )
        if publication_errors:
            raise ValueError(
                f"Invalid pipeline passport {unit.unit_id}: "
                + "; ".join(publication_errors)
            )
    markdown_filename = passport_markdown_filename(unit.unit_id)
    outputs = {
        output_root / "generated" / group / f"{unit.unit_id}.json": _canonical_bytes(
            facts
        ),
        output_root / group / markdown_filename: markdown.encode("utf-8"),
    }
    registry_row: dict[str, object] = {
        "typed_id": unit.typed_id,
        "aliases": list(unit.aliases),
        "config_path": _repo_path(unit.config_path),
        "passport_path": f"{group}/{markdown_filename}",
    }
    return outputs, registry_row, len(errors)


def _passport_index(registry_rows: list[dict[str, object]]) -> bytes:
    index = [
        "# Pipeline and workflow passports",
        "",
        "Generated, evidence-backed documentation projections.",
        "",
        "## Governance",
        "",
        "- [Pipeline passport projection guide](pipeline-passport-guide.md)",
        "- [ADR-054: passport documentation projections](../../02-architecture/decisions/ADR-054-passport-documentation-projections.md)",
        "- [ADR-055: workflow reconciliation ownership](../../02-architecture/decisions/ADR-055-workflow-reconciliation-data-step-ownership.md)",
        "- [Pipeline passport schema](schemas/pipeline-passport.schema.json)",
        "- [Workflow passport schema](schemas/workflow-passport.schema.json)",
        "- [Manual metadata schema](schemas/manual-passport-metadata.schema.json)",
        "- [Normalized duplication report](duplication-report.json)",
        "",
        "- Owner: `BioETL Team`; review cadence: each executable/config change and release.",
        "- Check: `python -m scripts.docs passports check`.",
        "- Reviewed update: `python -m scripts.docs passports generate`.",
        "- Generated facts are read-only projections; manual sidecars cannot override them.",
        "- Diagram dataflow passports are compatibility companions and link back here.",
        "",
        "## Pipelines",
        "",
    ]
    for row in registry_rows:
        typed_id = str(row["typed_id"])
        if not typed_id.startswith("workflow:"):
            name = typed_id.split(":", 1)[1]
            index.append(f"- [{name}](pipelines/{passport_markdown_filename(name)})")
    index.extend(["", "## Workflows", ""])
    for row in registry_rows:
        typed_id = str(row["typed_id"])
        if typed_id.startswith("workflow:"):
            name = typed_id.split(":", 1)[1]
            index.append(f"- [{name}](workflows/{passport_markdown_filename(name)})")
    index.append("")
    return "\n".join(index).encode("utf-8")


def build_all_outputs(
    *,
    configs_root: Path = DEFAULT_CONFIGS_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    source_revision: str | None = None,
    manual_root: Path | None = None,
) -> dict[Path, bytes]:
    """Build all registry, facts, Markdown, and completeness outputs."""
    revision = source_revision or _source_revision()
    units = discover_units(configs_root)
    sidecar_root = manual_root or output_root / "manual"
    outputs: dict[Path, bytes] = {}
    registry_rows = []
    error_count = 0
    for unit in units:
        unit_outputs, registry_row, unit_error_count = _unit_projection(
            unit,
            revision=revision,
            sidecar_root=sidecar_root,
            output_root=output_root,
        )
        outputs.update(unit_outputs)
        registry_rows.append(registry_row)
        error_count += unit_error_count
    report = {
        "passport_schema_version": SCHEMA_VERSION,
        "source_revision": revision,
        "counts": {
            "pipeline": sum(item.kind == "pipeline" for item in units),
            "composite": sum(item.kind == "composite" for item in units),
            "workflow": sum(item.kind == "workflow" for item in units),
            "total": len(units),
        },
        "orphan_passports": [],
        "duplicate_typed_identities": [],
        "unresolved_aliases": [],
        "registry_config_mismatches": [],
        "blocking_diagnostics": error_count,
    }
    outputs[output_root / "executable-unit-registry.json"] = _canonical_bytes(
        {"units": registry_rows}
    )
    outputs[output_root / "completeness-report.json"] = _canonical_bytes(report)
    pipeline_markdown = [
        content.decode("utf-8")
        for path, content in outputs.items()
        if path.parent == output_root / "pipelines" and path.suffix == ".md"
    ]
    outputs[output_root / "duplication-report.json"] = _canonical_bytes(
        {
            "method": "normalized Markdown lines, paragraphs, diagrams, and identity labels",
            "before": _DUPLICATION_BASELINE,
            "after": audit_markdown_texts(pipeline_markdown),
        }
    )
    outputs[output_root / "index.md"] = _passport_index(registry_rows)
    return outputs


def check_outputs(outputs: dict[Path, bytes]) -> list[Path]:
    """Return missing or stale paths."""
    return [
        path
        for path, expected in outputs.items()
        if not path.is_file() or path.read_bytes() != expected
    ]


def write_outputs(outputs: dict[Path, bytes]) -> None:
    """Atomically write generated outputs."""
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=path.parent
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        except BaseException:
            Path(temp_name).unlink(missing_ok=True)
            raise
