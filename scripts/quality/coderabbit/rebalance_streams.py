"""Rebalance open major residual issues into 5 independent streams."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

OUT = Path("reports/quality/coderabbit/_live")


def stream_of(path: str) -> str:
    p = path.replace("\\", "/")
    name = p.rsplit("/", 1)[-1]

    if p.startswith("src/bioetl/domain"):
        return "S5 domain"

    if "observability" in p:
        if any(
            k in p
            for k in (
                "logging",
                "unified_logger",
                "tracing",
                "debug_adapters",
                "circuit_breaker",
            )
        ):
            return "S4 obs-logging-tracing"
        return "S3 obs-metrics"

    # application/core
    lifecycle = {
        "runner.py",
        "config.py",
        "pipeline_services.py",
        "entity_id.py",
        "pre_silver_finalization_flow.py",
        "subcellular_fraction_support.py",
        "runner_flow_metrics.py",
    }
    if (
        any(x in p for x in ("/lifecycle", "/preflight", "/postrun", "/wiring"))
        or name in lifecycle
    ):
        return "S1 app-lifecycle-runner"

    # record / quarantine / fetch / transformer / publication / data_sources
    return "S2 app-record-transform"


def main() -> None:
    data = json.loads((OUT / "open_cm_streams.json").read_text(encoding="utf-8"))
    maj = data["major"]
    crit = data.get("critical") or []

    streams: dict[str, list[dict[str, object]]] = defaultdict(list)
    for m in maj:
        streams[stream_of(m["path"])].append(m)

    order = [
        "S1 app-lifecycle-runner",
        "S2 app-record-transform",
        "S3 obs-metrics",
        "S4 obs-logging-tracing",
        "S5 domain",
    ]
    total = sum(len(streams[s]) for s in order)
    assert total == len(maj), f"stream sum {total} != major {len(maj)}"

    roots = {
        "S1 app-lifecycle-runner": (
            "`application/core` runner/lifecycle/preflight/postrun/wiring/config/…"
        ),
        "S2 app-record-transform": (
            "`application/core` record/quarantine/fetch/transformer/publication/…"
        ),
        "S3 obs-metrics": (
            "`infrastructure/observability` metrics/prometheus/server/anomaly/…"
        ),
        "S4 obs-logging-tracing": (
            "`infrastructure/observability` logging/tracing/debug/circuit_breaker"
        ),
        "S5 domain": "`domain/ports/*`",
    }

    lines: list[str] = []
    lines.append("# Open CodeRabbit residual — CRITICAL + MAJOR (refreshed)")
    lines.append("")
    lines.append(
        "Live `gh` search, repo `SatoryKono/BioactivityDataAcquisition`."
    )
    lines.append("")
    lines.append("| Severity | Open |")
    lines.append("|----------|-----:|")
    lines.append(f"| **critical** | **{len(crit)}** |")
    lines.append(f"| **major** | **{len(maj)}** |")
    lines.append(f"| **TOTAL C+M** | **{len(crit) + len(maj)}** |")
    lines.append("")
    lines.append("## CRITICAL")
    lines.append("")
    if not crit:
        lines.append(
            "_Нет открытых critical residual path-cluster issues_ "
            "(ранее #7992/#7996 и storage FK cluster закрыты)."
        )
    else:
        for c in crit:
            lines.append(f"- **#{c['number']}** — `{c['path']}`")
    lines.append("")
    lines.append("## MAJOR (полный список по path)")
    lines.append("")
    for m in sorted(maj, key=lambda x: x["path"]):
        lines.append(f"- **#{m['number']}** — `{m['path']}`")
    lines.append("")
    lines.append("## 5 независимых потоков (exclusive path ownership)")
    lines.append("")
    lines.append(
        "Перебалансировка после закрытий: critical / application-batch / "
        "infrastructure-storage = 0 open → 5 потоков на оставшиеся major."
    )
    lines.append("")
    lines.append("```")
    lines.append("S1 app-lifecycle-runner ──┐")
    lines.append("S2 app-record-transform ──┼── parallel worktrees")
    lines.append("S3 obs-metrics          ──┤")
    lines.append("S4 obs-logging-tracing  ──┤")
    lines.append("S5 domain               ──┘")
    lines.append("```")
    lines.append("")
    lines.append("| Stream | Exclusive paths | Issues | IDs |")
    lines.append("|--------|-----------------|-------:|-----|")
    for s in order:
        items = sorted(streams[s], key=lambda x: x["number"])
        ids = ", ".join(f"#{m['number']}" for m in items[:8])
        if len(items) > 8:
            ids += f", … +{len(items) - 8}"
        lines.append(f"| **{s}** | {roots[s]} | {len(items)} | {ids} |")
    lines.append("")

    for s in order:
        items = sorted(streams[s], key=lambda x: x["number"])
        lines.append(f"### {s} ({len(items)})")
        lines.append("")
        for m in items:
            lines.append(f"- **#{m['number']}** `{m['path']}`")
        lines.append("")

    lines.append("## Правила параллелизма")
    lines.append("")
    lines.append(
        "1. Один worktree/agent на stream; **path ownership не пересекается**."
    )
    lines.append(
        "2. S1 и S2 оба под `application/core/` — **разные файлы**; "
        "не править «чужие»."
    )
    lines.append(
        "3. S3 и S4 оба под `observability/` — **разные файлы**."
    )
    lines.append(
        "4. S5 domain — 2 issue; можно закрыть быстро или прицепить к S4 "
        "(paths всё равно exclusive)."
    )
    lines.append("5. Не увеличивать бюджеты техдолга.")
    lines.append(
        "6. После PR: close issue + evidence; пересчёт inventory."
    )
    lines.append("")

    text = "\n".join(lines)
    (OUT / "OPEN_CRITICAL_MAJOR_STREAMS.md").write_text(text, encoding="utf-8")

    payload = {
        "critical": crit,
        "major": maj,
        "streams": {
            s: [
                {
                    "number": m["number"],
                    "severity": "major",
                    "path": m["path"],
                }
                for m in sorted(streams[s], key=lambda x: x["number"])
            ]
            for s in order
        },
    }
    (OUT / "open_cm_streams.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"CRITICAL={len(crit)} MAJOR={len(maj)}")
    for s in order:
        print(f"  {s}: {len(streams[s])}")
    print(f"wrote {OUT / 'OPEN_CRITICAL_MAJOR_STREAMS.md'}")


if __name__ == "__main__":
    main()
