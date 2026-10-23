"""Typed row for one normalized GitHub billing CSV record."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

MONEY_FIELDS = ("gross_amount", "discount_amount", "net_amount")


class GitHubBillingRecord(BaseModel):
    """One billing row. Money stays decimal and currency is never implied."""

    model_config = ConfigDict(hide_input_in_errors=True)

    date: date
    product: str
    sku: str
    repository: str | None = None
    workflow_path: str | None = None
    quantity: float
    unit_type: str
    gross_amount: Decimal
    discount_amount: Decimal
    net_amount: Decimal
    currency: str

    @field_validator(*MONEY_FIELDS, mode="before")
    @classmethod
    def money_must_be_exact(cls, value: object) -> Decimal:
        """Reject binary floats so cent totals cannot drift."""
        if isinstance(value, float):
            raise ValueError(
                "money fields reject float; use Decimal or a decimal string"
            )
        if isinstance(value, Decimal):
            return value
        if isinstance(value, int) and not isinstance(value, bool):
            return Decimal(value)
        if isinstance(value, str):
            return Decimal(value.strip())
        raise ValueError("unsupported money value")

    @field_validator("currency")
    @classmethod
    def currency_must_be_explicit(cls, value: str) -> str:
        """Keep a blank currency column from becoming an implicit USD row."""
        text = value.strip()
        if not text:
            raise ValueError("currency is required")
        return text

    @model_validator(mode="after")
    def net_equals_gross_minus_discount(self) -> GitHubBillingRecord:
        """Enforce the usage-report identity before any total is computed."""
        expected = self.gross_amount - self.discount_amount
        if self.net_amount != expected:
            raise ValueError("gross_amount - discount_amount must equal net_amount")
        return self
