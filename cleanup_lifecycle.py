#!/usr/bin/env python3
"""Remove deleted script entries from lifecycle registry."""

import json

# Scripts we deleted that need to be removed from lifecycle registry
DELETED_SCRIPTS = [
    "scripts/ai/code-reviewer.sh",
    "scripts/ai/data-engineer.sh", 
    "scripts/ai/literature-researcher.sh",
    "scripts/archive/migrations/migrate_openalex_citation_count.py",
    "scripts/archive/migrations/migrate_pmid_to_string.py",
    "scripts/archive/migrations/rename_structure_fields.py",
    "scripts/diagnostics/_tmp_inspect_vcr.py",
    "scripts/qa/generate_reports.py",
    "scripts/rerender_grafana_screenshots.py",
    "scripts/qa/hotspot_family_metrics.py",
    "src/tools/scripts/check_application_deps.py",
    "src/tools/scripts/check_architecture.py",
    "src/tools/scripts/check_constructor_args.py",
    "src/tools/scripts/config_matrix_generator.py",
    "src/tools/scripts/duplicate_function_analyzer.py",
    "src/tools/scripts/generate_contracts.py",
    "src/tools/scripts/lint_terminology.py",
    "src/tools/scripts/validate_unified_configs.py",
    "scripts/run_pytest.sh",
    "scripts/run_pytest.ps1"
]

# Load lifecycle registry
with open("configs/quality/scripts_lifecycle_registry.json", "r") as f:
    registry = json.load(f)

# Remove deleted script entries
original_count = len(registry["entries"])
removed_count = 0

for script_path in DELETED_SCRIPTS:
    if script_path in registry["entries"]:
        del registry["entries"][script_path]
        removed_count += 1
        print(f"Removed: {script_path}")

# Save updated registry
with open("configs/quality/scripts_lifecycle_registry.json", "w") as f:
    json.dump(registry, f, indent=2)

print(f"\nSummary: Removed {removed_count}/{len(DELETED_SCRIPTS)} entries from lifecycle registry")
print(f"Original entries: {original_count}, Remaining entries: {len(registry['entries'])}")