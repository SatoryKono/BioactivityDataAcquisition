"""Assert-density policy for table-driven unit suites (#6646)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

_REPO = Path(__file__).resolve().parents[2]
_POLICY = _REPO / "configs/quality/unit_assert_density_policy.yaml"


def test_unit_assert_density_policy_reviews_known_low_ratio_modules() -> None:
    payload = yaml.safe_load(_POLICY.read_text(encoding="utf-8"))
    assert payload["policy"]["forbid_empty_test_bodies"] is True
    reviewed = payload["reviewed_modules"]
    assert isinstance(reviewed, list) and reviewed
    for row in reviewed:
        path = _REPO / row["path"]
        assert path.is_file(), f"missing reviewed module {row['path']}"
        assert row["classification"] in {
            "table_driven_parametrized",
            "metrics_side_effect_spy",
        }
