from __future__ import annotations

import subprocess
import sys
from pathlib import Path

nodes: list[str] = []
for line in Path("_arch_fails_list.txt").read_text(encoding="utf-8").splitlines():
    raw = line.strip()
    if not raw:
        continue
    normalized = raw.replace("\\", "/")
    marker = "tests/architecture/"
    if marker in normalized:
        normalized = normalized[normalized.index(marker) :]
    nodes.append(normalized)

print(f"rerunning {len(nodes)} nodes", flush=True)
proc = subprocess.run(
    [sys.executable, "-m", "pytest", *nodes, "-q", "--tb=line"],
    check=False,
)
raise SystemExit(proc.returncode)
