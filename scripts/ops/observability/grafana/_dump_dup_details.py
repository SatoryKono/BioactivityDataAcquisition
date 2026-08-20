"""One-shot dump of text panels and targeted PromQL. Delete after audit."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

UIDS = [
    "bioetl-control-plane-v1",
    "bioetl-overview-v2",
    "bioetl-runtime",
    "bioetl-provider-health-v2",
    "bioetl-dq-v2",
    "bioetl-incident-v1",
    "bioetl-run-explorer-v1",
]
WANT = {
    "bioetl-control-plane-v1": {1, 2, 4, 132, 133, 136, 130, 3, 891, 893},
    "bioetl-overview-v2": {9018, 9019, 9020, 9003, 9004, 9005, 214, 215},
    "bioetl-runtime": {16, 9101, 242, 205},
    "bioetl-provider-health-v2": {9101, 9111, 9401, 104, 7, 106, 107},
    "bioetl-dq-v2": {117, 154, 6, 9401},
    "bioetl-incident-v1": {2010, 2002, 2003, 2004, 9401},
}


def git_json(path: str) -> dict:
    raw = subprocess.check_output(
        ["git", "show", f"origin/main:{path}"],
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(raw)
    assert isinstance(payload, dict)
    return payload


def walk(panels: list, acc: list | None = None, row: dict | None = None) -> list:
    if acc is None:
        acc = []
    for panel in panels or []:
        acc.append((panel, row))
        if panel.get("type") == "row" and panel.get("panels"):
            walk(panel.get("panels"), acc, panel)
    return acc


def main() -> int:
    dest = Path("reports/quality/grafana-data-duplication")
    dest.mkdir(parents=True, exist_ok=True)
    text_lines: list[str] = []
    expr_lines: list[str] = []
    for uid in UIDS:
        dash = git_json(f"grafana/dashboards/{uid}.json")
        text_lines.append(f"=== {uid} TEXT ===")
        for panel, row in walk(dash.get("panels") or []):
            if panel.get("type") != "text":
                continue
            content = ((panel.get("options") or {}).get("content") or "").replace("\n", " | ")
            rid = None if row is None else row.get("id")
            text_lines.append(
                f"{panel.get('id')}|row={rid}|y={(panel.get('gridPos') or {}).get('y')}|{panel.get('title')}"
            )
            text_lines.append(content[:320])
        expr_lines.append(f"=== {uid} EXPRS ===")
        ids = WANT.get(uid, set())
        for panel, row in walk(dash.get("panels") or []):
            if panel.get("id") not in ids:
                continue
            rid = None if row is None else row.get("id")
            expr_lines.append(
                f"{panel.get('id')}|{panel.get('type')}|row={rid}|{panel.get('title')}"
            )
            for target in panel.get("targets") or []:
                if target.get("hide"):
                    continue
                expr = str(target.get("expr") or "").replace("\n", " ")
                expr_lines.append("  " + expr[:300])
    (dest / "text_panels.txt").write_text("\n".join(text_lines) + "\n", encoding="utf-8")
    (dest / "target_exprs.txt").write_text("\n".join(expr_lines) + "\n", encoding="utf-8")
    print("wrote", dest / "text_panels.txt")
    print("wrote", dest / "target_exprs.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
