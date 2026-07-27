#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    report = Path(sys.argv[1] if len(sys.argv) > 1 else "reports/bp60.json")
    data = json.loads(report.read_text(encoding="utf-8"))
    diags = data.get("generalDiagnostics") or []
    print("total", len(diags), "summary", data.get("summary"))
    by: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for d in diags:
        f = d["file"].replace("\\", "/").split("/src/")[-1]
        line = d["range"]["start"]["line"] + 1
        by[f].append((line, str(d.get("rule")), str(d.get("message", ""))[:240]))
    lines: list[str] = []
    for f in sorted(by):
        for line, rule, msg in sorted(by[f]):
            lines.append(f"{f}:{line}: {rule}: {msg}")
    out = Path("reports/bp60_list.txt")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
