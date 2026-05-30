import json
from pathlib import Path

ROOT = Path(".")
data = json.loads((ROOT / "reports/quality/module-coverage-inventory.json").read_text())
rows = [r for r in data["modules"] if "composition/runtime_builders" in r["path"]]
total_cov = sum(r["covered_lines"] for r in rows)
total_exec = sum(r["executable_lines"] for r in rows)
target = int(total_exec * 0.80 + 0.999)
need = target - total_cov
print(f"covered={total_cov} exec={total_exec} current={100*total_cov/total_exec:.2f}%")
print(f"need {need} more lines for 80% (target covered={target})")
