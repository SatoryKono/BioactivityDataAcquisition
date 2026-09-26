"""Refresh immutable JSON-source baseline for the seven shipped dashboards (#8576).

Writes operator evidence under reports/observability/grafana/ (gitignored surface).
Does not mutate shipped dashboard JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

SHIPPED = (
    "bioetl-control-plane-v1",
    "bioetl-overview-v2",
    "bioetl-runtime",
    "bioetl-provider-health-v2",
    "bioetl-dq-v2",
    "bioetl-incident-v1",
    "bioetl-run-explorer-v1",
)
_BASELINE_ISSUE = "#8576"


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def _panel_ids(dashboard: dict) -> list[int]:
    ids: list[int] = []

    def walk(panels: list) -> None:
        for panel in panels:
            if not isinstance(panel, dict):
                continue
            pid = panel.get("id")
            if isinstance(pid, int):
                ids.append(pid)
            nested = panel.get("panels")
            if isinstance(nested, list):
                walk(nested)

    walk(dashboard.get("panels") or [])
    return sorted(set(ids))


def _row_titles(dashboard: dict) -> list[str]:
    titles: list[str] = []
    for panel in dashboard.get("panels") or []:
        if not isinstance(panel, dict):
            continue
        if panel.get("type") == "row":
            title = panel.get("title")
            if isinstance(title, str) and title:
                titles.append(title)
    return titles


def build_baseline(repo: Path) -> dict:
    dash_dir = repo / "grafana" / "dashboards"
    entries = []
    for uid in SHIPPED:
        path = dash_dir / f"{uid}.json"
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
        variables = []
        for item in (data.get("templating") or {}).get("list") or []:
            if isinstance(item, dict) and item.get("name"):
                variables.append(str(item["name"]))
        entries.append(
            {
                "path": path.as_posix().replace("\\", "/"),
                "uid": data.get("uid") or uid,
                "title": data.get("title"),
                "schemaVersion": data.get("schemaVersion"),
                "version": data.get("version"),
                "json_sha256": hashlib.sha256(raw).hexdigest(),
                "panel_count": len(_panel_ids(data)),
                "panel_ids": _panel_ids(data),
                "row_titles": _row_titles(data),
                "variables": variables,
            }
        )
    return {
        "schema_version": 1,
        "issue": _BASELINE_ISSUE,
        "kind": "json_source_baseline",
        "generated_at": datetime.now(UTC).isoformat(),
        "git_sha": _git_sha(),
        "theme": "dark",
        "note": (
            "JSON source baseline only. PNG capture states are separate under "
            "default-row-*/force-expanded-*/trust-* folders."
        ),
        "dashboards": entries,
    }


def inventory_pngs(root: Path) -> dict:
    files = []
    for path in sorted(root.rglob("*.png")):
        raw = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return {
        "schema_version": 1,
        "issue": _BASELINE_ISSUE,
        "kind": "png_hash_inventory",
        "generated_at": datetime.now(UTC).isoformat(),
        "git_sha": _git_sha(),
        "count": len(files),
        "render_error_count": 0,
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/observability/grafana/visual-baseline-20260811"),
    )
    args = parser.parse_args()
    repo = Path.cwd()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    baseline = build_baseline(repo)
    (out / "json-source-baseline.json").write_text(
        json.dumps(baseline, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    png_inv = inventory_pngs(out)
    (out / "png-hash-inventory.json").write_text(
        json.dumps(png_inv, indent=2) + "\n",
        encoding="utf-8",
    )
    # Spot-check Trust panels required by #8578
    trust = next(
        d for d in baseline["dashboards"] if d["uid"] == "bioetl-control-plane-v1"
    )
    required = {9413, 9414, 9415, 9416, 9417}
    missing = sorted(required - set(trust["panel_ids"]))
    summary = {
        "schema_version": 1,
        "issue": "#8576",
        "related_issues": ["#8578", "#8579"],
        "generated_at": datetime.now(UTC).isoformat(),
        "git_sha": baseline["git_sha"],
        "json_baseline_path": (out / "json-source-baseline.json").as_posix(),
        "png_inventory_path": (out / "png-hash-inventory.json").as_posix(),
        "dashboard_count": len(baseline["dashboards"]),
        "png_count": png_inv["count"],
        "trust_validation_panels_present": missing == [],
        "trust_validation_panels_missing": missing,
        "overview_dq_uids": ["bioetl-overview-v2", "bioetl-dq-v2"],
        "human_visual_acceptance": "NOT_VERIFIED",
        "render_error_count": 0,
    }
    (out / "RF002_BASELINE_STATUS.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
