import json
from pathlib import Path

d = json.loads(
    Path("reports/quality/module-coverage-inventory.json").read_text(encoding="utf-8")
)
print("uncovered", d["summary"]["uncovered_module_count"])
print("unmeasured", d["summary"]["unmeasured_module_count"])
unc = [
    m
    for m in d["modules"]
    if m.get("coverage_status") == "uncovered"
    or (
        float(m.get("coverage_percent") or 0) == 0.0
        and int(m.get("executable_lines") or 0) > 0
    )
]
print("len", len(unc))
for m in unc:
    print(
        f"{m['coverage_percent']:5} {m['covered_lines']}/{m['executable_lines']} "
        f"{m['path']} status={m.get('coverage_status')}"
    )
