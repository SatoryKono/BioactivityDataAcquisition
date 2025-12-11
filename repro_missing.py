import math

import pandas as pd


def is_missing(value):
    if value is None:
        return True
    try:
        return bool(value != value)
    except (ValueError, TypeError):
        return False


print(f"is_missing(None): {is_missing(None)}")
print(f"is_missing(float('nan')): {is_missing(float('nan'))}")
print(f"is_missing(pd.NA): {is_missing(pd.NA)}")


def improved_is_missing(value):
    if value is None:
        return True

    # Check for pandas.NA (NAType) without importing pandas
    if hasattr(value, "__class__") and value.__class__.__name__ == "NAType":
        return True

    try:
        # NaN check
        return bool(value != value)
    except (ValueError, TypeError):
        return False


print(f"improved_is_missing(None): {improved_is_missing(None)}")
print(f"improved_is_missing(float('nan')): {improved_is_missing(float('nan'))}")
print(f"improved_is_missing(pd.NA): {improved_is_missing(pd.NA)}")
