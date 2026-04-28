"""Unit tests for composition observability/data-source wiring helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from bioetl.composition.factories._observability_wiring import (
    _create_cached_bronze_data_source,
)
from bioetl.domain.context import CachedBronzeContext


def test_cached_bronze_data_source_reuses_shared_metrics(
    monkeypatch,
) -> None:
    """Cached-bronze path must not silently downgrade to NoOpMetrics."""
    captured: dict[str, object] = {}

    class _BronzeWriterSpy:
        def __init__(self, **kwargs: object) -> None:
            captured["writer_kwargs"] = kwargs

    class _CachedBronzeDataSourceSpy:
        def __init__(self, **kwargs: object) -> None:
            captured["data_source_kwargs"] = kwargs

    import bioetl.composition.factories._observability_wiring as wiring_module

    monkeypatch.setattr(
        wiring_module,
        "Path",
        Path,
    )

    import bioetl.infrastructure.adapters as adapters_module
    import bioetl.infrastructure.storage.bronze_writer as bronze_writer_module

    monkeypatch.setattr(
        adapters_module,
        "CachedBronzeDataSource",
        _CachedBronzeDataSourceSpy,
    )
    monkeypatch.setattr(
        bronze_writer_module,
        "BronzeWriter",
        _BronzeWriterSpy,
    )

    shared_metrics = MagicMock(name="shared_metrics")
    logger = MagicMock(name="logger")
    settings = SimpleNamespace(bronze_path=Path("/tmp/bronze"))
    pipeline_config = SimpleNamespace(provider="chembl", entity_type="activity")
    cached_bronze = CachedBronzeContext(
        enabled=True,
        bronze_path=None,
        bronze_date="2026-04-01",
    )

    _create_cached_bronze_data_source(
        settings=settings,
        pipeline_config=pipeline_config,
        logger=logger,
        metrics=shared_metrics,
        cached_bronze=cached_bronze,
    )

    writer_kwargs = captured["writer_kwargs"]
    assert writer_kwargs["metrics"] is shared_metrics
    assert writer_kwargs["base_path"] == Path("/tmp/bronze/chembl/activity")
    assert captured["data_source_kwargs"]["bronze_date"] == "2026-04-01"
