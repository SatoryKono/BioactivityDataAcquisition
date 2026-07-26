#!/usr/bin/env python3
"""Build consolidated architecture review markdown from CodeRabbit agent NDJSON."""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path


def layer_of(working_directory: str | None) -> str:
    if not working_directory:
        return "?"
    path = working_directory.replace("\\", "/")
    for suffix, name in (
        ("/src/bioetl/domain", "domain"),
        ("/src/bioetl/application", "application"),
        ("/src/bioetl/composition", "composition"),
        ("/src/bioetl/infrastructure", "infrastructure"),
        ("/src/bioetl/interfaces", "interfaces"),
        ("/tests/architecture", "tests/architecture"),
        ("/docs/02-architecture", "docs/02-architecture"),
    ):
        if suffix in path:
            return name
    return path.rsplit("/", 1)[-1]


def parse_body(text: str, file_name: str) -> tuple[str, str, str]:
    text = text or ""
    m = re.search(r"In @([^\s]+) around lines? ([^,]+),?\s*(.*)", text, re.S)
    if m:
        return m.group(1), m.group(2).strip(), " ".join(m.group(3).split())
    m = re.search(r"In @([^\s]+) at line (\d+),?\s*(.*)", text, re.S)
    if m:
        return m.group(1), m.group(2).strip(), " ".join(m.group(3).split())
    # Drop boilerplate
    body = text
    for marker in ("and validate.\n\n", "and validate.", "Validate.\n\n"):
        if marker in body:
            body = body.split(marker, 1)[-1]
            break
    return file_name, "?", " ".join(body.split())


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "usage: build_arch_review_report.py <agent.ndjson> <out.md>",
            file=sys.stderr,
        )
        return 2
    from scripts.engineering.common.repo_paths import resolve_output_path

    src = resolve_output_path(sys.argv[1])
    out = resolve_output_path(sys.argv[2])
    findings: list[dict[str, str]] = []
    completes: list[tuple[str, int]] = []
    current: str | None = None
    for raw in src.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = obj.get("type")
        if kind == "review_context":
            current = obj.get("workingDirectory")
        elif kind == "finding":
            file_name = str(obj.get("fileName") or "?")
            fpath, loc, body = parse_body(
                str(obj.get("codegenInstructions") or ""), file_name
            )
            findings.append(
                {
                    "layer": layer_of(current),
                    "severity": str(obj.get("severity") or "unknown"),
                    "file": fpath,
                    "loc": loc,
                    "body": body,
                }
            )
        elif kind == "complete":
            completes.append((layer_of(current), int(obj.get("findings") or 0)))

    by_sev = collections.Counter(f["severity"] for f in findings)
    by_layer = collections.Counter(f["layer"] for f in findings)
    order = ["critical", "major", "minor", "trivial", "info", "unknown"]
    sev_rank = {s: i for i, s in enumerate(order)}

    lines: list[str] = []
    lines.append("# CodeRabbit — исчерпывающий архитектурный обзор BioETL")
    lines.append("")
    lines.append("## Метаданные")
    lines.append("")
    lines.append("- **Инструмент:** CodeRabbit CLI 0.7.0 (`--agent` + plain summary)")
    lines.append("- **Режим:** layered hexagonal review (лимит 300 файлов/review)")
    lines.append("- **Диапазон:** `HEAD~300` → `HEAD`")
    lines.append("- **Источник findings:** agent NDJSON")
    lines.append(f"- **Файл-источник:** `{src.as_posix()}`")
    lines.append("")
    lines.append("### Статус слоёв")
    lines.append("")
    lines.append("| Layer | Agent findings | Complete event |")
    lines.append("| --- | ---: | --- |")
    complete_map = dict(completes)
    for layer in (
        "domain",
        "application",
        "composition",
        "infrastructure",
        "interfaces",
        "tests/architecture",
        "docs/02-architecture",
    ):
        n = by_layer.get(layer, 0)
        done = (
            "yes"
            if layer in complete_map
            else ("partial" if n else "not run / incomplete")
        )
        lines.append(f"| `{layer}` | {n} | {done} |")
    lines.append("")
    lines.append("## Сводка")
    lines.append("")
    lines.append(f"- **Всего agent findings:** **{len(findings)}**")
    lines.append(
        "- **По severity:** "
        + ", ".join(f"`{k}`={by_sev[k]}" for k in order if by_sev.get(k))
    )
    lines.append(
        "- **По слоям:** " + ", ".join(f"`{k}`={by_layer[k]}" for k in sorted(by_layer))
    )
    lines.append("")
    lines.append("### Архитектурные темы (сводка)")
    lines.append("")
    lines.append(
        "1. **Контракты и совместимость API** — positional fields в reconciliation ports; facade re-exports; deprecation window для `PhasedMigrationCoordinator`."
    )
    lines.append(
        "2. **Иммутабельность и целостность данных** — `FrozenList`/`FrozenDict` subclassing; deep-freeze rows; JSON key collision; replay identity override."
    )
    lines.append(
        "3. **Безопасность / redaction** — incomplete Authorization/Cookie redaction; raw `default_email` in effective-config snapshot."
    )
    lines.append(
        "4. **Async / event-loop safety** — blocking storage wrapper; sync artifact write in reconcile FK transform."
    )
    lines.append(
        "5. **Стабильность pipeline runtime** — transformer MRO recursion risk; checkpoint ranking with mixed timestamps; layer validation before write."
    )
    lines.append(
        "6. **Control-plane observability** — missing reason codes; dict payload details lost; blank step IDs on resume."
    )
    lines.append("")
    lines.append("## Findings (Critical → Trivial)")
    lines.append("")

    sorted_findings = sorted(
        findings,
        key=lambda f: (sev_rank.get(f["severity"], 99), f["layer"], f["file"]),
    )
    current_sev = None
    for idx, item in enumerate(sorted_findings, 1):
        if item["severity"] != current_sev:
            current_sev = item["severity"]
            lines.append(f"### {current_sev.upper()}")
            lines.append("")
        lines.append(
            f"{idx}. **[{item['layer']}]** `{item['file']}`"
            + (f" (lines {item['loc']})" if item["loc"] != "?" else "")
        )
        lines.append(f"   - {item['body']}")
        lines.append("")

    lines.append("## Ограничения review")
    lines.append("")
    lines.append(
        "- CodeRabbit анализирует **diff** (`HEAD~300..HEAD`), не полный статический AST-scan всего дерева."
    )
    lines.append(
        "- Полный `src/bioetl` (627 файлов) превышает лимит 300 → review выполнен по hexagonal layers."
    )
    lines.append(
        "- Worktree на native WSL FS с object alternates (обход GDrive + Windows git index extensions)."
    )
    lines.append(
        "- `composition` agent review завис на heartbeats; findings по composition **partial** (до kill)."
    )
    lines.append(
        "- `infrastructure`, `interfaces`, `tests/architecture`, `docs/02-architecture` не завершены в этом прогоне (WSL/timeout)."
    )
    lines.append(
        "- Plain mode для domain: 13 findings (Major 7 / Minor 4 / Trivial 2); application: 10 findings (Major 5 / Minor 3 / Trivial 2)."
    )
    lines.append("")
    lines.append("## Рекомендуемый порядок remediation")
    lines.append("")
    lines.append(
        "1. **Security:** redaction Authorization/Cookie; redact `default_email` in effective-config snapshot."
    )
    lines.append(
        "2. **Correctness/stability:** transformer MRO owner_type; Frozen* composition; stage complete idempotency; checkpoint timestamp compare."
    )
    lines.append(
        "3. **Contract stability:** FK reconciliation field order/keyword-only; ports facade exports; wiring `__all__`."
    )
    lines.append(
        "4. **Async integrity:** `run_storage_blocking` → `asyncio.to_thread`; reconcile artifact writes off event loop."
    )
    lines.append(
        "5. **Data integrity:** row reconcile validation; persist reconcile_rows artifacts; reject blank step IDs."
    )
    lines.append(
        "6. **DX/maintainability:** remove `@cache` on unhashable normalizers; OverflowError in coercion; deprecation aliases."
    )
    lines.append("")
    lines.append("## Артефакты")
    lines.append("")
    lines.append(f"- Agent NDJSON: `{src.as_posix()}`")
    lines.append(
        "- Layered summary MD: `reports/quality/coderabbit/architecture-layered_20260723_101412.md`"
    )
    lines.append(
        "- Helper scripts: `scripts/ops/_run_cr_arch_review_wsl.sh`, `scripts/ops/_run_cr_arch_review_remaining.sh`"
    )
    lines.append("")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE {out} findings={len(findings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
