from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

cmd = [
    sys.executable,
    "-m",
    "basedpyright",
    "src",
    "scripts",
    "tests",
    "--outputjson",
]
proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
# basedpyright may write json to stdout even with non-zero exit
raw = proc.stdout or ""
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    print("FAILED to parse json")
    print(raw[:2000])
    print(proc.stderr[:2000])
    sys.exit(1)

diags = data.get("generalDiagnostics") or []
errs = [d for d in diags if "error" in str(d.get("severity", "")).lower()]
warns = [d for d in diags if "warning" in str(d.get("severity", "")).lower()]
print(f"errors={len(errs)} warnings={len(warns)} total={len(diags)} exit={proc.returncode}")

by_file: Counter[str] = Counter()
by_msg: Counter[str] = Counter()
for e in errs:
    f = str(e.get("file", "")).replace("\\", "/")
    if "BioactivityDataAcquisition/" in f:
        f = f.split("BioactivityDataAcquisition/", 1)[1]
    by_file[f] += 1
    by_msg[str(e.get("message", ""))[:100]] += 1

print("\nTop files:")
for f, n in by_file.most_common(40):
    print(f"{n:3d}  {f}")
print("\nTop messages:")
for m, n in by_msg.most_common(30):
    print(f"{n:3d}  {m}")

out = Path("reports/quality/coderabbit/20260806-full/_live_errors.json")
out.write_text(json.dumps(errs, indent=2), encoding="utf-8")
print("wrote", out, "n=", len(errs))
