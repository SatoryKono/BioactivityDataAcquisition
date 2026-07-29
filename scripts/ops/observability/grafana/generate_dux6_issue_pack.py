#!/usr/bin/env python3
"""Generate DUX6 residual issue pack from re-submitted screenshot readability audit."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ISSUES = ROOT / ".github" / "ISSUES"
BODIES = ISSUES / "_dux6_bodies"
PACK = ISSUES / "DUX6-2026-07-29-DASHBOARD-READABILITY-REAUDIT-RESIDUAL-ISSUE-PACK.md"
ROADMAP = ROOT / "reports" / "quality" / "_ux_audit_roadmap_parsed_reaudit.json"

CODE_MAP = {
    "UX-P0-01": "DUX6-01",
    "UX-P0-02": "DUX6-02",
    "UX-P0-03": "DUX6-03",
    "UX-P0-04": "DUX6-04",
    "UX-P0-05": "DUX6-05",
    "UX-P0-06": "DUX6-06",
    "UX-P1-01": "DUX6-10",
    "UX-P1-02": "DUX6-11",
    "UX-P1-03": "DUX6-12",
    "UX-P1-04": "DUX6-13",
    "UX-P1-05": "DUX6-14",
    "UX-P2-01": "DUX6-20",
    "UX-P2-02": "DUX6-21",
    "UX-P2-03": "DUX6-22",
    "UX-P2-04": "DUX6-23",
    "UX-P3-01": "DUX6-30",
    "UX-P3-02": "DUX6-31",
}
WAVE = {"P0": "V1", "P1": "V2", "P2": "V3", "P3": "V4"}
PREFIX = {
    "DUX6-01": "feat(grafana)",
    "DUX6-02": "refactor(grafana)",
    "DUX6-03": "fix(grafana)",
    "DUX6-04": "fix(grafana)",
    "DUX6-05": "fix(grafana)",
    "DUX6-06": "feat(grafana)",
    "DUX6-10": "chore(grafana)",
    "DUX6-11": "feat(grafana)",
    "DUX6-12": "refactor(grafana)",
    "DUX6-13": "refactor(grafana)",
    "DUX6-14": "refactor(grafana)",
    "DUX6-20": "docs(grafana)",
    "DUX6-21": "refactor(grafana)",
    "DUX6-22": "refactor(grafana)",
    "DUX6-23": "fix(grafana)",
    "DUX6-30": "docs(grafana)",
    "DUX6-31": "test(grafana)",
}
PRED = {
    "DUX6-01": "#7117 DUX5-01 closed — residual: bare UNKNOWN still dominates without reason chip",
    "DUX6-02": "#7118 DUX5-02 closed — residual: re-audit still reports triage scroll in places",
    "DUX6-03": "#7119 DUX5-03 closed — residual: Not started / red-zero needs live pixel proof",
    "DUX6-04": "#7120 DUX5-04 closed — residual: Provider titles/copy under live capture",
    "DUX6-05": "#7121 DUX5-05 closed — residual: Value #* may still render live without aliases",
    "DUX6-06": "#7122 DUX5-06 closed — residual: short-ID + Copy not fully operator-visible",
    "DUX6-10": "#7123 DUX5-10 closed — residual: enforce typography floors in render evidence",
    "DUX6-11": "#7124 DUX5-11 closed — residual: Status still occupies full surface vs card",
    "DUX6-12": "#7125 DUX5-12 closed — residual: Approach B titles; operator nouns in cards only",
    "DUX6-13": "#7126 DUX5-13 closed — residual: full UUID selectors + numeric nav prefixes",
    "DUX6-14": "#7127 DUX5-14 closed — residual: Run context density under live provision",
    "DUX6-20": "#7128 DUX5-20 closed — residual: Run Explorer layers/artifacts still verbose",
    "DUX6-21": "#7129 DUX5-21 closed — residual: Trust dense identity tables (narrow capture)",
    "DUX6-22": "#7130 DUX5-22 closed — residual: empty-chart No data patterns inconsistent",
    "DUX6-23": "#7131 DUX5-23 closed — residual: 100.00% drift if overrides regress",
    "DUX6-30": "#7132 DUX5-30 closed — residual: library-panel extraction deferred",
    "DUX6-31": "#7133 DUX5-31 closed — residual: live render matrix not automated",
}
SG = {
    "DUX6-01": "SG-01..SG-07",
    "DUX6-02": "SG-01,02,03,06,07",
    "DUX6-03": "SG-07,05,03,04",
    "DUX6-04": "SG-04,06,07,01",
    "DUX6-05": "SG-02 Incident + tables",
    "DUX6-06": "SG-01..SG-07 selectors/identity",
    "DUX6-10": "all",
    "DUX6-11": "status-dominant boards",
    "DUX6-12": "all titles",
    "DUX6-13": "all nav/selectors",
    "DUX6-14": "non-explorer Run context",
    "DUX6-20": "SG-01,02,03,07",
    "DUX6-21": "SG-01,07",
    "DUX6-22": "SG-03..07 empty charts",
    "DUX6-23": "SG-03 scores; rates",
    "DUX6-30": "docs/system",
    "DUX6-31": "all groups + viewports",
}


def left_strip(text: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    indents = [
        len(line) - len(line.lstrip(" "))
        for line in lines
        if line.strip() and line.startswith(" ")
    ]
    if not indents:
        return text
    common = Counter(indents).most_common(1)[0][0]
    return "\n".join(
        line[common:] if line.startswith(" " * common) else line for line in lines
    )


def main() -> None:
    items = json.loads(ROADMAP.read_text(encoding="utf-8"))
    titles = {
        "DUX6-00": (
            "chore(grafana): DUX6 epic — screenshot readability re-audit residual after DUX5"
        )
    }
    meta: dict[str, tuple[str, str]] = {"DUX6-00": ("meta", "epic")}
    for it in items:
        dux = CODE_MAP[it["code"]]
        meta[dux] = (it["priority"], WAVE[it["priority"]])
        titles[dux] = f"{PREFIX[dux]}: {dux} {it['title']} (residual)"

    BODIES.mkdir(parents=True, exist_ok=True)

    epic = left_strip(
        """
        ## Summary

        Execute **DUX6 residual** after closed **DUX5** (#7116) against the **re-submitted
        screenshot readability audit** (SG-01..SG-07; WARN / redesign required).

        DUX5 delivered interface-layer contracts, compact triage text, copy dictionary, and
        residual applicator. This re-audit still shows the **same operator risks at pixel level**:
        bare UNKNOWN, giant OK/100%/0, reason/impact/action under fold or scroll, Value # headers,
        full UUIDs, false-precision scores.

        **DUX6 = live/pixel enforcement + residual gaps DUX5 did not fully eliminate under screenshots.**

        ## Mode of source audit

        - Read-only, screenshot-based (no JSON/Prometheus/API changes during audit capture)
        - Image size is not proof of browser viewport; live validation required

        ## Predecessor

        - DUX5 epic #7116 (closed) + children #7117–#7133
        - Closeout: `reports/quality/dux5-2026-07-29-closeout.md`
        - Applicator: `scripts/ops/observability/grafana/apply_dux5_residual.py`
        - No-scroll helper: `scripts/ops/observability/grafana/_fix_no_scroll_triage_panels.py`

        ## Waves

        | Wave | Codes | Focus |
        | --- | --- | --- |
        | V1 | DUX6-01..06 | P0 semantic safety residual (live pixels) |
        | V2 | DUX6-10..14 | P1 system patterns residual |
        | V3 | DUX6-20..23 | P2 density residual |
        | V4 | DUX6-30..31 | P3 governance + live regression residual |

        ## Portfolio (7 UIDs)

        Trust / Overview / Pipeline Diagnostics / Provider Health / Data Quality / Incident / Run Explorer

        ## Reading order

        Context → Status → Reason → Impact → Action → Evidence

        ## Constraints

        - 7 stable UIDs; surgical JSON; ADR-010
        - No invent metrics; no Prom `run_id` labels
        - Incident read-only; titles contract-stable (DUX4-01 Approach B) unless harness updated
        - Verdict semantics outside Grafana transforms
        - Tech-debt budgets non-increasing

        ## Out of scope

        - Greenfield rewrite; delete UIDs; incident write-path; MTT* claims

        ## Publish

        Fill Issue column + `reports/quality/dux6-2026-07-29-issue-publish.json` after create.
        """
    )
    (BODIES / "DUX6-00.md").write_text(epic, encoding="utf-8")

    for it in items:
        dux = CODE_MAP[it["code"]]
        pri, wave = meta[dux]
        body = left_strip(
            f"""
            ## Summary

            **{it["title"]}** (residual after DUX5)

            {it["problem"]}

            ## Priority / wave

            - Priority: **{pri}**
            - Wave: **{wave}**
            - Complexity: **{it["complexity"]}**
            - Audit code: `{it["code"]}`
            - DUX code: `{dux}`

            ## Scope

            {it["scope"]}

            Render groups: {SG[dux]}

            ## Concrete change

            {it["change"]}

            ## Expected effect

            {it["effect"]}

            ## Acceptance criteria

            - {it["acceptance"]}
            - Live/screenshot evidence at 1366×768 (blocking) after change
            - No new high-cardinality Prometheus labels
            - No hidden verdict logic only in Grafana transforms

            ## Dependencies

            {it["deps"]}

            ## Risk

            {it["risk"]}

            ## Predecessor / residual notes

            {PRED[dux]}

            ## Constraints

            - Surgical dashboard JSON; preserve panel IDs where possible
            - Prefer description/runbook for caveats; first-screen ≤2–4 lines
            - Tech-debt budgets non-increasing

            ## Verification

            - [ ] Before/after screenshots (dark)
            - [ ] Viewports 1366/1440/1920 @100% (125% if layout-sensitive)
            - [ ] Targeted pytest if JSON structure changes
            - [ ] 5-second operator comprehension on first-screen card

            ## Parent

            DUX6 epic (`DUX6-00`)
            """
        )
        (BODIES / f"{dux}.md").write_text(body, encoding="utf-8")

    title_lines = ["# DUX6 issue titles", ""]
    for code, title in titles.items():
        title_lines.append(f"- `{code}`: `{title}`")
    (BODIES / "TITLES.md").write_text("\n".join(title_lines) + "\n", encoding="utf-8")

    rows = [
        "| Code | Issue | Pri | Wave | Title |",
        "|------|-------|-----|------|-------|",
        f"| DUX6-00 | _TBD_ | meta | epic | {titles['DUX6-00']} |",
    ]
    for it in items:
        dux = CODE_MAP[it["code"]]
        pri, wave = meta[dux]
        rows.append(f"| {dux} | _TBD_ | {pri} | {wave} | {titles[dux]} |")

    pack = left_strip(
        f"""
        # Dashboard readability re-audit residual — DUX6

        **Status:** prepared (local pack; GH numbers filled after publish)
        **Wave code:** DUX6
        **Date:** 2026-07-29
        **Source audit:** re-submitted screenshot UX audit SG-01..SG-07 (WARN / redesign required)
        **Predecessor:** DUX5 epic #7116 (closed #7117–#7133)
        **Audit mode:** read-only screenshot-based; no JSON/Prometheus/API edits during capture

        ## Context

        DUX5 closed **contract/copy residual** from the same audit family. The re-submitted
        screenshot report still rates the portfolio **WARN / redesign required** because
        operator-visible pixels still allow dangerous interpretations (bare UNKNOWN, giant
        100%/0, scroll/clipping, full UUIDs, Value # headers).

        **DUX6 = residual live/pixel enforcement after DUX5.**

        ## Critical P0

        1. Formal Health/Execution/Evidence/Applicability instead of bare UNKNOWN/No data/VALID_EMPTY/0
        2. No internal scroll on mandatory triage; Status/Reason/Impact/Action simultaneous
        3. Fix literal Markdown, Value #*, clipping, metric/copy mismatch (Provider)
        4. Not started for inapplicable Silver/Gold; red only for confirmed failure

        ## Critical P1

        1. Neutral surface + severity strip vs full-color stat backgrounds
        2. Short IDs + Copy/Open
        3. Typography tokens + no auto-shrink below floors

        ## Issue matrix

        {chr(10).join(rows)}

        ## Delivery order

        1. V1 P0: DUX6-01 → 02 → 03 → 04 → 05 → 06
        2. V2 P1: DUX6-10 → 11 → 12 → 13 → 14
        3. V3 P2: DUX6-20 → 21 → 22 → 23
        4. V4 P3: DUX6-30 → 31

        ## Exit criteria (summary)

        ### V1
        - Live first-screen cards never show bare UNKNOWN without reason class
        - Zero internal scroll on Status/Provenance/First Action/Next actions at 1366
        - Red zero only on validated failure; Not started labelled
        - No Value #* / raw endpoints / VALID_EMPTY tokens in bodies
        - Short IDs + copy path without Prom cardinality

        ### V2–V4
        - Typography floors enforced in render evidence
        - Status card pattern dominant; compact run strip outside explorer
        - Tables/charts/copy residual closed
        - Live screenshot matrix + governance owners documented

        ## Constraints

        - 7 UIDs; no invent metrics; no Prom run_id; incident read-only
        - Titles Approach B unless harness lands first
        - Verdict logic outside Grafana transforms

        ## Evidence

        - Parsed roadmap: `reports/quality/_ux_audit_roadmap_parsed_reaudit.json`
        - Bodies: `.github/ISSUES/_dux6_bodies/`
        - DUX5 closeout: `reports/quality/dux5-2026-07-29-closeout.md`
        - Docs: `dux5-copy-dictionary.md`, `dux5-screenshot-regression-protocol.md`

        ## Publish record

        - After publish: `reports/quality/dux6-2026-07-29-issue-publish.json`
        """
    )
    PACK.write_text(pack, encoding="utf-8")

    meta_lines = ",\n".join(
        f'    "{code}": ("{pri}", "{wave}")' for code, (pri, wave) in meta.items()
    )
    publish = left_strip(
        f'''
        #!/usr/bin/env python3
        """Publish DUX6 epic + children via GitHub CLI."""
        from __future__ import annotations

        import argparse
        import json
        import os
        import re
        import subprocess
        from datetime import datetime, timezone
        from pathlib import Path
        from typing import TypedDict

        ROOT = Path(__file__).resolve().parents[3]
        BODIES = Path(__file__).resolve().parent
        PACK = ROOT / ".github" / "ISSUES" / "DUX6-2026-07-29-DASHBOARD-READABILITY-REAUDIT-RESIDUAL-ISSUE-PACK.md"
        PUBLISH = ROOT / "reports" / "quality" / "dux6-2026-07-29-issue-publish.json"
        TITLES_PATH = BODIES / "TITLES.md"

        class PublishedIssue(TypedDict):
            code: str
            number: int
            priority: str
            wave: str
            url: str
            title: str

        META: dict[str, tuple[str, str]] = {{
        {meta_lines}
        }}
        CHILD_ORDER = [c for c in META if c != "DUX6-00"]

        def load_titles() -> dict[str, str]:
            titles: dict[str, str] = {{}}
            for line in TITLES_PATH.read_text(encoding="utf-8").splitlines():
                m = re.match(r"- `(DUX6-\\d+)`: `(.*)`\\s*$", line)
                if m:
                    titles[m.group(1)] = m.group(2)
            missing = set(META) - set(titles)
            if missing:
                raise SystemExit(f"missing titles for: {{sorted(missing)}}")
            return titles

        def resolve_gh() -> str:
            for candidate in (
                os.environ.get("GH") or "",
                r"C:\\Program Files\\GitHub CLI\\gh.exe",
                "/c/Program Files/GitHub CLI/gh.exe",
                "gh",
            ):
                if candidate and (candidate == "gh" or Path(candidate).exists()):
                    return candidate
            return "gh"

        def run_gh(gh: str, args: list[str], *, dry_run: bool) -> str:
            cmd = [gh, *args]
            if dry_run:
                print("DRY-RUN:", " ".join(cmd))
                return "https://github.com/example/repo/issues/0"
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                raise SystemExit(
                    f"gh failed ({{proc.returncode}}): {{proc.stderr or proc.stdout}}"
                )
            return (proc.stdout or "").strip()

        def create_issue(
            gh: str,
            *,
            title: str,
            body_path: Path,
            labels: list[str],
            dry_run: bool,
        ) -> tuple[int, str]:
            args = [
                "issue",
                "create",
                "--title",
                title,
                "--body-file",
                str(body_path),
            ]
            for label in labels:
                args.extend(["--label", label])
            url = run_gh(gh, args, dry_run=dry_run)
            if dry_run:
                return 0, url
            m = re.search(r"/issues/(\\d+)\\s*$", url)
            if not m:
                raise SystemExit(f"could not parse issue number from: {{url!r}}")
            return int(m.group(1)), url

        def main() -> int:
            parser = argparse.ArgumentParser()
            parser.add_argument("--dry-run", action="store_true")
            args = parser.parse_args()
            codex = os.environ.get("CODEX_GITHUB_PERSONAL_ACCESS_TOKEN")
            if codex:
                os.environ["GH_TOKEN"] = codex
                os.environ.pop("GITHUB_TOKEN", None)
            titles = load_titles()
            gh = resolve_gh()
            labels_epic = ["grafana", "observability", "technical-debt"]
            labels_child = ["grafana", "observability"]
            created: list[PublishedIssue] = []
            epic_num, epic_url = create_issue(
                gh,
                title=titles["DUX6-00"],
                body_path=BODIES / "DUX6-00.md",
                labels=labels_epic,
                dry_run=args.dry_run,
            )
            created.append(
                {{
                    "code": "DUX6-00",
                    "number": epic_num,
                    "priority": "meta",
                    "wave": "epic",
                    "url": epic_url,
                    "title": titles["DUX6-00"],
                }}
            )
            for code in CHILD_ORDER:
                pri, wave = META[code]
                body_path = BODIES / f"{{code}}.md"
                if not args.dry_run and epic_num:
                    text = body_path.read_text(encoding="utf-8")
                    if f"#{{epic_num}}" not in text:
                        body_path.write_text(
                            text.replace(
                                "DUX6 epic (`DUX6-00`)",
                                f"DUX6 epic (#{{epic_num}})",
                            ),
                            encoding="utf-8",
                        )
                num, url = create_issue(
                    gh,
                    title=titles[code],
                    body_path=body_path,
                    labels=labels_child,
                    dry_run=args.dry_run,
                )
                created.append(
                    {{
                        "code": code,
                        "number": num,
                        "priority": pri,
                        "wave": wave,
                        "url": url,
                        "title": titles[code],
                    }}
                )
                print(f"created {{code}} -> {{url}}")
            record = {{
                "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "owner": "SatoryKono",
                "repo": "BioactivityDataAcquisition",
                "wave": "dux6-dashboard-readability-reaudit-residual-2026-07-29",
                "issue_pack": str(PACK.relative_to(ROOT)).replace("\\\\", "/"),
                "source_audit": "BIOETL-GRAFANA-UX-SCREENSHOT-READABILITY-REAUDIT-2026-07-29",
                "predecessors": {{
                    "dux5_epic": 7116,
                    "dux4_epic": 7088,
                    "dux3_epic": 7053,
                }},
                "epic": epic_num,
                "created": created,
                "dry_run": args.dry_run,
            }}
            if not args.dry_run:
                PUBLISH.parent.mkdir(parents=True, exist_ok=True)
                PUBLISH.write_text(
                    json.dumps(record, indent=2, ensure_ascii=False) + "\\n",
                    encoding="utf-8",
                )
                print(f"wrote {{PUBLISH}}")
            else:
                print(json.dumps(record, indent=2, ensure_ascii=False))
            return 0

        if __name__ == "__main__":
            raise SystemExit(main())
        '''
    )
    (BODIES / "publish_dux6_issues.py").write_text(publish, encoding="utf-8")

    idx = [
        "# DUX6 bodies",
        "",
        "| Code | Pri | Wave | File |",
        "| --- | --- | --- | --- |",
        "| DUX6-00 | meta | epic | [DUX6-00.md](./DUX6-00.md) |",
    ]
    for it in items:
        dux = CODE_MAP[it["code"]]
        pri, wave = meta[dux]
        idx.append(f"| {dux} | {pri} | {wave} | [{dux}.md](./{dux}.md) |")
    (BODIES / "README.md").write_text("\n".join(idx) + "\n", encoding="utf-8")

    print(f"wrote {PACK}")
    print(f"bodies={len(list(BODIES.glob('DUX6-*.md')))}")
    for code, title in titles.items():
        print(f"  {code}: {title}")


if __name__ == "__main__":
    main()
