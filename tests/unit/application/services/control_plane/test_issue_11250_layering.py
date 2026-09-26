"""Focused coverage for composition residuals moved in #11250."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.control_plane.ledger.artifact_recording import (
    canonical_lineage_fragment_id,
    record_input_snapshots_from_artifact,
)
from bioetl.infrastructure.control_plane.provider_health_evidence import (
    persist_probe_health_observation,
)


def test_lineage_fragment_id_rejects_layer_alias() -> None:
    assert canonical_lineage_fragment_id("bronze") is None
    assert canonical_lineage_fragment_id("frag-1") == "frag-1"


def test_input_snapshot_requires_snapshot_id() -> None:
    service = MagicMock()
    with pytest.raises(ValueError, match="snapshot_id"):
        record_input_snapshots_from_artifact(
            service,
            layer="bronze",
            artifact_path="bronze/batch",
            details={
                "input_snapshots": [
                    {"immutable_uri": "s3://snap", "content_hash": "abc"}
                ]
            },
        )
    service.record_input_snapshot_published.assert_not_called()


def test_probe_health_observation_persists_known_status() -> None:
    store = MagicMock()
    store.list_all.return_value = []
    metrics = MagicMock()
    checked = datetime(2026, 1, 1, tzinfo=UTC)
    persist_probe_health_observation(
        store=store,
        metrics=metrics,
        provider="chembl",
        status_name="healthy",
        checked_at=checked,
        endpoint="https://example.test/health",
        error=None,
        now=checked,
    )
    store.persist.assert_called_once()
    store.list_all.assert_called()
