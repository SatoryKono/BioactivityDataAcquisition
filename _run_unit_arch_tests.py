"""One-shot unit+architecture runner writing results to reports/quality."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

os.environ["PYTHONUNBUFFERED"] = "1"

OUT = Path("reports/quality/local-unit-arch-final.txt")
JUNIT = Path("reports/quality/local-unit-arch.xml")
OUT.parent.mkdir(parents=True, exist_ok=True)

cmd = [
    sys.executable,
    "-u",
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

env = {**os.environ, "PYTHONUNBUFFERED": "1"}
with OUT.open("w", encoding="utf-8", buffering=1) as handle:
    handle.write("CMD: " + " ".join(cmd) + "\n")
    handle.flush()
    proc = subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT, env=env)
    handle.write(f"EXIT:{proc.returncode}\n")
    handle.flush()

raise SystemExit(proc.returncode)
