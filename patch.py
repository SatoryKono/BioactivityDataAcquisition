import json

with open("configs/quality/scripts_lifecycle_registry.json", "r") as f:
    data = json.load(f)

if "scripts/ops/start-codex.bat" not in data["entries"]:
    data["entries"]["scripts/ops/start-codex.bat"] = {
        "owner": "@bioetl-platform",
        "decision": "legacy_manual_utility",
        "review_by": "2026-07-15",
        "next_step": "Retain as a legacy utility"
    }

if "scripts/qa/py_review_orchestrator.py" not in data["entries"]:
    data["entries"]["scripts/qa/py_review_orchestrator.py"] = {
        "owner": "@bioetl-platform",
        "decision": "active",
        "review_by": "2026-07-15",
        "next_step": "Active script for py-review-orchestrator static analysis"
    }

with open("configs/quality/scripts_lifecycle_registry.json", "w") as f:
    json.dump(data, f, indent=2)
