"""Behavioral tests for StorageFactory via the canonical storage_factory facade."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.storage.storage_factory import StorageContext
from bioetl.composition.factories.storage.storage_factory import StorageFactory


def _make_csv_config(path: str, *, enabled: bool) -> SimpleNamespace:
    return SimpleNamespace(
        enabled=enabled,
        path=path,
        delimiter=",",
        header=True,
        encoding="utf-8",
    )


def _make_sink_layer(
    path: Path,
    *,
    csv_enabled: bool = False,
    csv_path: str | None = None,
    save_json: bool = False,
    save_metadata: bool = False,
    flat_structure: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        path=str(path),
        csv_export=_make_csv_config(
            csv_path or str(path / "csv"),
            enabled=csv_enabled,
        ),
        save_json=save_json,
        save_metadata=save_metadata,
        flat_structure=flat_structure,
    )


def _make_settings(
    *,
    test_mode: bool,
    bronze_path: Path,
    silver_path: Path,
    gold_path: Path,
    checkpoint_path: Path,
) -> SimpleNamespace:
    return SimpleNamespace(
        test_mode=test_mode,
        bronze_path=bronze_path,
        silver_path=silver_path,
        gold_path=gold_path,
        checkpoint_path=checkpoint_path,
        pipeline=SimpleNamespace(silver_resilience_enabled=False),
    )


def _make_config(
    *,
    bronze_layer: SimpleNamespace,
    silver_layer: SimpleNamespace,
    gold_layer: SimpleNamespace,
) -> SimpleNamespace:
    return SimpleNamespace(
        sink={
            "bronze": bronze_layer,
            "silver": silver_layer,
            "gold": gold_layer,
        },
        transform=SimpleNamespace(version="v-test", steps=["extract", "normalize"]),
    )


@pytest.mark.unit
def test_create_uses_canonical_yaml_paths_and_returns_storage_context(
    tmp_path: Path,
) -> None:
    """Non-test mode should honor canonical YAML paths across all layers."""
    bronze_path = tmp_path / "yaml" / "bronze" / "chembl" / "activity"
    silver_path = tmp_path / "yaml" / "silver" / "chembl" / "activity"
    gold_path = tmp_path / "yaml" / "gold" / "chembl" / "activity"
    settings = _make_settings(
        test_mode=False,
        bronze_path=tmp_path / "default" / "bronze",
        silver_path=tmp_path / "default" / "silver",
        gold_path=tmp_path / "default" / "gold",
        checkpoint_path=tmp_path / "checkpoints",
    )
    config = _make_config(
        bronze_layer=_make_sink_layer(bronze_path),
        silver_layer=_make_sink_layer(silver_path),
        gold_layer=_make_sink_layer(gold_path),
    )
    logger = MagicMock()
    metrics = MagicMock()

    result = StorageFactory.create(
        settings=settings,
        config=config,
        logger=logger,
        metrics=metrics,
    )

    assert isinstance(result, StorageContext)
    assert result.bronze_path == bronze_path
    assert result.silver_path == silver_path
    assert result.gold_path == gold_path
    assert result.checkpoints_path == settings.checkpoint_path
    assert Path(result.adapter.bronze.base_path) == bronze_path
    assert Path(result.adapter.silver.base_path) == silver_path
    assert Path(result.adapter.gold.base_path) == gold_path
    assert result.adapter.silver.csv_exporter is None
    assert result.adapter.gold.csv_exporter is None
    logger.info.assert_any_call(
        "Using local storage",
        bronze_path=str(bronze_path),
        silver_path=str(silver_path),
        gold_path=str(gold_path),
    )


@pytest.mark.unit
def test_create_uses_test_mode_paths_and_overrides_csv_export_targets(
    tmp_path: Path,
) -> None:
    """Test mode should ignore YAML paths and bind CSV exporters to test roots."""
    settings = _make_settings(
        test_mode=True,
        bronze_path=tmp_path / "test-root" / "bronze",
        silver_path=tmp_path / "test-root" / "silver",
        gold_path=tmp_path / "test-root" / "gold",
        checkpoint_path=tmp_path / "test-root" / "checkpoints",
    )
    config = _make_config(
        bronze_layer=_make_sink_layer(tmp_path / "yaml" / "bronze"),
        silver_layer=_make_sink_layer(
            tmp_path / "yaml" / "silver",
            csv_enabled=True,
            csv_path=str(tmp_path / "custom" / "silver-csv"),
        ),
        gold_layer=_make_sink_layer(
            tmp_path / "yaml" / "gold",
            csv_enabled=True,
            csv_path=str(tmp_path / "custom" / "gold-csv"),
        ),
    )

    result = StorageFactory.create(
        settings=settings,
        config=config,
        logger=MagicMock(),
        metrics=MagicMock(),
    )

    assert result.bronze_path == settings.bronze_path
    assert result.silver_path == settings.silver_path
    assert result.gold_path == settings.gold_path
    assert result.adapter.silver.csv_exporter is not None
    assert result.adapter.gold.csv_exporter is not None
    assert Path(result.adapter.silver.csv_exporter.base_path) == settings.silver_path
    assert Path(result.adapter.gold.csv_exporter.base_path) == settings.gold_path
