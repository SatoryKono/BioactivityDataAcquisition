#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

src = Path(__file__).with_name("_cr_wave_runner.py").read_text(encoding="utf-8")
m = re.search(r"BASH_SCRIPT = r'''(.*)'''\n\n\ndef main", src, re.S)
if not m:
    raise SystemExit("BASH_SCRIPT block not found")
body = m.group(1)
# Prefer Linux path when available
outs = [
    Path("/mnt/c/Users/Fedor/_cr_wave_runner.sh"),
    Path.home() / "_cr_wave_runner.sh",
    Path(__file__).with_name("_cr_wave_runner.sh"),
]
written = None
for out in outs:
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8", newline="\n")
        written = out
        break
    except OSError as exc:
        print(f"skip {out}: {exc}")
if written is None:
    raise SystemExit("failed to write runner")
print(f"wrote {written} size={written.stat().st_size} dollars={body.count('$')}")
print("sample:", body.splitlines()[10])
print("sample:", body.splitlines()[19])
