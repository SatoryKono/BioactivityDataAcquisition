from pathlib import Path

import yaml

path = Path("configs/quality/architecture_metric_exemptions.yaml")
data = yaml.safe_load(path.read_text())

# Add exemption for PostrunService
found = False
for entry in data.get("class_size", []):
    if (
        entry.get("module") == "bioetl.application.core.postrun_service"
        and entry.get("symbol") == "PostrunService"
    ):
        found = True
        break

if not found:
    if "class_size" not in data:
        data["class_size"] = []

    data["class_size"].append(
        {
            "module": "bioetl.application.core.postrun_service",
            "symbol": "PostrunService",
            "value": 310,
            "owner": "@bioetl-architecture",
            "review_by": "2026-06-30",
            "rationale": "Service encapsulates complex post-run validation and summarization logic requiring large sequential steps.",
        }
    )

    with path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
