"""Exact-run accounting projection without inferred zeroes or denominators."""

from __future__ import annotations


def summary_accounting(payload: dict[str, object]) -> dict[str, object]:
    """Expose persisted layer counts and the denominator of contract exclusions."""
    layers = payload.get("layers")
    if not isinstance(layers, dict):
        layers = {}
    values = {
        key: value if type(value := layers.get(key)) is int and value >= 0 else None
        for key in (
            "bronze_records",
            "silver_valid",
            "silver_quarantined",
            "gold_quarantined",
            "gold_excluded_by_contract",
            "gold_written",
        )
    }
    excluded, accepted = values["gold_excluded_by_contract"], values["silver_valid"]
    return {
        **values,
        "contract_excluded_percent": 100 * excluded / accepted
        if excluded is not None and accepted is not None and accepted > 0
        else None,
        "contract_excluded_basis": "Gold exclusions / Silver accepted",
    }
