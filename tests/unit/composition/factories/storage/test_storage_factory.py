# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Behavioral tests for StorageFactory via the canonical storage_factory facade."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.storage.audit import create_audit_port
from bioetl.composition.factories.storage.storage_factory import BronzeWriter
from bioetl.composition.factories.storage.storage_factory import GoldWriter
from bioetl.composition.factories.storage.storage_factory import SilverWriter
from bioetl.composition.factories.storage.storage_factory import StorageContext
from bioetl.composition.factories.storage.storage_factory import StorageFactory
from bioetl.domain.ports.noop import NoOpAudit


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
    audit_enabled: bool = False,
    audit_base_path: Path | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        test_mode=test_mode,
        bronze_path=bronze_path,
        silver_path=silver_path,
        gold_path=gold_path,
        checkpoint_path=checkpoint_path,
        data_dir=bronze_path.parent.parent,
        observability=SimpleNamespace(
            audit_enabled=audit_enabled,
            audit_base_path=audit_base_path,
        ),
        pipeline=SimpleNamespace(silver_resilience_enabled=False),
    )


def _make_config(
    *,
    bronze_layer: SimpleNamespace,
    silver_layer: SimpleNamespace,
    gold_layer: SimpleNamespace,
    pipeline_name: str = "chembl_activity",
) -> SimpleNamespace:
    return SimpleNamespace(
        provider="chembl",
        entity_type="activity",
        pipeline_name=pipeline_name,
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
        audit=MagicMock(),
    )

    assert isinstance(result, StorageContext)
    assert result.bronze_path == bronze_path
    assert result.silver_path == silver_path
    assert result.gold_path == gold_path
    assert result.checkpoints_path == settings.checkpoint_path
    assert Path(result.adapter.bronze.base_path) == bronze_path
    assert Path(result.adapter.silver.base_path) == silver_path.parent.parent
    assert Path(result.adapter.gold.base_path) == gold_path.parent.parent
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
        audit=MagicMock(),
    )

    assert result.bronze_path == settings.bronze_path
    assert result.silver_path == settings.silver_path
    assert result.gold_path == settings.gold_path
    assert result.adapter.silver.csv_exporter is not None
    assert result.adapter.gold.csv_exporter is not None
    assert Path(result.adapter.silver.csv_exporter.base_path) == settings.silver_path
    assert Path(result.adapter.gold.csv_exporter.base_path) == settings.gold_path


@pytest.mark.unit
def test_create_normalizes_delta_writer_base_paths_for_entity_scoped_yaml_paths(
    tmp_path: Path,
) -> None:
    """Delta writers should keep layer-root base paths even when context paths are scoped."""
    settings = _make_settings(
        test_mode=False,
        bronze_path=tmp_path / "default" / "bronze",
        silver_path=tmp_path / "default" / "silver",
        gold_path=tmp_path / "default" / "gold",
        checkpoint_path=tmp_path / "checkpoints",
    )
    config = _make_config(
        bronze_layer=_make_sink_layer(
            tmp_path / "custom" / "bronze" / "chembl" / "activity"
        ),
        silver_layer=_make_sink_layer(
            tmp_path / "custom" / "silver" / "chembl" / "activity"
        ),
        gold_layer=_make_sink_layer(
            tmp_path / "custom" / "gold" / "chembl" / "activity"
        ),
    )

    result = StorageFactory.create(
        settings=settings,
        config=config,
        logger=MagicMock(),
        metrics=MagicMock(),
        audit=MagicMock(),
    )

    assert result.silver_path == tmp_path / "custom" / "silver" / "chembl" / "activity"
    assert result.gold_path == tmp_path / "custom" / "gold" / "chembl" / "activity"
    assert Path(result.adapter.silver.base_path) == tmp_path / "custom" / "silver"
    assert Path(result.adapter.gold.base_path) == tmp_path / "custom" / "gold"


@pytest.mark.unit
def test_create_normalizes_windows_style_entity_scoped_delta_paths() -> None:
    """Writer base paths should normalize Windows-style scoped paths to layer roots."""
    settings = _make_settings(
        test_mode=False,
        bronze_path=Path("data/default/bronze"),
        silver_path=Path("data/default/silver"),
        gold_path=Path("data/default/gold"),
        checkpoint_path=Path("data/default/checkpoints"),
    )
    config = _make_config(
        bronze_layer=SimpleNamespace(
            path=r"data\output\bronze\chembl\activity",
            csv_export=_make_csv_config(r"data\output\bronze\csv", enabled=False),
            save_json=False,
            save_metadata=False,
            flat_structure=False,
        ),
        silver_layer=SimpleNamespace(
            path=r"data\output\silver\chembl\activity",
            csv_export=_make_csv_config(r"data\output\silver\csv", enabled=False),
            save_json=False,
            save_metadata=False,
            flat_structure=False,
        ),
        gold_layer=SimpleNamespace(
            path=r"data\output\gold\chembl\activity",
            csv_export=_make_csv_config(r"data\output\gold\csv", enabled=False),
            save_json=False,
            save_metadata=False,
            flat_structure=False,
        ),
    )

    result = StorageFactory.create(
        settings=settings,
        config=config,
        logger=MagicMock(),
        metrics=MagicMock(),
        audit=MagicMock(),
    )

    assert Path(result.adapter.silver.base_path) == Path("data/output/silver")
    assert Path(result.adapter.gold.base_path) == Path("data/output/gold")


@pytest.mark.unit
def test_create_forwards_optional_runtime_collaborators_to_adapter_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Top-level StorageFactory should preserve optional runtime collaborators."""
    ctx = SimpleNamespace(
        bronze_path=tmp_path / "bronze",
        silver_path=tmp_path / "silver",
        gold_path=tmp_path / "gold",
    )
    adapter = MagicMock()
    mock_build_ctx = MagicMock(return_value=ctx)
    mock_create_adapter = MagicMock(return_value=adapter)
    monkeypatch.setattr(
        "bioetl.composition.factories.storage.factory.build_storage_creation_context",
        mock_build_ctx,
    )
    monkeypatch.setattr(
        "bioetl.composition.factories.storage.factory.create_storage_adapter",
        mock_create_adapter,
    )

    settings = _make_settings(
        test_mode=False,
        bronze_path=tmp_path / "default" / "bronze",
        silver_path=tmp_path / "default" / "silver",
        gold_path=tmp_path / "default" / "gold",
        checkpoint_path=tmp_path / "checkpoints",
    )
    config = _make_config(
        bronze_layer=_make_sink_layer(tmp_path / "yaml" / "bronze"),
        silver_layer=_make_sink_layer(tmp_path / "yaml" / "silver"),
        gold_layer=_make_sink_layer(tmp_path / "yaml" / "gold"),
    )
    logger = MagicMock()
    metrics = MagicMock()
    tracing = MagicMock()
    audit = MagicMock()
    metadata_coordinator = MagicMock()
    silver_validator = MagicMock()

    result = StorageFactory.create(
        settings=settings,
        config=config,
        logger=logger,
        metrics=metrics,
        audit=audit,
        tracing=tracing,
        metadata_coordinator=metadata_coordinator,
        silver_validator=silver_validator,
    )

    assert isinstance(result, StorageContext)
    assert result.adapter is adapter
    assert result.bronze_path == ctx.bronze_path
    assert result.silver_path == ctx.silver_path
    assert result.gold_path == ctx.gold_path
    assert result.checkpoints_path == settings.checkpoint_path
    mock_build_ctx.assert_called_once_with(
        settings=settings,
        config=config,
        logger=logger,
        pipeline_name=config.pipeline_name,
    )
    mock_create_adapter.assert_called_once_with(
        ctx=ctx,
        bronze_writer_cls=BronzeWriter,
        silver_writer_cls=SilverWriter,
        gold_writer_cls=GoldWriter,
        settings=settings,
        config=config,
        logger=logger,
        metrics=metrics,
        audit=audit,
        tracing=tracing,
        metadata_coordinator=metadata_coordinator,
        silver_validator=silver_validator,
    )


@pytest.mark.unit
def test_create_uses_explicit_noop_audit_by_default(tmp_path: Path) -> None:
    """Canonical storage path should always receive an explicit audit port."""
    settings = _make_settings(
        test_mode=True,
        bronze_path=tmp_path / "test-root" / "bronze",
        silver_path=tmp_path / "test-root" / "silver",
        gold_path=tmp_path / "test-root" / "gold",
        checkpoint_path=tmp_path / "test-root" / "checkpoints",
    )
    config = _make_config(
        bronze_layer=_make_sink_layer(tmp_path / "yaml" / "bronze"),
        silver_layer=_make_sink_layer(tmp_path / "yaml" / "silver"),
        gold_layer=_make_sink_layer(tmp_path / "yaml" / "gold"),
    )

    result = StorageFactory.create(
        settings=settings,
        config=config,
        logger=MagicMock(),
        metrics=MagicMock(),
        audit=NoOpAudit(),
    )

    assert isinstance(result.adapter.bronze._audit, NoOpAudit)
    assert result.adapter.bronze._audit is result.adapter.silver._audit
    assert result.adapter.bronze._audit is result.adapter.gold._audit


@pytest.mark.unit
def test_create_uses_file_audit_adapter_when_enabled(tmp_path: Path) -> None:
    """Enabled audit should propagate one configured file adapter to all writers."""
    audit_path = tmp_path / "audit"
    settings = _make_settings(
        test_mode=True,
        bronze_path=tmp_path / "test-root" / "bronze",
        silver_path=tmp_path / "test-root" / "silver",
        gold_path=tmp_path / "test-root" / "gold",
        checkpoint_path=tmp_path / "test-root" / "checkpoints",
        audit_enabled=True,
        audit_base_path=audit_path,
    )
    config = _make_config(
        bronze_layer=_make_sink_layer(tmp_path / "yaml" / "bronze"),
        silver_layer=_make_sink_layer(tmp_path / "yaml" / "silver"),
        gold_layer=_make_sink_layer(tmp_path / "yaml" / "gold"),
    )

    audit = create_audit_port(
        settings=settings,
        logger=MagicMock(),
        metrics=MagicMock(),
        tracing=MagicMock(),
    )

    result = StorageFactory.create(
        settings=settings,
        config=config,
        logger=MagicMock(),
        metrics=MagicMock(),
        audit=audit,
    )

    bronze_audit = result.adapter.bronze._audit
    silver_audit = result.adapter.silver._audit
    gold_audit = result.adapter.gold._audit
    assert bronze_audit is not None
    assert silver_audit is not None
    assert gold_audit is not None
    assert type(bronze_audit).__name__ == "FileAuditAdapter"
    assert bronze_audit is silver_audit
    assert bronze_audit is gold_audit
    assert bronze_audit.base_path == audit_path


@pytest.mark.unit
def test_create_resolves_tracing_once_at_storage_factory_boundary(
    tmp_path: Path,
) -> None:
    """StorageFactory owns disabled tracing fallback instead of layer sub-factories."""
    settings = _make_settings(
        test_mode=False,
        bronze_path=tmp_path / "default" / "bronze",
        silver_path=tmp_path / "default" / "silver",
        gold_path=tmp_path / "default" / "gold",
        checkpoint_path=tmp_path / "checkpoints",
    )
    config = _make_config(
        bronze_layer=_make_sink_layer(tmp_path / "yaml" / "bronze"),
        silver_layer=_make_sink_layer(tmp_path / "yaml" / "silver"),
        gold_layer=_make_sink_layer(tmp_path / "yaml" / "gold"),
    )
    logger = MagicMock()
    metrics = MagicMock()
    resolved_tracing = MagicMock()
    ctx = SimpleNamespace(
        bronze_path=tmp_path / "bronze",
        silver_path=tmp_path / "silver",
        gold_path=tmp_path / "gold",
        bronze_config=config.sink["bronze"],
        silver_config=config.sink["silver"],
        gold_config=config.sink["gold"],
        bronze_flat=False,
        silver_flat=False,
        gold_flat=False,
        bronze_csv_exporter=None,
        silver_csv_exporter=None,
        gold_csv_exporter=None,
    )
    adapter = MagicMock()

    with (
        patch(
            "bioetl.composition.factories.storage.factory.build_storage_creation_context",
            return_value=ctx,
        ) as mock_build_ctx,
        patch(
            "bioetl.composition.factories.storage.factory.resolve_tracing_port",
            return_value=resolved_tracing,
        ) as mock_resolve_tracing,
        patch(
            "bioetl.composition.factories.storage.factory.create_storage_adapter",
            return_value=adapter,
        ) as mock_create_adapter,
    ):
        result = StorageFactory.create(
            settings=settings,
            config=config,
            logger=logger,
            metrics=metrics,
            audit=MagicMock(),
            tracing=None,
        )

    mock_build_ctx.assert_called_once_with(
        settings=settings,
        config=config,
        logger=logger,
        pipeline_name=config.pipeline_name,
    )
    mock_resolve_tracing.assert_called_once_with(tracer=None, settings=settings)
    assert mock_create_adapter.call_args.kwargs["tracing"] is resolved_tracing
    assert result.adapter is adapter
