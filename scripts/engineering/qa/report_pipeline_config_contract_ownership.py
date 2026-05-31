#!/usr/bin/env python3
"""Generate deterministic pipeline-config-contract ownership traces."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "pipeline-config-contract-ownership-map.json"
)
DEFAULT_MD_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "pipeline-config-contract-ownership-map.md"
)
CONTRACT_REGISTRY_PATH = PROJECT_ROOT / "configs" / "base" / "contract_registry.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Expected mapping in {path.as_posix()}"
        raise TypeError(msg)
    return payload


_COMPOSITE_PIPELINE_OWNER = (
    "src/bioetl/application/composite/runner_pkg/runner.py"
)
_PIPELINE_OWNER_OVERRIDES: dict[tuple[str, str], str] = {
    ("uniprot", "idmapping"): (
        "src/bioetl/application/pipelines/uniprot/idmapping_transformer.py"
    ),
    ("uniprot", "protein"): "src/bioetl/application/pipelines/uniprot/transformer.py",
}
_PUBLICATION_PROVIDERS = frozenset(
    {"crossref", "openalex", "pubmed", "semanticscholar", "pubchem"}
)


def _pipeline_owner(provider: str, entity: str, _pipeline_name: str) -> str:
    if provider == "composite":
        return _COMPOSITE_PIPELINE_OWNER
    override = _PIPELINE_OWNER_OVERRIDES.get((provider, entity))
    if override is not None:
        return override
    if provider == "chembl":
        return f"src/bioetl/application/pipelines/chembl/{entity}_transformer.py"
    if provider in _PUBLICATION_PROVIDERS:
        return f"src/bioetl/application/pipelines/{provider}/transformer.py"
    return f"src/bioetl/application/pipelines/{provider}/{entity}.py"


def _gold_runtime_enabled(pipeline: dict[str, Any]) -> bool:
    sink = pipeline.get("sink")
    if not isinstance(sink, dict):
        return False
    gold = sink.get("gold")
    if not isinstance(gold, dict):
        return False
    enabled = gold.get("enabled")
    if enabled is None:
        return True
    return bool(enabled)


def _repo_relative_registry_path(raw_path: object) -> str:
    if not isinstance(raw_path, str) or not raw_path:
        return ""
    candidate = Path(raw_path)
    resolved = (
        candidate.resolve()
        if candidate.is_absolute()
        else (CONTRACT_REGISTRY_PATH.parent / candidate).resolve()
    )
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _first_published_artifact(registry_entry: dict[str, Any] | None) -> str:
    if registry_entry is None:
        return ""
    artifacts = registry_entry.get("published_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return ""
    return _repo_relative_registry_path(artifacts[0])


def _gold_schema_title(published_artifact_path: str) -> str:
    if not published_artifact_path:
        return ""
    artifact_path = PROJECT_ROOT / published_artifact_path
    if not artifact_path.is_file():
        return ""
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    title = payload.get("title") if isinstance(payload, dict) else None
    return title if isinstance(title, str) else ""


def _registry_contract_version(registry_entry: dict[str, Any] | None) -> str:
    if registry_entry is None:
        return ""
    identity = registry_entry.get("identity")
    if not isinstance(identity, dict):
        return ""
    version = identity.get("contract_version")
    return version if isinstance(version, str) else ""


def _coverage_status(
    *,
    gold_enabled: bool,
    registry_entry: dict[str, Any] | None,
    contract_config_path: str,
    published_artifact_path: str,
    registry_source_path: str,
    gold_schema_title: str,
) -> str:
    if not gold_enabled:
        return "excluded_non_gold"
    if registry_entry is None:
        return "missing_registry_entry"
    if registry_entry.get("status") != "active":
        return "registry_not_active"
    required_paths = (contract_config_path, published_artifact_path, registry_source_path)
    if not all(required_paths):
        return "missing_governance_path"
    if not all((PROJECT_ROOT / path).is_file() for path in required_paths):
        return "missing_governance_file"
    if not gold_schema_title:
        return "missing_gold_schema_title"
    return "covered"


def _load_registry_entries() -> dict[str, dict[str, Any]]:
    payload = _load_yaml(CONTRACT_REGISTRY_PATH)
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        return {}
    return {
        str(contract_ref): entry
        for contract_ref, entry in entries.items()
        if isinstance(entry, dict)
    }


def _gold_exclusion_reason(pipeline: dict[str, Any]) -> str:
    sink = pipeline.get("sink")
    if not isinstance(sink, dict):
        return ""
    gold = sink.get("gold")
    if not isinstance(gold, dict):
        return ""
    reason = gold.get("exclusion_reason")
    return reason if isinstance(reason, str) else ""


def _collect_entity_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    entities_root = PROJECT_ROOT / "configs" / "entities"
    registry_entries = _load_registry_entries()
    for config_path in sorted(entities_root.glob("*/*.yaml")):
        payload = _load_yaml(config_path)
        provider = str(payload.get("provider") or config_path.parent.name)
        entity = str(payload.get("entity") or config_path.stem)
        pipeline = payload.get("pipeline", {})
        assert isinstance(pipeline, dict)
        pipeline_name = str(pipeline.get("pipeline_name") or f"{provider}_{entity}")
        sink = pipeline.get("sink", {})
        gold_enabled = _gold_runtime_enabled(pipeline)
        contract_ref = f"{provider}.{entity}"
        contract_config = (
            PROJECT_ROOT / "configs" / "contracts" / provider / f"{entity}.yaml"
        )
        composite_runtime_config = (
            PROJECT_ROOT / "configs" / "composites" / f"{entity}.yaml"
        )
        registry_entry = registry_entries.get(contract_ref)
        registry_source_path = _repo_relative_registry_path(
            registry_entry.get("source_path") if registry_entry is not None else ""
        )
        published_artifact_path = _first_published_artifact(registry_entry)
        gold_schema_title = _gold_schema_title(published_artifact_path)
        contract_config_path = (
            contract_config.relative_to(PROJECT_ROOT).as_posix()
            if contract_config.exists()
            else ""
        )
        row: dict[str, Any] = {
            "pipeline_name": pipeline_name,
            "provider": provider,
            "entity": entity,
            "contract_ref": contract_ref,
            "config_path": config_path.relative_to(PROJECT_ROOT).as_posix(),
            "contract_config_path": contract_config_path,
            "registry_status": (
                str(registry_entry.get("status")) if registry_entry is not None else ""
            ),
            "registry_contract_version": _registry_contract_version(registry_entry),
            "registry_source_path": registry_source_path,
            "published_artifact_path": published_artifact_path,
            "gold_schema_title": gold_schema_title,
            "pipeline_code_owner": _pipeline_owner(provider, entity, pipeline_name),
            "gold_enabled": gold_enabled,
            "gold_exclusion_reason": _gold_exclusion_reason(pipeline),
        }
        row["coverage_status"] = _coverage_status(
            gold_enabled=gold_enabled,
            registry_entry=registry_entry,
            contract_config_path=contract_config_path,
            published_artifact_path=published_artifact_path,
            registry_source_path=registry_source_path,
            gold_schema_title=gold_schema_title,
        )
        if provider == "composite":
            row["composite_runtime_config_path"] = (
                composite_runtime_config.relative_to(PROJECT_ROOT).as_posix()
                if composite_runtime_config.exists()
                else ""
            )
        rows.append(row)
    return rows


def _render_markdown(rows: list[dict[str, str | bool]]) -> str:
    lines = [
        "# Pipeline Config Contract Ownership Map",
        "",
        f"- snapshot_date: {date.today().isoformat()}",
        f"- row_count: {len(rows)}",
        "",
        "| pipeline_name | contract_ref | config_path | registry_status | "
        "contract_config_path | published_artifact_path | gold_schema_title | "
        "pipeline_code_owner | gold_enabled | coverage_status |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| `{pipeline_name}` | `{contract_ref}` | `{config_path}` | "
            "`{registry_status}` | `{contract_config_path}` | "
            "`{published_artifact_path}` | `{gold_schema_title}` | "
            "`{pipeline_code_owner}` | {gold_enabled} | `{coverage_status}` |".format(
                **row
            )
        )
    lines.append("")
    return "\n".join(lines)


def build_payload() -> dict[str, Any]:
    rows = _collect_entity_rows()
    explicit_exclusions = [
        {
            "pipeline_name": row["pipeline_name"],
            "contract_ref": row["contract_ref"],
            "config_path": row["config_path"],
            "reason": row["gold_exclusion_reason"],
        }
        for row in rows
        if not row["gold_enabled"]
    ]
    return {
        "snapshot_date": date.today().isoformat(),
        "row_count": len(rows),
        "explicit_exclusions": explicit_exclusions,
        "rows": rows,
    }


def write_artifacts(*, json_out: Path, md_out: Path) -> None:
    payload = build_payload()
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_out.write_text(_render_markdown(payload["rows"]), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate pipeline-config-contract ownership map artifacts."
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=DEFAULT_JSON_OUTPUT,
        help="JSON output path",
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        default=DEFAULT_MD_OUTPUT,
        help="Markdown output path",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when committed artifacts drift from the generator output.",
    )
    args = parser.parse_args(argv)

    if args.check:
        expected = json.dumps(build_payload(), indent=2, sort_keys=True) + "\n"
        actual = args.json_out.read_text(encoding="utf-8")
        if actual != expected:
            print(
                "[pipeline-config-contract-ownership-map] artifact drift detected; "
                "regenerate with: python -m scripts.engineering.qa "
                "report-pipeline-config-contract-ownership-map",
                file=sys.stderr,
            )
            return 1
        print("[ok] pipeline-config-contract ownership map is up to date")
        return 0

    write_artifacts(json_out=args.json_out, md_out=args.md_out)
    payload = build_payload()
    print(
        "[pipeline-config-contract-ownership-map] "
        f"rows={payload['row_count']}; json={args.json_out}; md={args.md_out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
