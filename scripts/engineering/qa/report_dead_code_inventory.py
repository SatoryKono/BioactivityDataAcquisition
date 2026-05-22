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
    parser.add_argument(
        "--snapshot-date",
        default=None,
        help=(
            "Snapshot date to embed in generated artifacts. In --check mode the "
            "existing JSON snapshot_date is reused when this is omitted."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if committed dead-code inventory artifacts differ from generated output.",
    )
    return parser.parse_args()


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_retained_entrypoint_paths(repo_root: Path) -> set[str]:
    payload = _load_yaml(
        repo_root / "configs" / "quality" / "compatibility_facade_inventory.yaml"
    )
    rows = payload.get("retained_entrypoints", [])
    assert isinstance(rows, list)
    return {str(row["path"]) for row in rows if isinstance(row, dict) and "path" in row}


def _build_review_window(
    triage_payload: dict[str, Any],
    *,
    snapshot_date: str,
) -> dict[str, object]:
    zero_import_review = triage_payload.get("repo_wide_zero_import_review", {})
    if not isinstance(zero_import_review, dict):
        zero_import_review = {}
    policy = triage_payload.get("policy", {})
    if not isinstance(policy, dict):
        policy = {}
    last_reviewed = zero_import_review.get("last_reviewed")
    next_review_by = zero_import_review.get("next_review_by")
    return {
        "linked_issue": zero_import_review.get("linked_issue"),
        "mode": zero_import_review.get("mode"),
        "last_reviewed": last_reviewed,
        "next_review_by": next_review_by,
        "review_cycle_days": policy.get("review_cycle_days"),
        "max_untriaged_zero_import_candidates": zero_import_review.get(
            "max_untriaged_zero_import_candidates"
        ),
        "snapshot_matches_last_reviewed": snapshot_date == last_reviewed,
        "guardrail_note": (
            "Zero static importer count is a review signal only; removals must "
            "still verify public entrypoints and dynamic/plugin import paths."
        ),
    }


def _load_repo_wide_zero_import_classifications(
    triage_payload: dict[str, Any],
) -> tuple[dict[str, dict[str, object]], set[str]]:
    section = triage_payload.get("repo_wide_zero_import_classification", {})
    assert isinstance(section, dict)
    entries = section.get("entries", [])
    assert isinstance(entries, list)
    allowed = section.get("allowed_dispositions", [])
    assert isinstance(allowed, list)
    classification_by_path: dict[str, dict[str, object]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        module_path = entry.get("module_path")
        if isinstance(module_path, str):
            classification_by_path[module_path] = entry
    return classification_by_path, {str(item) for item in allowed}


def _review_window_is_stale(review_window: dict[str, object]) -> bool:
    next_review_by = review_window.get("next_review_by")
    if not isinstance(next_review_by, str):
        return False
    return date.today() > date.fromisoformat(next_review_by)


def build_dead_code_inventory(
    repo_root: Path,
    *,
    snapshot_date: str | None = None,
) -> dict[str, object]:
    from scripts.engineering.qa.import_graph_inventory import (
        collect_bioetl_importers,
        collect_zero_import_bioetl_modules,
    )

    importer_map = collect_bioetl_importers(repo_root)
    triage_payload = _load_yaml(
        repo_root / "configs" / "quality" / "retirement_candidate_triage.yaml"
    )
    retained_entrypoint_paths = _load_retained_entrypoint_paths(repo_root)
    repo_wide_classifications, allowed_repo_wide_dispositions = (
        _load_repo_wide_zero_import_classifications(triage_payload)
    )

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

    repo_wide_zero_import_candidates: list[dict[str, object]] = []
    repo_wide_disposition_counts: dict[str, int] = {}
    untriaged_candidates: list[dict[str, object]] = []
    for row in collect_zero_import_bioetl_modules(repo_root):
        module_path = str(row["path"])
        if module_path in retained_entrypoint_paths:
            continue
        enriched = dict(row)
        classification = repo_wide_classifications.get(module_path)
        if classification is None:
            enriched["classification_status"] = "untriaged"
            untriaged_candidates.append(enriched)
            repo_wide_zero_import_candidates.append(enriched)
            continue
        module_name = classification.get("module_name")
        if isinstance(module_name, str):
            assert module_name == row["module_name"], (
                f"repo_wide_zero_import_classification module_name mismatch for "
                f"{module_path}: {module_name!r} != {row['module_name']!r}"
            )
        disposition = classification.get("disposition")
        assert isinstance(disposition, str) and disposition in allowed_repo_wide_dispositions
        repo_wide_disposition_counts[disposition] = (
            repo_wide_disposition_counts.get(disposition, 0) + 1
        )
        enriched.update(
            {
                "classification_status": "classified",
                "disposition": disposition,
                "reviewed_on": classification.get("reviewed_on"),
                "review_by": classification.get("review_by"),
                "linked_issue": classification.get("linked_issue"),
                "rationale": classification.get("rationale"),
            }
        )
        repo_wide_zero_import_candidates.append(enriched)

    resolved_snapshot_date = snapshot_date or date.today().isoformat()
    review_window = _build_review_window(
        triage_payload,
        snapshot_date=resolved_snapshot_date,
    )

    return {
        "snapshot_date": resolved_snapshot_date,
        "triage_source": "configs/quality/retirement_candidate_triage.yaml",
        "static_inventory_scope": "src/bioetl",
        "review_window": review_window,
        "summary": {
            "triaged_entry_count": len(triaged_rows),
            "triaged_entries_below_min_importers": sum(
                1 for row in triaged_rows if row["verification_status"] == "below_min"
            ),
            "repo_wide_zero_import_candidate_count": len(
                repo_wide_zero_import_candidates
            ),
            "repo_wide_classified_zero_import_candidate_count": len(
                repo_wide_zero_import_candidates
            )
            - len(untriaged_candidates),
            "repo_wide_untriaged_zero_import_candidate_count": len(
                untriaged_candidates
            ),
            "repo_wide_disposition_counts": dict(
                sorted(repo_wide_disposition_counts.items())
            ),
        },
        "triaged_entries": triaged_rows,
        "repo_wide_zero_import_candidates": repo_wide_zero_import_candidates,
    }


def _render_markdown(payload: dict[str, object]) -> str:
    review_window = payload["review_window"]
    summary = payload["summary"]
    triaged_rows = payload["triaged_entries"]
    zero_rows = payload["repo_wide_zero_import_candidates"]
    assert isinstance(review_window, dict)
    assert isinstance(summary, dict)
    assert isinstance(triaged_rows, list)
    assert isinstance(zero_rows, list)
    lines = [
        "# Dead Code Inventory",
        "",
        f"- snapshot_date: {payload['snapshot_date']}",
        f"- linked_issue: {review_window['linked_issue']}",
        f"- last_reviewed: {review_window['last_reviewed']}",
        f"- next_review_by: {review_window['next_review_by']}",
        f"- review_cycle_days: {review_window['review_cycle_days']}",
        f"- triaged_entry_count: {summary['triaged_entry_count']}",
        f"- repo_wide_zero_import_candidate_count: {summary['repo_wide_zero_import_candidate_count']}",
        "- repo_wide_classified_zero_import_candidate_count: "
        f"{summary['repo_wide_classified_zero_import_candidate_count']}",
        "- repo_wide_untriaged_zero_import_candidate_count: "
        f"{summary['repo_wide_untriaged_zero_import_candidate_count']}",
        "- note: zero static importer count is a review signal, not automatic removal proof",
        f"- guardrail: {review_window['guardrail_note']}",
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
            "| Module | Disposition | Path |",
            "| --- | --- | --- |",
        ]
    )
    for row in zero_rows:
        assert isinstance(row, dict)
        lines.append(
            f"| `{row['module_name']}` | `{row.get('disposition', 'untriaged')}` | `{row['path']}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _existing_snapshot_date(path: Path) -> str | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    snapshot_date = payload.get("snapshot_date")
    return snapshot_date if isinstance(snapshot_date, str) else None


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.repo_root)
    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    snapshot_date = args.snapshot_date
    if args.check and snapshot_date is None:
        snapshot_date = _existing_snapshot_date(json_out)
    payload = build_dead_code_inventory(repo_root, snapshot_date=snapshot_date)
    rendered_json = json.dumps(payload, indent=2) + "\n"
    rendered_markdown = _render_markdown(payload)

    if args.check:
        if not json_out.exists():
            print(f"[dead-code-inventory] missing JSON artifact: {json_out}")
            return 1
        if not md_out.exists():
            print(f"[dead-code-inventory] missing Markdown artifact: {md_out}")
            return 1
        if json_out.read_text(encoding="utf-8") != rendered_json:
            print(f"[dead-code-inventory] FAIL: JSON artifact drifted: {json_out}")
            return 1
        if md_out.read_text(encoding="utf-8") != rendered_markdown:
            print(f"[dead-code-inventory] FAIL: Markdown artifact drifted: {md_out}")
            return 1
        review_window = payload["review_window"]
        assert isinstance(review_window, dict)
        if _review_window_is_stale(review_window):
            print(
                "[dead-code-inventory] FAIL: review window is stale: "
                f"next_review_by={review_window.get('next_review_by')}"
            )
            return 1
        summary = payload["summary"]
        assert isinstance(summary, dict)
        untriaged = summary["repo_wide_untriaged_zero_import_candidate_count"]
        max_untriaged = review_window.get("max_untriaged_zero_import_candidates")
        if isinstance(max_untriaged, int) and untriaged > max_untriaged:
            print(
                "[dead-code-inventory] FAIL: repo-wide zero-import candidates remain "
                "untriaged: "
                f"{untriaged} > {max_untriaged}"
            )
            return 1
        print("[dead-code-inventory] PASS: artifacts are up to date")
        return 0

    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(rendered_json, encoding="utf-8")
    md_out.write_text(rendered_markdown, encoding="utf-8")
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
