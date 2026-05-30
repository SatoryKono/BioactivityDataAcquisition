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


def _collect_entity_rows() -> list[dict[str, str | bool]]:
    rows: list[dict[str, str | bool]] = []
    entities_root = PROJECT_ROOT / "configs" / "entities"
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
        row: dict[str, str | bool] = {
            "pipeline_name": pipeline_name,
            "provider": provider,
            "entity": entity,
            "contract_ref": contract_ref,
            "config_path": config_path.relative_to(PROJECT_ROOT).as_posix(),
            "contract_config_path": (
                contract_config.relative_to(PROJECT_ROOT).as_posix()
                if contract_config.exists()
                else ""
            ),
            "pipeline_code_owner": _pipeline_owner(provider, entity, pipeline_name),
            "gold_enabled": gold_enabled,
        }
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
        "| pipeline_name | contract_ref | config_path | contract_config_path | pipeline_code_owner | gold_enabled |",
        "| --- | --- | --- | --- | --- | ---: |",
    ]
    for row in rows:
        lines.append(
            "| `{pipeline_name}` | `{contract_ref}` | `{config_path}` | "
            "`{contract_config_path}` | `{pipeline_code_owner}` | {gold_enabled} |".format(
                **row
            )
        )
    lines.append("")
    return "\n".join(lines)


def build_payload() -> dict[str, Any]:
    rows = _collect_entity_rows()
    return {
        "snapshot_date": date.today().isoformat(),
        "row_count": len(rows),
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
