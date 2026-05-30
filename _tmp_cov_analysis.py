import json
from pathlib import Path

ROOT = Path(".")
data = json.loads((ROOT / "reports/quality/module-coverage-inventory.json").read_text())
rows = [r for r in data["modules"] if "composition/runtime_builders" in r["path"]]
rows.sort(key=lambda r: (r.get("coverage_percent") is None, r.get("coverage_percent") or 0))
for r in rows:
    pct = r["coverage_percent"]
    pct_s = f"{pct:6.1f}" if pct is not None else "  None"
    print(
        f"{pct_s} {r['coverage_status']:20} "
        f"{r['covered_lines']:>4}/{r['executable_lines']:<4} {r['path']}"
    )
total_cov = sum(r["covered_lines"] for r in rows)
total_exec = sum(r["executable_lines"] for r in rows)
print("---")
print(f"line percent: {100 * total_cov / total_exec:.2f}")
