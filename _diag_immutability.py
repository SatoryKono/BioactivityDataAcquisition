"""Temporary diagnostic script for _immutability import."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_diag_immutability_result.txt"
SRC = ROOT / "src" / "bioetl" / "domain" / "_immutability.py"


def _run(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return f"$ {' '.join(cmd)}\nexit={proc.returncode}\nstdout={proc.stdout!r}\nstderr={proc.stderr!r}\n"
    except Exception as exc:  # noqa: BLE001
        return f"$ {' '.join(cmd)}\nERROR={exc!r}\n"


lines: list[str] = []
lines.append(f"python={sys.executable}")
lines.append(f"file_exists={SRC.is_file()} file={SRC}")
lines.append(_run(["git", "status", "--short", "--", "src/bioetl/domain/_immutability.py"]))
lines.append(_run(["git", "ls-files", "--", "src/bioetl/domain/_immutability.py"]))

sys.path.insert(0, str(ROOT / "src"))
try:
    import bioetl.domain._immutability as m

    public = [x for x in dir(m) if not x.startswith("_")]
    lines.append(f"IMPORT_OK file={m.__file__} public={public}")
except Exception as exc:
    lines.append(f"IMPORT_FAIL type={type(exc).__name__} msg={exc!r}")

try:
    import bioetl

    lines.append(f"bioetl.__file__={getattr(bioetl, '__file__', None)}")
    lines.append(f"bioetl.__path__={getattr(bioetl, '__path__', None)}")
except Exception as exc:
    lines.append(f"bioetl_import_fail={exc!r}")

spec = importlib.util.find_spec("bioetl")
lines.append(f"find_spec(bioetl)={spec}")
spec_imm = importlib.util.find_spec("bioetl.domain._immutability")
lines.append(f"find_spec(bioetl.domain._immutability)={spec_imm}")

for sp in sys.path:
    candidate = Path(sp) / "bioetl" / "domain" / "_immutability.py"
    if candidate.is_file():
        lines.append(f"site_packages_hit={candidate}")

lines.append(_run([sys.executable, "-m", "pytest", "tests/unit/config/test_non_chembl_composite_boundary_policy.py", "--collect-only", "-q"]))

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"WROTE {OUT}")
