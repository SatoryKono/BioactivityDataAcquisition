#!/usr/bin/env python3
"""Temporary governance drift check."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

from scripts.engineering.qa.hotspot_family_metrics import (
    count_internal_fan_in,
    iter_family_python_files,
    load_scorecard,
)
from scripts.engineering.qa.import_graph_inventory import collect_zero_import_bioetl_modules
from scripts.engineering.qa.report_dead_code_inventory import build_dead_code_inventory
from scripts.engineering.qa.report_test_governance_audit import (
    COMPATIBILITY_FILE_RE,
    _iter_test_files,
    collect_test_governance_report,
)

print("=== hotspot fan-in ===")
scorecard = load_scorecard()
for family in scorecard.get("hotspot_family_ratchets", {}).get("families", []):
    if family.get("name") != "composition_runtime_builders":
        continue
    files = iter_family_python_files(path_prefixes=family["path_prefixes"])
    fan_in, module = count_internal_fan_in(files=files)
    budget = family["bounded_growth_budgets"]["max_internal_fan_in"]
    print(f"family={family['name']} fan_in={fan_in} module={module} budget={budget}")

print("\n=== zero-import candidates ===")
for row in collect_zero_import_bioetl_modules(ROOT):
    print(row["path"])

print("\n=== dead code inventory summary ===")
inv = build_dead_code_inventory(ROOT)
print(inv["summary"])

print("\n=== compatibility test files ===")
report = collect_test_governance_report(ROOT)
print("count:", report["compatibility_test_files"])
for path in report.get("compatibility_files", []):
    print(" ", path)

print("\n=== manual compat scan ===")
for path in _iter_test_files(ROOT):
    rel = path.relative_to(ROOT).as_posix()
    if COMPATIBILITY_FILE_RE.search(rel):
        print(" ", rel)
