"""Fast schema drift gate for a representative subset of Silver pipelines.

This suite intentionally covers a small cross-section of Silver schemas so the
repository gets regular per-PR schema drift protection without turning the full
Silver contract surface into a mandatory fast lane.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.contract.silver_schemas.conftest import (
    REPRESENTATIVE_SILVER_SCHEMAS,
    assert_schema_matches_snapshot,
)

UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"


@pytest.mark.contracts
@pytest.mark.no_api
class TestSelectedPipelineSchemaDrift:
    """Representative schema-watch gate for regular CI."""

    @pytest.mark.parametrize("schema_name", REPRESENTATIVE_SILVER_SCHEMAS)
    def test_selected_pipeline_schema_matches_snapshot(
        self, schema_name: str, snapshots_dir: Path
    ) -> None:
        """Selected Silver pipelines MUST fail fast on schema drift in CI."""
        assert_schema_matches_snapshot(
            schema_name,
            snapshots_dir=snapshots_dir,
            update_snapshots=UPDATE_SNAPSHOTS,
        )
