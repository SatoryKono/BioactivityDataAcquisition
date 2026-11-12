"""The W153 contract rejects a function. Pipeline integration stays NOT_RUN."""

from __future__ import annotations

import pytest

from iuphar_target_class.w153 import INTEGRATION_REASON, INTEGRATION_STATUS, join_w153

pytestmark = pytest.mark.unit


def test_w153_join_receives_computed_rows() -> None:
    rows = ({"input_row_id": "1", "effective_class": "Receptor"},)
    assert join_w153(rows) == rows


def test_w153_join_rejects_a_function() -> None:
    def table() -> tuple[dict[str, str], ...]:
        return ()

    with pytest.raises(TypeError, match="computed rows"):
        join_w153(table)  # type: ignore[arg-type]


def test_pipeline_integration_is_not_run() -> None:
    assert INTEGRATION_STATUS == "NOT_RUN"
    assert "BioETL" in INTEGRATION_REASON
