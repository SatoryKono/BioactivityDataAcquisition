from datetime import date
from pydantic import BaseModel, Field
from typing import Optional

class GitHubBillingRecord(BaseModel):
    date: date
    product: str
    sku: str
    repository: Optional[str] = None
    workflow_path: Optional[str] = None
    quantity: float
    unit_type: str
    gross_amount: float
    discount_amount: float
    net_amount: float
    currency: str = "USD"
