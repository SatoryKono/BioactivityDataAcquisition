from typing import List, Dict, Tuple
from .github_billing_schema import GitHubBillingRecord

def calculate_totals(records: List[GitHubBillingRecord]) -> Dict[str, float]:
    """Calculate the total net amount for different billing categories."""
    totals = {
        "actions_compute": 0.0,
        "shared_storage": 0.0,
        "copilot": 0.0,
        "lfs": 0.0,
        "other": 0.0
    }

    for record in records:
        product_lower = record.product.lower()
        if "actions" in product_lower and "compute" in record.sku.lower():
             totals["actions_compute"] += record.net_amount
        elif "shared storage" in product_lower:
             totals["shared_storage"] += record.net_amount
        elif "copilot" in product_lower:
             totals["copilot"] += record.net_amount
        elif "lfs" in product_lower:
             totals["lfs"] += record.net_amount
        else:
             totals["other"] += record.net_amount

    return totals

def extract_workflow_attribution(records: List[GitHubBillingRecord]) -> Dict[str, float]:
    """Attribute Actions compute net amount to specific workflows."""
    attribution = {}
    for record in records:
         if "actions" in record.product.lower() and "compute" in record.sku.lower():
             if record.workflow_path:
                 attribution[record.workflow_path] = attribution.get(record.workflow_path, 0.0) + record.net_amount
             else:
                 attribution["unattributed"] = attribution.get("unattributed", 0.0) + record.net_amount

    return attribution
