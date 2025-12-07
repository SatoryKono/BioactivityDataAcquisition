"""Golden snapshot for activity_chembl pipeline outputs."""

from pathlib import Path

from .utils import load_expected_records

expected_activity_records = load_expected_records(
    Path("data/output/activity/activity.csv"), sort_key="activity_id"
)

__all__ = ["expected_activity_records"]
