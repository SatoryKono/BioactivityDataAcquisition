"""Live inventory: open CR residual critical/major + 5 streams."""

# NOSONAR - S1192: stream literals are intentional for categorization logic
STREAM_S5_PUBLICATION = "S5 publication"
STREAM_S4_TRANSFORMER = "S4 transformer"
STREAM_S3_RECORD_QUARANTINE_FETCH = "S3 record-quarantine-fetch"
STREAM_S2_CONFIG_SERVICES = "S2 config-services"
STREAM_S1_LIFECYCLE_RUNNER = "S1 lifecycle-runner"

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

OUT = Path("reports/quality/coderabbit/_live")


def strip_ansi(raw: bytes) -> str:
    return (
        re.sub(rb"\x1b\[[0-9;]*m", b"", raw).decode("utf-8", errors="replace").strip()
    )


def load_search(path: Path) -> list[dict[str, object]]:
    text = strip_ansi(path.read_bytes())
    dec = json.JSONDecoder()
    idx = 0
    items: list[dict[str, object]] = []
    while idx < len(text):
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text):
            break
        obj, end = dec.raw_decode(text, idx)
        idx = end
        if isinstance(obj, dict):
            raw_items = obj.get("items")
            if isinstance(raw_items, list):
                for item in raw_items:
                    if isinstance(item, dict):
                        items.append(item)
    return items


def path_of(title: str) -> str:
    m = re.search(r"`([^`]+)`", title or "")
    if m and not m.group(1).endswith("..."):
        return m.group(1)
    return ""


def stream_of(path: str) -> str:
    p = path.replace("\\", "/")
    name = p.rsplit("/", 1)[-1]
    if "publication_term" in p:
        return STREAM_S5_PUBLICATION
    if "base_transformer" in p or "_base_transformer" in p:
        return STREAM_S4_TRANSFORMER
    if any(
        k in p
        for k in (
            "quarantine",
            "fetch",
            "filtered_data",
            "record_",
            "record_processor",
            "normalization",
            "data_sources",
        )
    ) or name in {"record_processor.py", "normalization_fallbacks.py"}:
        return STREAM_S3_RECORD_QUARANTINE_FETCH
    if name in {
        "config.py",
        "pipeline_services.py",
        "entity_id.py",
        "subcellular_fraction_support.py",
    }:
        return STREAM_S2_CONFIG_SERVICES
    return STREAM_S1_LIFECYCLE_RUNNER


def _issue_number(item: dict[str, object]) -> int | None:
    raw = item.get("number")
    return raw if isinstance(raw, int) else None


def main() -> None:
    maj_raw = load_search(OUT / "search_major_residual.json")
    crit_raw = load_search(OUT / "search_critical_residual.json")

    path_clusters: list[dict[str, object]] = []
    meta: list[dict[str, object]] = []
    for it in maj_raw:
        title = str(it.get("title", "") or "")
        p = path_of(title)
        if "[major]" in title.lower() and p.startswith("src/"):
            path_clusters.append(
                {"number": it.get("number"), "path": p, "title": title}
            )
        else:
            meta.append({"number": it.get("number"), "title": title})

    crit_pc: list[dict[str, object]] = []
    crit_meta: list[dict[str, object]] = []
    for it in crit_raw:
        title = str(it.get("title", "") or "")
        p = path_of(title)
        if "[critical]" in title.lower() and p.startswith("src/"):
            crit_pc.append({"number": it.get("number"), "path": p, "title": title})
        else:
            crit_meta.append({"number": it.get("number"), "title": title})

    streams: dict[str, list[dict[str, object]]] = defaultdict(list)
    for m in path_clusters:
        streams[stream_of(str(m.get("path") or ""))].append(m)

    order = [
        "S1 lifecycle-runner",
        "S2 config-services",
        "S3 record-quarantine-fetch",
        "S4 transformer",
        "S5 publication",
    ]
    assert sum(len(streams[s]) for s in order) == len(path_clusters)

    roots = {
        "S1 lifecycle-runner": (
            "postrun, wiring, lifecycle, preflight, runner, "
            "pre_silver, runner_flow_metrics"
        ),
        "S2 config-services": (
            "config.py, pipeline_services.py, entity_id.py, "
            "subcellular_fraction_support.py"
        ),
        "S3 record-quarantine-fetch": (
            "record_*, quarantine_*, fetch_*, filtered_*, data_sources, normalization_*"
        ),
        "S4 transformer": "base_transformer*",
        "S5 publication": "publication_term_*",
    }

    # meta unique
    seen: set[int] = set()
    meta_all: list[dict[str, object]] = []
    cluster_nums = {
        n for n in (_issue_number(x) for x in path_clusters) if n is not None
    }
    for m in meta + crit_meta:
        n = _issue_number(m)
        if n is None or n in seen or n in cluster_nums:
            continue
        seen.add(n)
        meta_all.append(m)

    lines: list[str] = []
    lines.append("# Open CodeRabbit residual — CRITICAL + MAJOR")
    lines.append("")
    lines.append("Live `gh` snapshot, repo `SatoryKono/BioactivityDataAcquisition`.")
    lines.append("")
    lines.append("| Class | Open |")
    lines.append("|-------|-----:|")
    lines.append(f"| **critical path-cluster** | **{len(crit_pc)}** |")
    lines.append(f"| **major path-cluster** | **{len(path_clusters)}** |")
    lines.append(
        f"| **TOTAL C+M path-clusters** | **{len(crit_pc) + len(path_clusters)}** |"
    )
    lines.append("")
    lines.append("## CRITICAL path-clusters")
    lines.append("")
    if not crit_pc:
        lines.append("_Нет открытых critical residual path-cluster issues._")
    else:
        for c in sorted(crit_pc, key=lambda x: _issue_number(x) or 0):
            lines.append(f"- **#{c.get('number')}** `{c.get('path')}`")
    lines.append("")
    lines.append("## MAJOR path-clusters (полный список)")
    lines.append("")
    for m in sorted(path_clusters, key=lambda x: str(x.get("path") or "")):
        lines.append(f"- **#{m.get('number')}** — `{m.get('path')}`")
    lines.append("")
    lines.append("## Campaign / meta open (не path-cluster implement)")
    lines.append("")
    for m in sorted(meta_all, key=lambda x: _issue_number(x) or 0):
        lines.append(f"- **#{m.get('number')}** — {m.get('title')}")
    lines.append("")
    lines.append("## 5 независимых потоков (exclusive path ownership)")
    lines.append("")
    lines.append("Все major path-clusters сейчас под `src/bioetl/application/core/*`.")
    lines.append("Critical / domain / observability / storage path-clusters закрыты.")
    lines.append("")
    lines.append("```")
    lines.append("S1 lifecycle-runner       ──┐")
    lines.append("S2 config-services        ──┼── parallel worktrees")
    lines.append("S3 record-quarantine-fetch──┤")
    lines.append("S4 transformer            ──┤")
    lines.append("S5 publication            ──┘")
    lines.append("```")
    lines.append("")
    lines.append("| Stream | Exclusive paths | Issues | IDs |")
    lines.append("|--------|-----------------|-------:|-----|")
    for s in order:
        items = sorted(streams[s], key=lambda x: _issue_number(x) or 0)
        ids = ", ".join(f"#{m.get('number')}" for m in items)
        lines.append(f"| **{s}** | `{roots[s]}` | {len(items)} | {ids} |")
    lines.append("")
    for s in order:
        items = sorted(streams[s], key=lambda x: _issue_number(x) or 0)
        lines.append(f"### {s} ({len(items)})")
        lines.append("")
        for m in items:
            lines.append(f"- **#{m.get('number')}** `{m.get('path')}`")
        lines.append("")
    lines.append("## Правила параллелизма")
    lines.append("")
    lines.append("1. Один worktree/agent на stream; path ownership не пересекается.")
    lines.append("2. Все потоки под `application/core/` — разные файлы.")
    lines.append("3. Не увеличивать бюджеты техдолга.")
    lines.append(
        "4. Meta issues (#7688, #7946, #8031, #8032) — не в implement-streams."
    )
    lines.append("5. После PR: close + evidence; пересчёт inventory.")
    lines.append("")

    text = "\n".join(lines)
    (OUT / "OPEN_CRITICAL_MAJOR_STREAMS.md").write_text(text, encoding="utf-8")
    payload = {
        "critical_path_clusters": crit_pc,
        "major_path_clusters": path_clusters,
        "meta_open": meta_all,
        "streams": {
            s: [
                {
                    "number": m.get("number"),
                    "severity": "major",
                    "path": m.get("path"),
                }
                for m in sorted(streams[s], key=lambda x: _issue_number(x) or 0)
            ]
            for s in order
        },
    }
    (OUT / "open_cm_streams.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(text)
    print("COUNTS:")
    for s in order:
        print(f"  {s}: {len(streams[s])}")
    print("total", sum(len(streams[s]) for s in order))


if __name__ == "__main__":
    main()
