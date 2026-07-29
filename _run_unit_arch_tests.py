
from __future__ import annotations
import os, subprocess, sys
from pathlib import Path
os.environ["PYTHONUNBUFFERED"] = "1"
OUT = Path("reports/quality/local-unit-arch-final.txt")
JUNIT = Path("reports/quality/local-unit-arch.xml")
OUT.parent.mkdir(parents=True, exist_ok=True)
cmd = [sys.executable, "-u", "-m", "pytest", "tests/unit", "tests/architecture", "-q", "--tb=line", "--maxfail=8", "--timeout=180", "-p", "no:cacheprovider", "--color=no", f"--junitxml={JUNIT.as_posix()}"]
with OUT.open("w", encoding="utf-8", buffering=1) as handle:
    handle.write("CMD: " + " ".join(cmd) + chr(10))
    handle.flush()
    proc = subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT, env={**os.environ, "PYTHONUNBUFFERED": "1"})
    handle.write(f"EXIT:{proc.returncode}" + chr(10))
    handle.flush()
raise SystemExit(proc.returncode)
