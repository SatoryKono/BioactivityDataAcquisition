import csv
from typing import List, Dict, Any
from .github_billing_schema import GitHubBillingRecord

def validate_billing_report(file_path: str) -> List[GitHubBillingRecord]:
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle empty optional fields explicitly
            if not row.get("repository"):
                row["repository"] = None
            if not row.get("workflow_path"):
                row["workflow_path"] = None

            record = GitHubBillingRecord(**row)
            records.append(record)
    return records
