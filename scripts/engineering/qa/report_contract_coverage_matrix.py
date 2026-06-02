#!/usr/bin/env python3
"""Generate deterministic contract coverage matrix artifacts for active entity configs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIGS_ROOT = PROJECT_ROOT / "configs"
ENTITIES_ROOT = CONFIGS_ROOT / "entities"
REGISTRY_PATH = CONFIGS_ROOT / "base" / "contract_registry.yaml"
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "contract-coverage-matrix.json"
)
DEFAULT_MD_OUTPUT = PROJECT_ROOT / "reports" / "quality" / "contract-coverage-matrix.md"


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Expected mapping in {path.as_posix()}"
        raise TypeError(msg)
    return payload


def _gold_runtime_enabled(pipeline: dict[str, Any]) -> bool:
    sink = pipeline.get("sink")
    if not isinstance(sink, dict):
        return True
    gold = sink.get("gold")
    if not isinstance(gold, dict):
        return True
    enabled = gold.get("enabled")
    return True if enabled is None else bool(enabled)


def _registry_entries() -> dict[str, dict[str, Any]]:
    payload = _load_yaml(REGISTRY_PATH)
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        msg = f"Expected entries mapping in {REGISTRY_PATH.as_posix()}"
        raise TypeError(msg)
    normalized: dict[str, dict[str, Any]] = {}
    for contract_ref, entry in entries.items():
        if not isinstance(contract_ref, str) or not isinstance(entry, dict):
            continue
        normalized[contract_ref] = entry
    return normalized


def _resolve_registry_relative(path: str) -> Path:
    return (REGISTRY_PATH.parent / path).resolve()


def _relativize(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _build_row(
    *,
    config_path: Path,
    config_payload: dict[str, Any],
    registry_entries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    provider = str(config_payload.get("provider") or config_path.parent.name)
    entity = str(config_payload.get("entity") or config_path.stem)
    pipeline = config_payload.get("pipeline")
    if not isinstance(pipeline, dict):
        pipeline = {}
    pipeline_name = str(pipeline.get("pipeline_name") or f"{provider}_{entity}")
    contract_ref = f"{provider}.{entity}"
    gold_enabled = _gold_runtime_enabled(pipeline)

    contract_yaml_path = CONFIGS_ROOT / "contracts" / provider / f"{entity}.yaml"
    contract_yaml_exists = contract_yaml_path.is_file()
    contract_payload = _load_yaml(contract_yaml_path) if contract_yaml_exists else {}

    registry_entry = registry_entries.get(contract_ref)
    registry_entry_exists = registry_entry is not None
    registry_identity = (
        registry_entry.get("identity", {}) if isinstance(registry_entry, dict) else {}
    )
    if not isinstance(registry_identity, dict):
        registry_identity = {}

    source_path = (
        str(registry_entry.get("source_path", ""))
        if isinstance(registry_entry, dict)
        else ""
    )
    source_exists = (
        bool(source_path) and _resolve_registry_relative(source_path).is_file()
    )

    published_artifacts = (
        _string_list(registry_entry.get("published_artifacts"))
        if isinstance(registry_entry, dict)
        else []
    )
    published_artifact_missing_paths = [
        artifact
        for artifact in published_artifacts
        if not _resolve_registry_relative(artifact).is_file()
    ]

    missing_surfaces: list[str] = []
    if not contract_yaml_exists:
        missing_surfaces.append("contract_yaml")
    if not registry_entry_exists:
        missing_surfaces.append("registry_entry")
    if not source_path:
        missing_surfaces.append("gold_schema_source_path")
    elif not source_exists:
        missing_surfaces.append("gold_schema_source_file")
    if not published_artifacts:
        missing_surfaces.append("published_artifact")
    elif published_artifact_missing_paths:
        missing_surfaces.append("published_artifact_file")

    yaml_contract_ref = contract_payload.get("contract_ref")
    yaml_contract_version = contract_payload.get("contract_version")
    registry_contract_version = registry_identity.get("contract_version")
    if contract_yaml_exists and yaml_contract_ref != contract_ref:
        missing_surfaces.append("contract_ref_mismatch")
    if contract_yaml_exists and registry_entry_exists:
        if yaml_contract_version != registry_contract_version:
            missing_surfaces.append("contract_version_mismatch")

    parity_status = "covered"
    exclusion_reason = ""
    if not gold_enabled:
        parity_status = "excluded"
        exclusion_reason = "gold_runtime_disabled"
    elif missing_surfaces:
        parity_status = "missing_surfaces"

    return {
        "pipeline_name": pipeline_name,
        "provider": provider,
        "entity": entity,
        "contract_ref": contract_ref,
        "config_path": _relativize(config_path),
        "gold_enabled": gold_enabled,
        "parity_status": parity_status,
        "exclusion_reason": exclusion_reason,
        "contract_yaml_path": (
            _relativize(contract_yaml_path) if contract_yaml_exists else ""
        ),
        "contract_yaml_exists": contract_yaml_exists,
        "contract_yaml_contract_ref": (
            str(yaml_contract_ref) if isinstance(yaml_contract_ref, str) else ""
        ),
        "contract_yaml_contract_version": (
            str(yaml_contract_version) if isinstance(yaml_contract_version, str) else ""
        ),
        "registry_entry_exists": registry_entry_exists,
        "registry_status": (
            str(registry_entry.get("status", ""))
            if isinstance(registry_entry, dict)
            else ""
        ),
        "registry_contract_version": (
            str(registry_contract_version)
            if isinstance(registry_contract_version, str)
            else ""
        ),
        "gold_schema_source_path": source_path,
        "gold_schema_source_exists": source_exists,
        "published_artifact_paths": published_artifacts,
        "published_artifact_missing_paths": published_artifact_missing_paths,
        "missing_surfaces": sorted(set(missing_surfaces)),
    }


def _collect_rows() -> list[dict[str, Any]]:
    registry_entries = _registry_entries()
    rows: list[dict[str, Any]] = []
    for config_path in sorted(ENTITIES_ROOT.glob("*/*.yaml")):
        rows.append(
            _build_row(
                config_path=config_path,
                config_payload=_load_yaml(config_path),
                registry_entries=registry_entries,
            )
        )
    return rows


def build_payload() -> dict[str, Any]:
    rows = _collect_rows()
    covered_gold_enabled_count = sum(
        1 for row in rows if row["gold_enabled"] and row["parity_status"] == "covered"
    )
    gold_enabled_count = sum(1 for row in rows if row["gold_enabled"])
    excluded_rows = [row for row in rows if row["parity_status"] == "excluded"]
    return {
        "snapshot_date": date.today().isoformat(),
        "row_count": len(rows),
        "gold_enabled_count": gold_enabled_count,
        "covered_gold_enabled_count": covered_gold_enabled_count,
        "missing_gold_enabled_count": gold_enabled_count - covered_gold_enabled_count,
        "excluded_count": len(excluded_rows),
        "exclusions": [
            {
                "pipeline_name": row["pipeline_name"],
                "contract_ref": row["contract_ref"],
                "reason": row["exclusion_reason"],
            }
            for row in excluded_rows
        ],
        "rows": rows,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    rows = payload["rows"]
    lines = [
        "# Contract Coverage Matrix",
        "",
        f"- snapshot_date: {payload['snapshot_date']}",
        f"- row_count: {payload['row_count']}",
        f"- gold_enabled_count: {payload['gold_enabled_count']}",
        f"- covered_gold_enabled_count: {payload['covered_gold_enabled_count']}",
        f"- missing_gold_enabled_count: {payload['missing_gold_enabled_count']}",
        f"- excluded_count: {payload['excluded_count']}",
        "",
        "| pipeline_name | contract_ref | gold_enabled | parity_status | contract_yaml_path | registry_status | missing_surfaces |",
        "| --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        render_row = dict(row)
        render_row["missing_surfaces_rendered"] = (
            ", ".join(row["missing_surfaces"]) or "-"
        )
        lines.append(
            "| `{pipeline_name}` | `{contract_ref}` | {gold_enabled} | "
            "`{parity_status}` | `{contract_yaml_path}` | `{registry_status}` | {missing_surfaces_rendered} |".format(
                **render_row,
            )
        )
    lines.append("")
    return "\n".join(lines)


def write_artifacts(*, json_out: Path, md_out: Path) -> None:
    payload = build_payload()
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_out.write_text(_render_markdown(payload), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate contract coverage matrix artifacts."
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
        help="Fail when committed artifacts drift from generator output.",
    )
    args = parser.parse_args(argv)

    if args.check:
        expected = json.dumps(build_payload(), indent=2, sort_keys=True) + "\n"
        actual = args.json_out.read_text(encoding="utf-8")
        if actual != expected:
            print(
                "[contract-coverage-matrix] artifact drift detected; regenerate with: "
                "python -m scripts.engineering.qa report-contract-coverage-matrix",
                file=sys.stderr,
            )
            return 1
        print("[ok] contract coverage matrix is up to date")
        return 0

    write_artifacts(json_out=args.json_out, md_out=args.md_out)
    payload = build_payload()
    print(
        "[contract-coverage-matrix] "
        f"rows={payload['row_count']}; gold_enabled={payload['gold_enabled_count']}; "
        f"covered={payload['covered_gold_enabled_count']}; "
        f"json={args.json_out}; md={args.md_out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
