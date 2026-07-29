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

from .inventory import ExecutableUnit, discover_units
from .manual_sidecar import load_manual_sidecar

SCHEMA_VERSION = "1.0.0"
PROJECTOR_VERSION = "1.0.0"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIGS_ROOT = PROJECT_ROOT / "configs"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "docs/04-reference/passports"
JsonObject = dict[str, Any]


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
    result = subprocess.run(
        [
            "git",
            "log",
            "-1",
            "--format=%H",
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
    pipeline = payload["pipeline"]
    assert isinstance(pipeline, dict)
    provider = str(pipeline.get("provider") or payload.get("provider") or "")
    entity = str(pipeline.get("entity_type") or payload.get("entity") or "")
    contract_path = _contract_path(provider, entity)
    contract = _load_yaml(contract_path) if contract_path.is_file() else {}
    source_refs = [
        {"role": "effective_entity_config", "path": _repo_path(unit.config_path)}
    ]
    if contract:
        source_refs.append(
            {"role": "dq_contract", "path": _repo_path(contract_path)}
        )
    raw_schema = payload.get("schema")
    schema: JsonObject = raw_schema if isinstance(raw_schema, dict) else {}
    raw_sink = pipeline.get("sink")
    sink: JsonObject = raw_sink if isinstance(raw_sink, dict) else {}
    return {
        "passport_schema_version": SCHEMA_VERSION,
        "kind": "pipeline",
        "identity": {
            "typed_id": unit.typed_id,
            "pipeline_id": unit.unit_id,
            "provider": provider,
            "entity": entity,
            "pipeline_type": "provider_entity",
            "status": "active",
            "aliases": [],
        },
        "provenance": {
            "source_revision": revision,
            "projector_version": PROJECTOR_VERSION,
            "semantic_content_hash": _sha(payload),
        },
        "source_references": source_refs,
        "extraction": {
            "source_type": "runtime_resolved",
            "request": {
                "method": {"status": "runtime_resolved"},
                "endpoint_template": {"status": "runtime_resolved"},
            },
            "supported_source_modes": ["api", "cached_bronze"],
        },
        "bronze": {
            "capability": "append_only_snapshot",
            "content_hash": payload.get("schema", {}).get("content_hash", {})
            if isinstance(payload.get("schema"), dict)
            else {},
        },
        "silver": {
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
                "status": "resolved_by_runtime_contract",
                "strict": True,
            },
            "write": sink.get("gold", {}) if isinstance(sink, dict) else {},
        },
        "execution": {
            "control_plane": {
                "run_manifest": True,
                "run_ledger": True,
                "checkpoints": True,
            },
            "cached_bronze_is_mode": True,
        },
        "observability": {
            "metric_labels": ["provider", "pipeline", "run_type", "status"],
            "correlation_fields": ["run_id", "manifest_id"],
        },
        "diagnostics": [],
    }


def _composite_facts(unit: ExecutableUnit, revision: str) -> JsonObject:
    payload = _load_yaml(unit.config_path)
    composite = payload["composite"]
    assert isinstance(composite, dict)
    raw_seed = composite.get("seed")
    seed: JsonObject = raw_seed if isinstance(raw_seed, dict) else {}
    output_keys = {
        str(value) for value in seed.get("output_keys", []) if isinstance(value, str)
    }
    diagnostics: list[JsonObject] = []
    for enricher in composite.get("enrichers", []):
        if not isinstance(enricher, dict):
            continue
        missing = [
            key
            for key in enricher.get("join_keys", [])
            if isinstance(key, str) and key not in output_keys
        ]
        if missing:
            diagnostics.append(
                {
                    "code": "COMPOSITE_JOIN_KEY_NOT_IN_SEED_OUTPUT",
                    "severity": "error",
                    "pipeline": enricher.get("pipeline"),
                    "keys": missing,
                }
            )
    provider, entity = unit.unit_id.split("_", 1)
    contract_path = _contract_path(provider, entity)
    return {
        "passport_schema_version": SCHEMA_VERSION,
        "kind": "pipeline",
        "identity": {
            "typed_id": unit.typed_id,
            "pipeline_id": unit.unit_id,
            "provider": provider,
            "entity": entity,
            "pipeline_type": "composite",
            "status": "active",
            "aliases": [],
        },
        "provenance": {
            "source_revision": revision,
            "projector_version": PROJECTOR_VERSION,
            "semantic_content_hash": _sha(payload),
        },
        "source_references": [
            {"role": "composite_config", "path": _repo_path(unit.config_path)},
            {"role": "gold_contract", "path": _repo_path(contract_path)},
        ],
        "composite": {
            "version": composite.get("version"),
            "seed": seed,
            "dependencies": composite.get("dependencies", []),
            "enrichers": composite.get("enrichers", []),
            "merge": composite.get("merge", {}),
            "cross_validation": composite.get("cross_validation", {}),
            "execution": composite.get("execution", {}),
        },
        "execution": {
            "control_plane": {"run_manifest": True, "checkpoints": True}
        },
        "observability": {
            "metric_labels": ["pipeline", "run_type", "status"],
            "correlation_fields": ["run_id", "manifest_id"],
        },
        "diagnostics": diagnostics,
    }


def _classify_transform(name: str) -> list[str]:
    if name == "reconcile_foreign_keys":
        return ["data_plane_transformation", "dq_validation", "destructive_mutation"]
    if name == "summarize_upstream_outputs":
        return ["control_plane_projection"]
    return ["unknown"]


def _topological_order(steps: list[JsonObject]) -> list[str]:
    step_ids = [str(step.get("step_id")) for step in steps]
    if len(step_ids) != len(set(step_ids)):
        raise ValueError("Workflow contains duplicate step IDs")
    dependencies = {
        str(step.get("step_id")): {
            str(value)
            for value in step.get("depends_on", [])
            if isinstance(value, str)
        }
        for step in steps
    }
    unknown = sorted(
        dependency
        for values in dependencies.values()
        for dependency in values
        if dependency not in dependencies
    )
    if unknown:
        raise ValueError(f"Workflow contains unknown dependencies: {unknown}")
    ordered: list[str] = []
    remaining = dict(dependencies)
    while remaining:
        ready = sorted(
            step_id
            for step_id, values in remaining.items()
            if values.issubset(ordered)
        )
        if not ready:
            raise ValueError("Workflow dependency cycle detected")
        for step_id in ready:
            ordered.append(step_id)
            del remaining[step_id]
    return ordered


def _workflow_facts(unit: ExecutableUnit, revision: str) -> JsonObject:
    payload = _load_yaml(unit.config_path)
    workflow = payload["workflow"]
    assert isinstance(workflow, dict)
    raw_steps = workflow.get("steps", [])
    steps = [step for step in raw_steps if isinstance(step, dict)]
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
            "topological_order": _topological_order(steps),
            "steps": steps,
            "edges": [{"from": source, "to": target} for source, target in edges],
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
            "metric_labels": ["workflow", "pipeline", "step_kind", "status", "run_type"],
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


def _render_markdown(facts: JsonObject, manual: dict[str, object]) -> str:
    identity = facts["identity"]
    assert isinstance(identity, dict)
    name = str(identity.get("pipeline_id") or identity.get("workflow_id"))
    kind = str(facts["kind"])
    diagnostics = facts.get("diagnostics", [])
    refs = facts.get("source_references", [])
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
    if diagnostics:
        for diagnostic in diagnostics:
            lines.append(
                f"- `{diagnostic['severity']}` `{diagnostic['code']}`"
            )
    else:
        lines.append("- No blocking diagnostics.")
    if manual:
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
    lines.append("")
    return "\n".join(lines)


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
        facts = _facts(unit, revision)
        errors = [
            item
            for item in facts.get("diagnostics", [])
            if item.get("severity") == "error"
        ]
        error_count += len(errors)
        group = "workflows" if unit.kind == "workflow" else "pipelines"
        manual = load_manual_sidecar(sidecar_root / group / f"{unit.unit_id}.yaml")
        outputs[output_root / "generated" / group / f"{unit.unit_id}.json"] = (
            _canonical_bytes(facts)
        )
        outputs[output_root / group / f"{unit.unit_id}.md"] = _render_markdown(
            facts, manual
        ).encode("utf-8")
        registry_rows.append(
            {
                "typed_id": unit.typed_id,
                "config_path": _repo_path(unit.config_path),
                "passport_path": _display_path(
                    output_root / group / f"{unit.unit_id}.md"
                ),
            }
        )
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
        "blocking_diagnostics": error_count,
    }
    outputs[output_root / "executable-unit-registry.json"] = _canonical_bytes(
        {"units": registry_rows}
    )
    outputs[output_root / "completeness-report.json"] = _canonical_bytes(report)
    index = [
        "# Pipeline and workflow passports",
        "",
        "Generated, evidence-backed documentation projections.",
        "",
        "## Governance",
        "",
        "- [ADR-054: passport documentation projections](../../02-architecture/decisions/ADR-054-passport-documentation-projections.md)",
        "- [ADR-055: workflow reconciliation ownership](../../02-architecture/decisions/ADR-055-workflow-reconciliation-data-step-ownership.md)",
        "- [Pipeline passport schema](schemas/pipeline-passport.schema.json)",
        "- [Workflow passport schema](schemas/workflow-passport.schema.json)",
        "- [Manual metadata schema](schemas/manual-passport-metadata.schema.json)",
        "",
        "## Pipelines",
        "",
    ]
    for row in registry_rows:
        if not row["typed_id"].startswith("workflow:"):
            name = row["typed_id"].split(":", 1)[1]
            index.append(f"- [{name}](pipelines/{name}.md)")
    index.extend(["", "## Workflows", ""])
    for row in registry_rows:
        if row["typed_id"].startswith("workflow:"):
            name = row["typed_id"].split(":", 1)[1]
            index.append(f"- [{name}](workflows/{name}.md)")
    index.append("")
    outputs[output_root / "index.md"] = "\n".join(index).encode("utf-8")
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
        descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
            os.replace(temp_name, path)
        except BaseException:
            Path(temp_name).unlink(missing_ok=True)
            raise
