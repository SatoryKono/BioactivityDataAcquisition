#!/usr/bin/env python3
"""Normalize CodeRabbit agent NDJSON into FINDINGS.md and open net-new GH issues.

Usage (WSL):
  python3 scripts/ops/_cr_publish_findings.py \\
    --artifact-dir /mnt/c/Users/Fedor/bioetl-cr-artifacts/20260805 \\
    --wave A --parent-issue 7690 --epic 7688 \\
    --create-issues --min-severity major
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SEV_RANK = {"critical": 0, "major": 1, "minor": 2, "trivial": 3, "info": 4}


@dataclass
class Finding:
    leaf: str
    severity: str
    file_name: str
    body: str
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def claim(self) -> str:
        # Prefer first sentence of codegenInstructions after the path hint
        text = self.body.strip()
        # Drop boilerplate preamble
        text = re.sub(
            r"^Verify each finding against current code\.[^\n]*\n+",
            "",
            text,
            flags=re.I,
        )
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 280:
            text = text[:277] + "..."
        return text or "(no claim)"

    @property
    def fingerprint(self) -> str:
        key = f"{self.severity}|{self.file_name}|{self.claim[:120]}".lower()
        return hashlib.sha1(key.encode()).hexdigest()[:12]


def parse_agent_ndjson(path: Path, leaf: str) -> list[Finding]:
    out: list[Finding] = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "finding":
            continue
        sev = str(obj.get("severity") or "minor").lower()
        fname = str(obj.get("fileName") or obj.get("file") or "(unknown)")
        body = str(
            obj.get("codegenInstructions")
            or obj.get("description")
            or obj.get("message")
            or ""
        )
        out.append(Finding(leaf=leaf, severity=sev, file_name=fname, body=body, raw=obj))
    return out


def load_wave(artifact_dir: Path, wave: str) -> list[Finding]:
    findings: list[Finding] = []
    for agent in sorted(artifact_dir.glob("review_*.agent.json")):
        leaf = agent.name.removeprefix("review_").removesuffix(".agent.json")
        findings.extend(parse_agent_ndjson(agent, leaf))
    return findings


def group_for_issues(findings: list[Finding], min_severity: str) -> list[dict[str, Any]]:
    """Group major+ findings by top-level package path for one issue per root theme."""
    min_rank = SEV_RANK.get(min_severity, 1)
    actionable = [f for f in findings if SEV_RANK.get(f.severity, 9) <= min_rank]
    # Group by package path; go deeper for large trees (composition/adapters)
    buckets: dict[str, list[Finding]] = defaultdict(list)
    for f in actionable:
        parts = Path(f.file_name).parts
        if len(parts) >= 5 and parts[0] == "src" and parts[1] == "bioetl":
            # src/bioetl/<layer>/<pkg>[/<sub>]
            layer = parts[2]
            if layer in {"composition", "infrastructure", "application", "domain", "interfaces"}:
                key = "/".join(parts[:5])  # include first subpackage
            else:
                key = "/".join(parts[:4])
        elif len(parts) >= 4 and parts[0] == "src":
            key = "/".join(parts[:4])
        elif len(parts) >= 2:
            key = "/".join(parts[:2])
        else:
            key = f.file_name
        buckets[key].append(f)

    issues: list[dict[str, Any]] = []
    for key, items in sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        sev_counts = Counter(i.severity for i in items)
        worst = min(items, key=lambda x: SEV_RANK.get(x.severity, 9)).severity
        # Cap issue body findings
        top = sorted(items, key=lambda x: (SEV_RANK.get(x.severity, 9), x.file_name))[:12]
        issues.append(
            {
                "path_key": key,
                "worst": worst,
                "count": len(items),
                "sev_counts": dict(sev_counts),
                "findings": top,
                "all_findings": items,
            }
        )
    return issues


def write_findings_md(
    artifact_dir: Path,
    wave: str,
    findings: list[Finding],
    groups: list[dict[str, Any]],
    parent_issue: int,
    epic: int,
) -> Path:
    sev = Counter(f.severity for f in findings)
    lines = [
        f"# CodeRabbit Wave {wave} FINDINGS",
        "",
        f"- Parent issue: #{parent_issue}",
        f"- Epic: #{epic}",
        f"- Total findings: {len(findings)}",
        f"- Severity: {dict(sev)}",
        f"- Actionable groups (for issues): {len(groups)}",
        "",
        "## Groups (issue candidates)",
        "",
    ]
    for i, g in enumerate(groups, 1):
        lines.append(
            f"### G{i}: `{g['path_key']}` — {g['count']} findings (worst={g['worst']})"
        )
        lines.append("")
        for f in g["findings"]:
            lines.append(f"- **{f.severity}** `{f.file_name}` — {f.claim}")
        lines.append("")

    lines.append("## All findings")
    lines.append("")
    lines.append("| id | sev | leaf | path | claim |")
    lines.append("| --- | --- | --- | --- | --- |")
    for f in sorted(findings, key=lambda x: (SEV_RANK.get(x.severity, 9), x.file_name)):
        claim = f.claim.replace("|", "\\|")
        lines.append(
            f"| `{f.fingerprint}` | {f.severity} | {f.leaf} | `{f.file_name}` | {claim} |"
        )
    lines.append("")
    out = artifact_dir / f"FINDINGS_wave_{wave}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def gh_create_issue(
    title: str,
    body: str,
    labels: list[str],
    repo: str,
) -> str:
    cmd = [
        "gh",
        "issue",
        "create",
        "--repo",
        repo,
        "--title",
        title,
        "--body",
        body,
    ]
    for lab in labels:
        cmd.extend(["--label", lab])
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return proc.stdout.strip()


def load_published_keys(artifact_dir: Path, wave: str) -> set[str]:
    path = artifact_dir / f"PUBLISHED_wave_{wave}.json"
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("path_keys", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_published_keys(artifact_dir: Path, wave: str, keys: set[str], urls: list[str]) -> None:
    path = artifact_dir / f"PUBLISHED_wave_{wave}.json"
    prev: dict[str, Any] = {}
    if path.exists():
        try:
            prev = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            prev = {}
    merged_keys = sorted(set(prev.get("path_keys", [])) | keys)
    merged_urls = list(dict.fromkeys(list(prev.get("urls", [])) + urls))
    path.write_text(
        json.dumps({"path_keys": merged_keys, "urls": merged_urls}, indent=2),
        encoding="utf-8",
    )


def publish_issues(
    groups: list[dict[str, Any]],
    wave: str,
    parent_issue: int,
    epic: int,
    repo: str,
    dry_run: bool,
    max_issues: int,
    artifact_dir: Path | None = None,
) -> list[str]:
    created: list[str] = []
    published = load_published_keys(artifact_dir, wave) if artifact_dir else set()
    # Map wave to default labels
    label_map = {
        "A": ["architecture", "quality", "technical-debt", "priority:high"],
        "B": ["data-quality", "architecture", "quality", "priority:high"],
        "C": ["architecture", "quality", "priority:medium"],
        "D": ["security", "quality", "ci", "priority:high"],
        "E": ["documentation", "docs-drift", "quality", "priority:medium"],
        "F": ["testing", "architecture-tests", "quality", "priority:medium"],
    }
    labels = label_map.get(wave, ["quality", "technical-debt"])

    pending = [g for g in groups if g["path_key"] not in published]
    new_keys: set[str] = set()
    for idx, g in enumerate(pending[:max_issues], 1):
        worst = g["worst"]
        title = (
            f"[CR-FULL][Wave {wave}][{worst}] residual in `{g['path_key']}` "
            f"({g['count']} findings)"
        )
        if len(title) > 120:
            title = title[:117] + "..."
        bullets = []
        for f in g["findings"]:
            bullets.append(f"- **{f.severity}** `{f.file_name}`: {f.claim}")
        body = textwrap.dedent(
            f"""\
            ## Source

            - Epic: #{epic}
            - Wave parent: #{parent_issue}
            - Wave: **{wave}**
            - Path cluster: `{g['path_key']}`
            - Severity counts: `{g['sev_counts']}`

            ## Findings (top)

            {chr(10).join(bullets)}

            ## Acceptance

            - [ ] Confirm each finding against current `main` (code wins)
            - [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
            - [ ] Do **not** grow tech-debt / quality budgets
            - [ ] Prefer one root-cause PR

            ## Notes

            Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
            De-dupe against open ARCH-CR / prior packs before implementing.
            """
        )
        if dry_run:
            print(f"[dry-run] would create: {title}")
            created.append(title)
            new_keys.add(g["path_key"])
            continue
        try:
            url = gh_create_issue(title, body, labels, repo)
            print(f"created {url}")
            created.append(url)
            new_keys.add(g["path_key"])
        except subprocess.CalledProcessError as exc:
            # Retry without labels if some labels missing
            print(f"label create failed, retry plain: {exc.stderr}")
            url = gh_create_issue(title, body, [], repo)
            print(f"created {url}")
            created.append(url)
            new_keys.add(g["path_key"])
    if artifact_dir and new_keys and not dry_run:
        save_published_keys(artifact_dir, wave, new_keys, [u for u in created if u.startswith("http")])
    return created


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact-dir", required=True, type=Path)
    ap.add_argument("--wave", required=True)
    ap.add_argument("--parent-issue", type=int, required=True)
    ap.add_argument("--epic", type=int, default=7688)
    ap.add_argument("--repo", default="SatoryKono/BioactivityDataAcquisition")
    ap.add_argument("--min-severity", default="major", choices=list(SEV_RANK))
    ap.add_argument("--create-issues", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-issues", type=int, default=15)
    args = ap.parse_args()

    findings = load_wave(args.artifact_dir, args.wave)
    print(f"loaded {len(findings)} findings from {args.artifact_dir}")
    groups = group_for_issues(findings, args.min_severity)
    md = write_findings_md(
        args.artifact_dir, args.wave, findings, groups, args.parent_issue, args.epic
    )
    print(f"wrote {md}")
    print(f"groups={len(groups)} min_severity={args.min_severity}")

    summary = {
        "wave": args.wave,
        "total_findings": len(findings),
        "severity": dict(Counter(f.severity for f in findings)),
        "groups": len(groups),
        "findings_md": str(md),
    }

    if args.create_issues or args.dry_run:
        urls = publish_issues(
            groups,
            args.wave,
            args.parent_issue,
            args.epic,
            args.repo,
            dry_run=not args.create_issues,
            max_issues=args.max_issues,
            artifact_dir=args.artifact_dir,
        )
        summary["issues"] = urls

    out_json = args.artifact_dir / f"TRIAGE_wave_{args.wave}.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
