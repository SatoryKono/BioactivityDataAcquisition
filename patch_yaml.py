import yaml
from pathlib import Path

path = Path("configs/quality/dashboard_query_duplicate_allowlist.yaml")
data = yaml.safe_load(path.read_text(encoding="utf-8"))

# The failure was: Exact duplicate query group is not declared in allowlist: bioetl-overview-v2.json :: Monitor Global Alerts, bioetl-overview-v2.json :: Monitor Global Alerts (Full)
new_group = {
    "id": "overview-global-alerts-exact",
    "owner": "@bioetl-observability",
    "linked_issue": "#13058",
    "normalized_expression": "bioetl_incident_global_alerts",
    "panel_refs": [
        "bioetl-overview-v2.json :: Monitor Global Alerts",
        "bioetl-overview-v2.json :: Monitor Global Alerts (Full)"
    ],
    "disposition": "retain_shared_priority_signal",
    "rationale": "Exact duplicate to mirror identical alerts between full view and standard view"
}

data["exact_duplicates"]["allowed_groups"].append(new_group)

path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
