from __future__ import annotations

from collections import Counter
from pathlib import Path

text = Path(
    r"C:/Users/Fedor/AppData/Local/Temp/grok-test-sessions-70364/pasted/abfcfd24-diagnostics"
).read_text(encoding="utf-8", errors="replace")

prefix = "BioactivityDataAcquisition\\"
files: list[str] = []
for line in text.splitlines():
    if line.startswith(prefix) and line.endswith(".py"):
        files.append(line[len(prefix) :].replace("\\", "/"))

print("files unique", len(set(files)))
for f, n in Counter(files).most_common(50):
    print(f"{n:3d}  {f}")

errs: list[str] = []
for line in text.splitlines():
    if line.startswith("// error:"):
        errs.append(line[len("// error: ") :])
print("\nerrors", len(errs))
for m, n in Counter(e[:120] for e in errs).most_common(40):
    print(f"{n:3d}  {m}")

cats: Counter[str] = Counter()
others: list[str] = []
for e in errs:
    el = e.lower()
    if "parameter name mismatch" in el:
        cats["param_name_mismatch"] += 1
    elif "not initialized in the class body or __init__" in el:
        cats["uninit_instance_var"] += 1
    elif "partially unknown" in el:
        cats["partially_unknown"] += 1
    elif "is unknown" in el:
        cats["unknown"] += 1
    elif "is not assignable" in el or "cannot be assigned" in el:
        cats["assignability"] += 1
    elif "has no attribute" in el:
        cats["no_attribute"] += 1
    elif "override" in el:
        cats["override"] += 1
    elif "return type" in el:
        cats["return_type"] += 1
    else:
        cats["other"] += 1
        others.append(e[:160])
print("\nCategories", dict(cats))
print("\nOTHER samples:")
for o in others[:20]:
    print(" -", o)

# dump unique files list
Path("reports/quality/coderabbit/20260806-full/_diag_files.txt").write_text(
    "\n".join(sorted(set(files))), encoding="utf-8"
)
