#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "bioetl"
spec = importlib.util.spec_from_file_location("h", ROOT / "scripts" / "tmp_pd3_host_defaults.py")
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

changed = 0
for path in SRC.rglob("*.py"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "reportUninitializedInstanceVariable=false" not in text:
        continue
    rel = str(path.relative_to(SRC)).replace("\\", "/")
    original = text
    updated = mod.inject_defaults(text)
    updated = mod.strip_uninit_directive(updated)
    if updated == original:
        continue
    path.write_text(updated, encoding="utf-8")
    err = mod.bp_errors(path)
    if err == 0:
        print("OK", rel)
        changed += 1
    else:
        path.write_text(original, encoding="utf-8")
        print("REVERT", rel, err)
print("changed", changed)
