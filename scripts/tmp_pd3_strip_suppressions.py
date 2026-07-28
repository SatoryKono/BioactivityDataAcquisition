#!/usr/bin/env python3
"""Try stripping # pyright suppressions file-by-file; keep only if basedpyright clean."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "bioetl"
BP = ROOT / ".venv-win" / "Scripts" / "basedpyright.exe"
INV = ROOT / "reports" / "quality" / "basedpyright-suppression-inventory.json"

DIRECTIVE_LINE = re.compile(r"^\s*#\s*pyright:\s*")
# Also strip our PD2/PD3 rationale comments that only document suppressions
RATIONALE = re.compile(
    r"^\s*#\s*("
    r"Host attrs/methods|"
    r"Host/cast bridge|"
    r"Import cycle residual|"
    r"MRO/override residual|"
    r"Boundary object/payload|"
    r"basedpyright residual burn-down|"
    r"Host attrs/methods provided by concrete|"
    r"Optional dependency probe|"
    r"Pandera/ETL nested Config|"
    r"RuntimeState properties own|"
    r"OpenAlex payload fields|"
    r"DQ request payload|"
    r"Click callback|"
    r"Entity fixture overrides"
    r").*$"
)


def strip_directives(text: str) -> str:
    lines = text.splitlines(True)
    out: list[str] = []
    for line in lines:
        if DIRECTIVE_LINE.match(line):
            continue
        if RATIONALE.match(line):
            continue
        out.append(line)
    # collapse leading blank lines after strip
    while out and out[0].strip() == "":
        out.pop(0)
    return "".join(out)


def bp_errors(path: Path) -> int:
    cmd = [str(BP), str(path)]
    try:
        completed = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 999
    # basedpyright ends with "N errors, M warnings"
    text = (completed.stdout or "") + "\n" + (completed.stderr or "")
    for line in reversed(text.splitlines()):
        line = line.strip()
        if "error" in line and "warning" in line:
            # e.g. 0 errors, 12 warnings, 0 notes
            m = re.search(r"(\d+)\s+errors?", line)
            if m:
                return int(m.group(1))
    if completed.returncode not in (0, 1):
        return 999
    return 0 if completed.returncode == 0 else 999


def main() -> None:
    inv = json.loads(INV.read_text(encoding="utf-8"))
    paths = [f["path"] for f in inv.get("files", [])]
    removed: list[str] = []
    kept: list[str] = []
    failed: list[str] = []

    for i, rel in enumerate(paths, 1):
        path = SRC / rel
        if not path.is_file():
            continue
        original = path.read_text(encoding="utf-8")
        if "# pyright:" not in original:
            continue
        stripped = strip_directives(original)
        if stripped == original:
            continue
        path.write_text(stripped, encoding="utf-8")
        err_count = bp_errors(path)
        if err_count == 0:
            removed.append(rel)
            print(f"[{i}/{len(paths)}] REMOVED {rel}")
        else:
            path.write_text(original, encoding="utf-8")
            kept.append(rel)
            if err_count >= 999:
                failed.append(rel)
                print(f"[{i}/{len(paths)}] KEEP(fail) {rel} errors={err_count}")
            else:
                print(f"[{i}/{len(paths)}] KEEP {rel} errors={err_count}")
        sys.stdout.flush()

    report = {
        "removed_count": len(removed),
        "kept_count": len(kept),
        "failed_count": len(failed),
        "removed": removed,
        "kept": kept[:50],
        "failed": failed,
    }
    out = ROOT / "reports" / "quality" / "pd3-suppression-strip-trial.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"DONE removed={len(removed)} kept={len(kept)} failed={len(failed)} report={out}"
    )


if __name__ == "__main__":
    main()
