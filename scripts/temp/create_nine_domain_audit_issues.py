"""Prepare and create GitHub issues for nine-domain-audit P0/P1 findings.

Usage:
  python scripts/temp/create_nine_domain_audit_issues.py --prepare-only
  python scripts/temp/create_nine_domain_audit_issues.py --create
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = ROOT / "reports/audit-runs/latest-nine-domain/findings-index.json"
OUT = ROOT / "reports/audit-runs/latest-nine-domain/issue-payloads"

DOMAIN_PATH = {
    "tests-system": "tests",
    "github-actions": "gha",
    "agents-runtime": "agents",
    "architecture-review": "architecture",
}

DOMAIN_LABELS = {
    "docs-content": ["docs", "documentation"],
    "tests-system": ["testing", "ci"],
    "tech-debt": ["tech-debt", "coverage"],
    "repo-tree": ["cleanup"],
    "github-actions": ["ci", "ci/cd"],
    "agents-runtime": ["ai-runtime", "ai"],
    "diagrams": ["diagrams", "docs"],
    "docs-pipeline": ["docs", "documentation"],
    "architecture-review": ["architecture"],
}


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)


def load_index() -> dict:
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def load_enriched(index: dict) -> dict[tuple[str, str], dict]:
    enriched: dict[tuple[str, str], dict] = {}
    for ds in index["domain_scores"]:
        fp = Path(ds["findings_path"])
        if not fp.is_file():
            continue
        raw = json.loads(fp.read_text(encoding="utf-8"))
        items = (
            raw
            if isinstance(raw, list)
            else raw.get("findings") or raw.get("items") or []
        )
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                enriched[(ds["domain_id"], str(item["id"]))] = item
    return enriched


def labels_for(domain_id: str, priority: str) -> list[str]:
    labels = ["audit"]
    if priority == "P0":
        labels.extend(["priority:critical", "P0"])
    else:
        labels.extend(["priority:high", "P1"])
    labels.extend(DOMAIN_LABELS.get(domain_id, []))
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for label in labels:
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out


def body_for(finding: dict, enriched: dict, parent_ref: str | None) -> str:
    detail = enriched.get((finding["domain_id"], finding["id"]), {})
    dpath = DOMAIN_PATH.get(finding["domain_id"], finding["domain_id"])
    expected = detail.get("expected") or ""
    actual = detail.get("actual") or ""
    method = detail.get("method") or ""
    category = detail.get("category") or ""
    confidence = detail.get("confidence") or "PROVEN"
    remediation = (
        finding.get("remediation")
        or detail.get("remediation")
        or detail.get("fix")
        or "_TBD_"
    )
    observation = finding.get("observation") or detail.get("observation") or ""

    parts = [
        f"## Audit finding `{finding['id']}`",
        "",
        "- **Campaign:** nine-domain-audit 2026-08-11",
        f"- **Domain:** `{finding['domain_id']}`",
        f"- **Priority:** {finding['priority']}",
        f"- **Status:** {confidence}",
        f"- **Path:** `{finding['path']}`",
    ]
    if parent_ref:
        parts.append(f"- **Parent:** {parent_ref}")
    if category:
        parts.append(f"- **Category:** `{category}`")
    parts += ["", "## Observation", "", str(observation), ""]
    if expected:
        parts += ["## Expected", "", "```", str(expected)[:2000], "```", ""]
    if actual:
        parts += ["## Actual", "", "```", str(actual)[:2000], "```", ""]
    if method:
        parts += ["## Method", "", str(method)[:1500], ""]
    parts += [
        "## Remediation",
        "",
        str(remediation),
        "",
        "## Acceptance criteria",
        "",
        "- [ ] Root-cause path fixed or docs/CI SSOT aligned",
        "- [ ] Focused verification command documented in closeout comment",
        "- [ ] No tech-debt budget increases",
        f"- [ ] Re-audit domain `{finding['domain_id']}` does not regress finding `{finding['id']}`",
        "",
        "## Evidence",
        "",
        "- Rollup: `reports/audit-runs/latest-nine-domain/findings-index.json`",
        f"- Domain report: `reports/audit/{dpath}/report.md`",
        f"- Domain findings: `reports/audit/{dpath}/findings.json`",
        "",
        "## Non-goals",
        "",
        "- Do not invent green states",
        "- Do not raise lifecycle/debt budgets",
        "- Do not close as NOT_PROVEN without re-running domain audit",
        "",
    ]
    return "\n".join(parts)


def parent_body(index: dict) -> str:
    rows = []
    for ds in index["domain_scores"]:
        rows.append(
            f"| {ds['domain_id']} | {ds['surface_score']} | {ds['finding_count']} | {ds['p0_p1_count']} |"
        )
    table = "\n".join(rows)
    steps = "\n".join(
        f"{i}. {s}" for i, s in enumerate(index["recommended_next_steps"], 1)
    )
    return f"""## Nine-domain audit rollup (2026-08-11)

| Field | Value |
| --- | --- |
| Run | `nine-domain-audit` |
| Args | domains=all, language=ru, mode=audit |
| overall_surface_score | **{index["overall_surface_score"]}** (acceptable) |
| gate | **{index["gate"]}** |
| Findings | {index["all_findings_total"]} total · {index["proven_findings_total"]} PROVEN · {index["not_proven_findings_total"]} NOT_PROVEN |
| P0+P1 | **{index["p0_p1_count"]}** |
| Blocked domains | {index["blocked_domains"]} |

### Domain scores

| Domain | score | findings | P0/P1 |
| --- | ---: | ---: | ---: |
{table}

### Evidence

- `reports/audit-runs/latest-nine-domain/final-summary.md`
- `reports/audit-runs/latest-nine-domain/findings-index.json`
- Per-domain: `reports/audit/<domain>/report.md` + `findings.json`

### Recommended order

{steps}

### Scope of child issues

This parent tracks **{index["p0_p1_count"]} PROVEN P0/P1** findings only. P2/P3 and NOT_PROVEN remain in the rollup unless promoted later.

### Guards

- No tech-debt budget increases
- No invented findings
- Close children with verification evidence; re-audit domain when closing clusters
"""


def prepare() -> dict:
    index = load_index()
    enriched = load_enriched(index)
    OUT.mkdir(parents=True, exist_ok=True)

    parent = {
        "title": (
            "[nine-domain-audit 2026-08-11] Parent: surface score "
            f"{index['overall_surface_score']} / {index['gate']} · "
            f"{index['p0_p1_count']} P0+P1"
        ),
        "body": parent_body(index),
        "labels": ["audit", "priority:high", "meta"],
    }
    (OUT / "00-parent.json").write_text(
        json.dumps(parent, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    children: list[dict] = []
    for finding in index["top_findings"]:
        obs = str(finding.get("observation") or "")
        title = (
            f"[nine-domain-audit][{finding['priority']}][{finding['domain_id']}] "
            f"{finding['id']}: {obs[:90]}"
        )
        if len(title) > 200:
            title = title[:197] + "..."
        payload = {
            "id": finding["id"],
            "domain_id": finding["domain_id"],
            "priority": finding["priority"],
            "title": title,
            "body": body_for(finding, enriched, parent_ref="(parent pending)"),
            "labels": labels_for(finding["domain_id"], finding["priority"]),
        }
        children.append(payload)
        (OUT / f"{finding['id']}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    manifest = {
        "schema_version": 1,
        "campaign": "nine-domain-audit-20260811",
        "parent_title": parent["title"],
        "child_count": len(children),
        "children": [
            {"id": c["id"], "title": c["title"], "labels": c["labels"]}
            for c in children
        ],
    }
    (OUT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return {"parent": parent, "children": children, "manifest": manifest}


def create_issue(title: str, body: str, labels: list[str]) -> dict:
    # Filter labels that exist; gh fails hard on unknown labels.
    existing = _run(["gh", "label", "list", "--limit", "200", "--json", "name"])
    known: set[str] = set()
    if existing.returncode == 0 and existing.stdout.strip():
        known = {item["name"] for item in json.loads(existing.stdout)}
    use_labels = [label for label in labels if not known or label in known]
    cmd = [
        "gh",
        "issue",
        "create",
        "--title",
        title,
        "--body",
        body,
    ]
    for label in use_labels:
        cmd.extend(["--label", label])
    proc = _run(cmd)
    if proc.returncode != 0:
        # retry without optional labels if label failure
        if "label" in (proc.stderr or "").lower():
            cmd2 = [
                "gh",
                "issue",
                "create",
                "--title",
                title,
                "--body",
                body,
                "--label",
                "audit",
            ]
            proc = _run(cmd2)
    if proc.returncode != 0:
        raise RuntimeError(f"gh issue create failed: {proc.stderr or proc.stdout}")
    url = (proc.stdout or "").strip().splitlines()[-1].strip()
    number = int(url.rstrip("/").split("/")[-1])
    return {"url": url, "number": number, "labels": use_labels}


def create_all() -> dict:
    prepared = prepare()
    parent = prepared["parent"]
    print(f"Creating parent: {parent['title']}")
    parent_res = create_issue(parent["title"], parent["body"], parent["labels"])
    parent_ref = f"#{parent_res['number']}"
    print(f"  -> {parent_res['url']}")

    created = []
    for child in prepared["children"]:
        body = child["body"].replace("(parent pending)", parent_ref)
        print(f"Creating {child['id']}: {child['title'][:80]}")
        res = create_issue(child["title"], body, child["labels"])
        print(f"  -> {res['url']}")
        created.append(
            {
                "id": child["id"],
                "number": res["number"],
                "url": res["url"],
                "title": child["title"],
            }
        )

    # Comment on parent with child list
    lines = [
        "## Child issues (PROVEN P0/P1)",
        "",
        "| Finding | Issue |",
        "| --- | --- |",
    ]
    for item in created:
        lines.append(f"| `{item['id']}` | #{item['number']} |")
    comment = "\n".join(lines) + "\n"
    _run(
        [
            "gh",
            "issue",
            "comment",
            str(parent_res["number"]),
            "--body",
            comment,
        ]
    )

    result = {
        "parent": parent_res,
        "children": created,
        "count": len(created),
    }
    (OUT / "CREATED.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    if not args.prepare_only and not args.create:
        args.create = True
    prepared = prepare()
    print(f"Prepared {prepared['manifest']['child_count']} child payloads in {OUT}")
    if args.prepare_only and not args.create:
        return 0
    result = create_all()
    print(
        json.dumps(
            {
                "parent": result["parent"]["url"],
                "created": result["count"],
                "children": [c["url"] for c in result["children"]],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
