#!/usr/bin/env python3
"""Generate dashboard inventory and verify docs parity for canonical fields."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DASHBOARDS_DIR = Path("grafana/dashboards")
VARIABLES_GUIDE = Path("docs/03-guides/dashboards/variables-guide.md")
MONITORING_INDEX = Path("docs/03-guides/dashboards/monitoring-index.md")

MANDATORY_LINK_UIDS: dict[str, set[str]] = {
    "bioetl-overview-v2": {
        "bioetl-runtime",
        "bioetl-provider-health-v2",
        "bioetl-dq-v2",
        "bioetl-control-plane-v1",
        "bioetl-workflow-overview",
    },
    "bioetl-runtime": {"bioetl-overview-v2", "bioetl-dq-v2", "bioetl-control-plane-v1"},
    "bioetl-provider-health-v2": {"bioetl-overview-v2", "bioetl-runtime"},
    "bioetl-dq-v2": {"bioetl-overview-v2", "bioetl-silver-reject-explorer"},
    "bioetl-workflow-overview": {"bioetl-overview-v2", "bioetl-runtime", "bioetl-control-plane-v1"},
}


def _extract_variables(payload: dict) -> list[str]:
    templating = payload.get("templating", {}).get("list", [])
    names = [f"${item.get('name')}" for item in templating if item.get("name")]
    return sorted(names)


def _extract_link_uids(payload: dict) -> list[str]:
    links = payload.get("links", [])
    discovered: set[str] = set()
    for link in links:
        url = str(link.get("url", ""))
        matches = re.findall(r"/d/([A-Za-z0-9\-_]+)", url)
        discovered.update(matches)
    return sorted(discovered)


def _load_inventory() -> list[dict[str, object]]:
    inventory: list[dict[str, object]] = []
    for path in sorted(DASHBOARDS_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        inventory.append(
            {
                "file": str(path),
                "uid": payload.get("uid"),
                "title": payload.get("title"),
                "variables": _extract_variables(payload),
                "link_uids": _extract_link_uids(payload),
                "tags": sorted(payload.get("tags", [])),
            }
        )
    return inventory


def _parse_variables_guide(text: str) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for line in text.splitlines():
        if not line.startswith("| `bioetl-"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) < 2:
            continue
        uid = parts[0].strip("`")
        variables = sorted(re.findall(r"\$[A-Za-z0-9_]+", parts[1]))
        mapping[uid] = variables
    return mapping


def _check_parity(inventory: list[dict[str, object]]) -> list[str]:
    errors: list[str] = []
    vars_text = VARIABLES_GUIDE.read_text(encoding="utf-8")
    idx_text = MONITORING_INDEX.read_text(encoding="utf-8")
    vars_map = _parse_variables_guide(vars_text)

    for item in inventory:
        uid = str(item["uid"])
        vars_actual = list(item["variables"])
        doc_vars = vars_map.get(uid)
        if doc_vars is None:
            errors.append(f"variables-guide: missing UID row for {uid}")
        elif doc_vars != vars_actual:
            errors.append(f"variables-guide: variables mismatch for {uid}: doc={doc_vars} actual={vars_actual}")

        if uid not in idx_text:
            errors.append(f"monitoring-index: missing UID mention for {uid}")

        expected_links = MANDATORY_LINK_UIDS.get(uid)
        if expected_links:
            actual_links = set(item["link_uids"])
            missing = sorted(expected_links - actual_links)
            if missing:
                errors.append(f"mandatory links: {uid} missing links to {missing}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--check", action="store_true", help="Fail on canonical parity mismatches")
    args = parser.parse_args()

    inventory = _load_inventory()
    if args.json:
        print(json.dumps(inventory, ensure_ascii=False, indent=2))
    else:
        for item in inventory:
            print(f"{item['uid']}: {item['title']} vars={item['variables']} links={item['link_uids']} tags={item['tags']}")

    if args.check:
        errors = _check_parity(inventory)
        if errors:
            print("\nDashboard inventory parity check failed:")
            for error in errors:
                print(f"- {error}")
            return 1
        print("\nDashboard inventory parity check passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
