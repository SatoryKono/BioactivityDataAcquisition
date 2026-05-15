#!/usr/bin/env python3
"""Generate a repo-local static dead-code review inventory."""

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
DEFAULT_JSON_OUTPUT = PROJECT_ROOT / "reports" / "quality" / "dead-code-inventory.json"
DEFAULT_MD_OUTPUT = PROJECT_ROOT / "reports" / "quality" / "dead-code-inventory.md"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(PROJECT_ROOT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-out", default=str(DEFAULT_MD_OUTPUT))
    return parser.parse_args()


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_retained_entrypoint_paths(repo_root: Path) -> set[str]:
    payload = _load_yaml(repo_root / "configs" / "quality" / "compatibility_facade_inventory.yaml")
    rows = payload.get("retained_entrypoints", [])
    assert isinstance(rows, list)
    return {
        str(row["path"]) for row in rows if isinstance(row, dict) and "path" in row
    }


def build_dead_code_inventory(repo_root: Path) -> dict[str, object]:
    from scripts.engineering.qa.import_graph_inventory import (
        collect_bioetl_importers,
        collect_zero_import_bioetl_modules,
    )

    importer_map = collect_bioetl_importers(repo_root)
    triage_payload = _load_yaml(
        repo_root / "configs" / "quality" / "retirement_candidate_triage.yaml"
    )
    retained_entrypoint_paths = _load_retained_entrypoint_paths(repo_root)

    triaged_rows: list[dict[str, object]] = []
    families = triage_payload.get("families", [])
    assert isinstance(families, list)
    for family in families:
        if not isinstance(family, dict):
            continue
        family_name = str(family.get("name", "unknown"))
        entries = family.get("entries", [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            target = entry.get("target", {})
            if not isinstance(target, dict):
                continue
            module_name = target.get("module_name")
            module_path = target.get("module_path") or target.get("name")
            if not isinstance(module_path, str):
                continue
            importers = (
                importer_map.get(str(module_name), {"src": (), "tests": ()})
                if isinstance(module_name, str)
                else {"src": (), "tests": ()}
            )
            min_src_importers = (
                entry.get("verification", {}).get("min_src_importers")
                if isinstance(entry.get("verification"), dict)
                else None
            )
            src_count = len(importers.get("src", ()))
            verification_status = "not_applicable"
            if isinstance(min_src_importers, int):
                verification_status = (
                    "satisfied" if src_count >= min_src_importers else "below_min"
                )
            triaged_rows.append(
                {
                    "family": family_name,
                    "entry_id": entry.get("id"),
                    "disposition": entry.get("disposition"),
                    "module_path": module_path,
                    "module_name": module_name,
                    "src_importer_count": src_count,
                    "test_importer_count": len(importers.get("tests", ())),
                    "min_src_importers": min_src_importers,
                    "verification_status": verification_status,
                }
            )

    repo_wide_zero_import_candidates = [
        row
        for row in collect_zero_import_bioetl_modules(repo_root)
        if str(row["path"]) not in retained_entrypoint_paths
    ]

    return {
        "snapshot_date": date.today().isoformat(),
        "triage_source": "configs/quality/retirement_candidate_triage.yaml",
        "static_inventory_scope": "src/bioetl",
        "summary": {
            "triaged_entry_count": len(triaged_rows),
            "triaged_entries_below_min_importers": sum(
                1 for row in triaged_rows if row["verification_status"] == "below_min"
            ),
            "repo_wide_zero_import_candidate_count": len(repo_wide_zero_import_candidates),
        },
        "triaged_entries": triaged_rows,
        "repo_wide_zero_import_candidates": repo_wide_zero_import_candidates,
    }


def _render_markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    triaged_rows = payload["triaged_entries"]
    zero_rows = payload["repo_wide_zero_import_candidates"]
    assert isinstance(summary, dict)
    assert isinstance(triaged_rows, list)
    assert isinstance(zero_rows, list)
    lines = [
        "# Dead Code Inventory",
        "",
        f"- snapshot_date: {payload['snapshot_date']}",
        f"- triaged_entry_count: {summary['triaged_entry_count']}",
        "- note: zero static importer count is a review signal, not automatic removal proof",
        "",
        "## Triage Verification",
        "",
        "| Entry | Disposition | src importers | Verification |",
        "| --- | --- | ---: | --- |",
    ]
    for row in triaged_rows:
        assert isinstance(row, dict)
        lines.append(
            "| "
            f"`{row['entry_id']}` | `{row['disposition']}` | "
            f"{row['src_importer_count']} | `{row['verification_status']}` |"
        )

    lines.extend(
        [
            "",
            "## Repo-wide Zero-import Candidates",
            "",
            "| Module | Path |",
            "| --- | --- |",
        ]
    )
    for row in zero_rows:
        assert isinstance(row, dict)
        lines.append(f"| `{row['module_name']}` | `{row['path']}` |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.repo_root)
    payload = build_dead_code_inventory(repo_root)
    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(_render_markdown(payload), encoding="utf-8")
    print(
        "[dead-code-inventory] "
        f"triaged_entries={payload['summary']['triaged_entry_count']}; "
        "repo_wide_zero_import_candidates="
        f"{payload['summary']['repo_wide_zero_import_candidate_count']}; "
        f"json={json_out}; markdown={md_out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
