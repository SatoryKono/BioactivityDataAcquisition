"""One-shot unit+architecture runner writing results to reports/quality."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

OUT = Path("reports/quality/local-unit-arch-final.txt")
JUNIT = Path("reports/quality/local-unit-arch.xml")
OUT.parent.mkdir(parents=True, exist_ok=True)

cmd = [
    sys.executable,
    "-m",
    "pytest",
    "tests/unit",
    "tests/architecture",
    "-q",
    "--tb=line",
    "--maxfail=8",
    "--timeout=180",
    "-p",
    "no:cacheprovider",
    "--color=no",
    f"--junitxml={JUNIT.as_posix()}",
]

with OUT.open("w", encoding="utf-8") as handle:
    handle.write("CMD: " + " ".join(cmd) + "\n")
    handle.flush()
    proc = subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT)
    handle.write(f"\nEXIT:{proc.returncode}\n")

raise SystemExit(proc.returncode)
