"""Build open critical/major residual inventory + 5 independent streams."""
from __future__ import annotations

import json
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path

OUT = Path("reports/quality/coderabbit/_live")
REPO = "SatoryKono/BioactivityDataAcquisition"


def strip_ansi(raw: bytes) -> str:
    return re.sub(rb"\x1b\[[0-9;]*m", b"", raw).decode("utf-8", errors="replace").strip()


def load_search(path: Path) -> list[dict]:
    text = strip_ansi(path.read_bytes())
    dec = json.JSONDecoder()
    idx = 0
    items: list[dict] = []
    while idx < len(text):
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text):
            break
        obj, end = dec.raw_decode(text, idx)
        idx = end
        if isinstance(obj, dict) and "items" in obj:
            items.extend(obj["items"])
    return items


def sev_of(title: str) -> str | None:
    m = re.search(r"\[(critical|major|minor|trivial)\]", (title or "").lower())
    return m.group(1) if m else None


def path_from_title(title: str) -> str:
    m = re.search(r"`([^`]+)`", title or "")
    if not m:
        return ""
    p = m.group(1)
    if p.endswith("..."):
        return ""
    return p


def path_from_body(body: str) -> str:
    if not body:
        return ""
    m = re.search(r"Path cluster:\s*`([^`]+)`", body)
    if m:
        return m.group(1)
    m = re.search(r"`(src/[^`]+)`", body)
    return m.group(1) if m else ""


def gh_issue(n: int) -> dict:
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["CLICOLOR"] = "0"
    env["CLICOLOR_FORCE"] = "0"
    env["GH_FORCE_TTY"] = "0"
    env["TERM"] = "dumb"
    r = subprocess.run(
        [
            "gh",
            "issue",
            "view",
            str(n),
            "--repo",
            REPO,
            "--json",
            "number,title,body",
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=env,
    )
    if r.returncode != 0:
        raise RuntimeError(f"gh issue view {n}: {(r.stderr or '')[:300]}")
    text = strip_ansi((r.stdout or "").encode("utf-8", errors="replace"))
    return json.loads(text)


def is_batch_path(p: str) -> bool:
    p = p.replace("\\", "/")
    name = p.rsplit("/", 1)[-1]
    markers = (
        "/batch_",
        "batch_transformer",
        "batch_executor",
        "batch_writer",
        "batch_processing",
        "batch_memory",
        "batch_metrics",
        "batch_progress",
        "batch_runtime",
        "/_batch_",
    )
    if any(x in p for x in markers):
        return True
    if name.startswith("batch_") or name.startswith("_batch_"):
        return True
    return False


def stream_of(sev: str, path: str) -> str:
    p = path.replace("\\", "/")
    if sev == "critical" or "workflow_foreign_key_reconciliation" in p:
        return "P1 critical-storage-FK"
    if p.startswith("src/bioetl/domain"):
        return "P5 observability+domain"
    if p.startswith("src/bioetl/application"):
        if is_batch_path(p):
            return "P2 application-batch"
        return "P3 application-core-other"
    if p.startswith("src/bioetl/infrastructure/storage"):
        return "P4 infrastructure-storage"
    if p.startswith("src/bioetl/infrastructure/observability"):
        return "P5 observability+domain"
    if p.startswith("src/bioetl/infrastructure"):
        return "P4 infrastructure-storage"
    return "P5 observability+domain"


def main() -> None:
    token = os.environ.get("CODEX_GITHUB_PERSONAL_ACCESS_TOKEN") or os.environ.get(
        "GH_TOKEN", ""
    )
    if token:
        os.environ["GH_TOKEN"] = token
    os.environ["NO_COLOR"] = "1"

    by: dict[int, dict] = {}
    for it in load_search(OUT / "search_residual_title.json") + load_search(
        OUT / "search_cr_residual.json"
    ):
        by[it["number"]] = it

    cm: list[tuple[str, int, str]] = []
    for n, it in by.items():
        s = sev_of(it.get("title", ""))
        if s in ("critical", "major"):
            cm.append((s, n, it.get("title", "")))

    resolved: dict[int, tuple[str, str, str]] = {}
    need_body: list[int] = []
    for s, n, t in cm:
        p = path_from_title(t)
        if p:
            resolved[n] = (s, p, t)
        else:
            need_body.append(n)

    print(f"CM={len(cm)} need_body={need_body}")
    for n in need_body:
        data = gh_issue(n)
        s = sev_of(data.get("title", "")) or "?"
        p = path_from_body(data.get("body", "")) or path_from_title(
            data.get("title", "")
        )
        if not p:
            p = "(unknown)"
        resolved[n] = (s, p, data.get("title", ""))
        print(f"  resolved #{n} -> {p}")

    streams: dict[str, list[tuple[int, str, str, str]]] = defaultdict(list)
    for n, (s, p, t) in resolved.items():
        streams[stream_of(s, p)].append((n, s, p, t))

    order = [
        "P1 critical-storage-FK",
        "P2 application-batch",
        "P3 application-core-other",
        "P4 infrastructure-storage",
        "P5 observability+domain",
    ]

    n_crit = sum(1 for s, _, _ in cm if s == "critical")
    n_maj = sum(1 for s, _, _ in cm if s == "major")

    roots = {
        "P1 critical-storage-FK": "`infrastructure/storage/workflow_foreign_key_reconciliation*`",
        "P2 application-batch": "`application/core/batch_*`, `_batch_*`",
        "P3 application-core-other": "`application/core/*` (non-batch)",
        "P4 infrastructure-storage": "`infrastructure/storage/*` except FK reconciliation*",
        "P5 observability+domain": "`infrastructure/observability/*` + `domain/ports/*`",
    }

    lines: list[str] = []
    lines.append("# Open CodeRabbit residual — CRITICAL + MAJOR")
    lines.append("")
    lines.append(
        "Источник: live `gh` search (`residual in:title` ∪ `CodeRabbit residual`), "
        f"repo `{REPO}`."
    )
    lines.append("")
    lines.append("| Severity | Open |")
    lines.append("|----------|-----:|")
    lines.append(f"| **critical** | **{n_crit}** |")
    lines.append(f"| **major** | **{n_maj}** |")
    lines.append(f"| **TOTAL C+M** | **{len(cm)}** |")
    lines.append("")
    lines.append("## CRITICAL")
    lines.append("")
    for n, (s, p, t) in sorted(resolved.items()):
        if s != "critical":
            continue
        lines.append(f"- **#{n}** — `{p}`")
        lines.append(f"  {t}")
    if n_crit == 0:
        lines.append("_Нет открытых critical residual path-cluster issues._")
    lines.append("")
    lines.append("## MAJOR (полный список по path)")
    lines.append("")
    for n, (s, p, t) in sorted(resolved.items(), key=lambda x: (x[1][1], x[0])):
        if s != "major":
            continue
        lines.append(f"- **#{n}** — `{p}`")
    lines.append("")
    lines.append("## 5 независимых потоков (exclusive path ownership)")
    lines.append("")
    lines.append("```")
    lines.append("P1 critical FK storage ──┐")
    lines.append("P2 application batch  ──┼── parallel worktrees")
    lines.append("P3 application other  ──┤")
    lines.append("P4 infra storage       ──┤")
    lines.append("P5 obs + domain        ──┘")
    lines.append("```")
    lines.append("")
    lines.append("| Stream | Paths (exclusive) | Issues | Sample IDs |")
    lines.append("|--------|-------------------|-------:|------------|")
    for name in order:
        items = sorted(streams.get(name, []), key=lambda x: x[0])
        ids = ", ".join(f"#{n}" for n, _, _, _ in items[:8])
        if len(items) > 8:
            ids += f", … +{len(items) - 8}"
        lines.append(f"| **{name}** | {roots[name]} | {len(items)} | {ids} |")
    lines.append("")

    for name in order:
        items = sorted(streams.get(name, []), key=lambda x: (x[1] != "critical", x[0]))
        lines.append(f"### {name} ({len(items)})")
        lines.append("")
        for n, s, p, t in items:
            badge = "CRITICAL " if s == "critical" else ""
            lines.append(f"- {badge}**#{n}** `{p}`")
        lines.append("")

    lines.append("## Правила параллелизма")
    lines.append("")
    lines.append("1. Один worktree / agent на stream; path ownership не пересекается.")
    lines.append(
        "2. **P1 (critical) — highest priority**; файлы FK reconciliation не трогать из P4."
    )
    lines.append(
        "3. P2 и P3 оба под `application/core/`, но разные файлы "
        "(batch_* vs остальное) — не править «чужие» файлы."
    )
    lines.append("4. Не увеличивать бюджеты техдолга.")
    lines.append("5. После PR: close issue + evidence; пересчёт inventory.")
    lines.append("")

    text = "\n".join(lines)
    outp = OUT / "OPEN_CRITICAL_MAJOR_STREAMS.md"
    outp.write_text(text, encoding="utf-8")
    print(f"wrote {outp} ({len(text)} bytes)")
    print(f"CRITICAL={n_crit} MAJOR={n_maj}")
    for name in order:
        print(f"  {name}: {len(streams.get(name, []))}")

    payload = {
        "critical": [
            {"number": n, "path": p, "title": t}
            for n, (s, p, t) in sorted(resolved.items())
            if s == "critical"
        ],
        "major": [
            {"number": n, "path": p, "title": t}
            for n, (s, p, t) in sorted(resolved.items())
            if s == "major"
        ],
        "streams": {
            name: [
                {"number": n, "severity": s, "path": p}
                for n, s, p, _t in sorted(streams.get(name, []), key=lambda x: x[0])
            ]
            for name in order
        },
    }
    (OUT / "open_cm_streams.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
