#!/usr/bin/env python3
"""Generate a deterministic importer census for retained seams and twin modules."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
DEFAULT_MD_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "compatibility-importer-census.md"
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(PROJECT_ROOT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-out", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument("--snapshot-date", default=date.today().isoformat())
    return parser.parse_args()


def _load_retained_entrypoints(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    rows = payload.get("retained_entrypoints", [])
    assert isinstance(rows, list)
    return [row for row in rows if isinstance(row, dict)]


def _module_name_from_repo_path(repo_path: str) -> str:
    normalized = repo_path.removeprefix("src/").removesuffix(".py")
    if normalized.endswith("/__init__"):
        normalized = normalized[: -len("/__init__")]
    return normalized.replace("/", ".")


def build_compatibility_importer_census(
    repo_root: Path, *, snapshot_date: str | None = None
) -> dict[str, object]:
    from scripts.engineering.qa.import_graph_inventory import (
        collect_bioetl_importers,
        find_public_private_twin_modules,
    )

    importer_map = collect_bioetl_importers(repo_root)
    retained_entrypoints = _load_retained_entrypoints(
        repo_root / "configs" / "quality" / "compatibility_facade_inventory.yaml"
    )
    twin_pairs = find_public_private_twin_modules(repo_root)

    retained_rows: list[dict[str, object]] = []
    for row in retained_entrypoints:
        repo_path = str(row["path"])
        module_name = _module_name_from_repo_path(repo_path)
        importers = importer_map.get(module_name, {"src": (), "tests": ()})
        retained_rows.append(
            {
                "path": repo_path,
                "module_name": module_name,
                "status": row.get("status"),
                "canonical_target": row.get("canonical_target"),
                "owner": row.get("owner"),
                "src_importers": list(importers.get("src", ())),
                "test_importers": list(importers.get("tests", ())),
                "src_importer_count": len(importers.get("src", ())),
                "test_importer_count": len(importers.get("tests", ())),
            }
        )

    twin_rows: list[dict[str, object]] = []
    for pair in twin_pairs:
        public_importers = importer_map.get(pair["public_module"], {"src": (), "tests": ()})
        private_importers = importer_map.get(
            pair["private_module"], {"src": (), "tests": ()}
        )
        twin_rows.append(
            {
                **pair,
                "public_src_importer_count": len(public_importers.get("src", ())),
                "public_test_importer_count": len(public_importers.get("tests", ())),
                "private_src_importer_count": len(private_importers.get("src", ())),
                "private_test_importer_count": len(private_importers.get("tests", ())),
                "public_src_importers": list(public_importers.get("src", ())),
                "private_src_importers": list(private_importers.get("src", ())),
            }
        )

    return {
        "snapshot_date": snapshot_date or date.today().isoformat(),
        "inventory_source": "configs/quality/compatibility_facade_inventory.yaml",
        "summary": {
            "retained_entrypoint_count": len(retained_rows),
            "twin_pair_count": len(twin_rows),
            "twin_pairs_with_private_src_importers": sum(
                1 for row in twin_rows if row["private_src_importer_count"] > 0
            ),
            "twin_pairs_without_public_src_importers": sum(
                1 for row in twin_rows if row["public_src_importer_count"] == 0
            ),
        },
        "retained_entrypoints": retained_rows,
        "twin_pairs": twin_rows,
    }


def _render_markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    retained_rows = payload["retained_entrypoints"]
    twin_rows = payload["twin_pairs"]
    assert isinstance(summary, dict)
    assert isinstance(retained_rows, list)
    assert isinstance(twin_rows, list)

    lines = [
        "# Compatibility Importer Census",
        "",
        f"- snapshot_date: {payload['snapshot_date']}",
        f"- retained_entrypoint_count: {summary['retained_entrypoint_count']}",
        f"- twin_pair_count: {summary['twin_pair_count']}",
        "- purpose: measure sanctioned public seams and underscore/public twin usage",
        "",
        "## Retained Entrypoints",
        "",
        "| Path | src importers | test importers |",
        "| --- | ---: | ---: |",
    ]
    for row in retained_rows:
        assert isinstance(row, dict)
        lines.append(
            f"| `{row['path']}` | {row['src_importer_count']} | {row['test_importer_count']} |"
        )

    lines.extend(
        [
            "",
            "## Twin Modules",
            "",
            "| Public module | Public src | Private src |",
            "| --- | ---: | ---: |",
        ]
    )
    for row in twin_rows:
        assert isinstance(row, dict)
        lines.append(
            f"| `{row['public_module']}` | {row['public_src_importer_count']} | {row['private_src_importer_count']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.repo_root)
    payload = build_compatibility_importer_census(
        repo_root, snapshot_date=str(args.snapshot_date)
    )
    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(_render_markdown(payload), encoding="utf-8")
    print(
        "[compatibility-importer-census] "
        f"retained_entrypoints={payload['summary']['retained_entrypoint_count']}; "
        f"twin_pairs={payload['summary']['twin_pair_count']}; "
        f"json={json_out}; markdown={md_out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
