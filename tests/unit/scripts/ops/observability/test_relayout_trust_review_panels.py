"""Tests for the bounded Trust Review panel relayout helper."""

from __future__ import annotations

import pytest

from scripts.ops.observability import relayout_trust_review_panels as subject

pytestmark = pytest.mark.unit


def test_transform_helpers_update_existing_entries_without_duplicates() -> None:
    panel = {
        "transformations": [
            {"id": "limit", "options": {"limitField": 2}},
            {
                "id": "organize",
                "options": {
                    "excludeByName": {"old": True},
                    "indexByName": {"old": 0},
                },
            },
        ]
    }

    subject.ensure_limit(panel, 4)
    subject.ensure_organize(panel, ["reasons"], {"trust_status": 0})

    transforms = panel["transformations"]
    assert [item["id"] for item in transforms] == ["limit", "organize"]
    assert transforms[0]["options"]["limitField"] == 4
    assert transforms[1]["options"]["excludeByName"] == {
        "old": True,
        "reasons": True,
    }
    assert transforms[1]["options"]["indexByName"] == {"trust_status": 0}
