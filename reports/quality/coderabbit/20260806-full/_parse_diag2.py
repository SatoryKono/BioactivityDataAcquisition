from __future__ import annotations

from collections import defaultdict
from pathlib import Path

text = Path(
    r"C:/Users/Fedor/AppData/Local/Temp/grok-test-sessions-70364/pasted/abfcfd24-diagnostics"
).read_text(encoding="utf-8", errors="replace")

current: str | None = None
blocks: dict[str, list[str]] = defaultdict(list)
for line in text.splitlines():
    if "BioactivityDataAcquisition" in line and line.endswith(".py"):
        part = line.split("BioactivityDataAcquisition", 1)[1]
        current = part.lstrip("\\/").replace("\\", "/")
        continue
    if line.startswith("// error:") and current:
        blocks[current].append(line[len("// error: ") :])

out = Path("reports/quality/coderabbit/20260806-full/_diag_by_file.txt")
lines: list[str] = []
for f, errs in sorted(blocks.items()):
    uniq = list(dict.fromkeys(errs))
    lines.append(f"=== {f} ({len(errs)} total, {len(uniq)} unique) ===")
    for e in uniq:
        lines.append(f"  - {e}")
    lines.append("")
out.write_text("\n".join(lines), encoding="utf-8")
print(out)
print("files", len(blocks))
for f, errs in sorted(blocks.items(), key=lambda x: -len(x[1])):
    print(len(errs), f)
