from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

text = Path(
    r"C:/Users/Fedor/AppData/Local/Temp/grok-test-sessions-70364/pasted/e7611a30-diagnostics"
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

out = Path("reports/quality/coderabbit/20260806-full/_diag277_by_file.txt")
lines: list[str] = [f"TOTAL_FILES={len(blocks)} TOTAL_ERRORS={sum(len(v) for v in blocks.values())}", ""]
for f, errs in sorted(blocks.items(), key=lambda x: -len(x[1])):
    uniq = list(dict.fromkeys(errs))
    lines.append(f"=== {f} ({len(errs)} total, {len(uniq)} unique) ===")
    for e in uniq:
        lines.append(f"  - {e}")
    lines.append("")
out.write_text("\n".join(lines), encoding="utf-8")
print(out)
print("files", len(blocks), "errors", sum(len(v) for v in blocks.values()))
for f, errs in sorted(blocks.items(), key=lambda x: -len(x[1])):
    print(f"{len(errs):3d}  {f}")

# top messages
all_errs = [e for errs in blocks.values() for e in errs]
print("\nTop messages:")
for m, n in Counter(e[:100] for e in all_errs).most_common(25):
    print(f"{n:3d}  {m}")
