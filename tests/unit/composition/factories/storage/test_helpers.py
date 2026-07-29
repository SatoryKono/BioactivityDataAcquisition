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
"""Unit tests for storage factory helper functions."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.storage._helpers import (
    create_csv_exporter_from_config,
    get_layer_configs,
    log_configured_export_status,
    log_export_status,
    resolve_export_flags,
    resolve_flat_structure_flags,
    resolve_layer_path,
    resolve_storage_paths,
)


# --- resolve_layer_path ---


@pytest.mark.unit
def test_resolve_layer_path_uses_yaml_path_when_enabled() -> None:
    """resolve_layer_path uses config path when use_yaml_paths is True."""
    config = SimpleNamespace(path="/custom/silver")
    result = resolve_layer_path(config, Path("/default"), use_yaml_paths=True)  # type: ignore[arg-type]
    assert result == Path("/custom/silver")


@pytest.mark.unit
def test_resolve_layer_path_uses_default_when_disabled() -> None:
    """resolve_layer_path uses default when use_yaml_paths is False."""
    config = SimpleNamespace(path="/custom/silver")
    result = resolve_layer_path(config, Path("/default"), use_yaml_paths=False)  # type: ignore[arg-type]
    assert result == Path("/default")


@pytest.mark.unit
def test_resolve_layer_path_uses_default_when_config_is_none() -> None:
    """resolve_layer_path uses default when config is None."""
    result = resolve_layer_path(None, Path("/default"), use_yaml_paths=True)  # type: ignore[arg-type]
    assert result == Path("/default")


@pytest.mark.unit
def test_resolve_layer_path_uses_default_when_config_path_is_none() -> None:
    """resolve_layer_path uses default when config.path is None."""
    config = SimpleNamespace(path=None)
    result = resolve_layer_path(config, Path("/default"), use_yaml_paths=True)  # type: ignore[arg-type]
    assert result == Path("/default")


# --- get_layer_configs ---


@pytest.mark.unit
def test_get_layer_configs_extracts_all() -> None:
    """get_layer_configs extracts bronze, silver, gold from sink dict."""
    bronze_cfg = SimpleNamespace(path="/b")
    silver_cfg = SimpleNamespace(path="/s")
    gold_cfg = SimpleNamespace(path="/g")
    config = SimpleNamespace(
        sink={"bronze": bronze_cfg, "silver": silver_cfg, "gold": gold_cfg}
    )
    b, s, g = get_layer_configs(config)  # type: ignore[arg-type]
    assert b is bronze_cfg
    assert s is silver_cfg
    assert g is gold_cfg


@pytest.mark.unit
def test_get_layer_configs_missing_layers() -> None:
    """get_layer_configs returns None for missing layers."""
    config = SimpleNamespace(sink={})
    b, s, g = get_layer_configs(config)  # type: ignore[arg-type]
    assert b is None
    assert s is None
    assert g is None


# --- resolve_storage_paths ---


@pytest.mark.unit
def test_resolve_storage_paths_test_mode() -> None:
    """resolve_storage_paths uses defaults in test mode."""
    settings = SimpleNamespace(
        test_mode=True,
        bronze_path=Path("/default/bronze"),
        silver_path=Path("/default/silver"),
        gold_path=Path("/default/gold"),
    )
    use_yaml, bronze, silver, gold = resolve_storage_paths(
        settings,
        None,
        None,
        None,  # type: ignore[arg-type]
    )
    assert use_yaml is False
    assert bronze == Path("/default/bronze")
    assert silver == Path("/default/silver")
    assert gold == Path("/default/gold")


@pytest.mark.unit
def test_resolve_storage_paths_prod_mode_with_configs() -> None:
    """resolve_storage_paths uses config paths in prod mode."""
    settings = SimpleNamespace(
        test_mode=False,
        bronze_path=Path("/default/bronze"),
        silver_path=Path("/default/silver"),
        gold_path=Path("/default/gold"),
    )
    bronze_cfg = SimpleNamespace(path="/yaml/bronze")
    silver_cfg = SimpleNamespace(path="/yaml/silver")
    gold_cfg = SimpleNamespace(path="/yaml/gold")
    use_yaml, bronze, silver, gold = resolve_storage_paths(
        settings,
        bronze_cfg,
        silver_cfg,
        gold_cfg,  # type: ignore[arg-type]
    )
    assert use_yaml is True
    assert bronze == Path("/yaml/bronze")
    assert silver == Path("/yaml/silver")
    assert gold == Path("/yaml/gold")


# --- resolve_export_flags ---


@pytest.mark.unit
def test_resolve_export_flags_all_set() -> None:
    """resolve_export_flags reads flags from all configs."""
    bronze = SimpleNamespace(save_json=True, save_metadata=True)
    silver = SimpleNamespace(save_metadata=True)
    gold = SimpleNamespace(save_metadata=False)
    sj, bm, sm, gm = resolve_export_flags(bronze, silver, gold)  # type: ignore[arg-type]
    assert sj is True
    assert bm is True
    assert sm is True
    assert gm is False


@pytest.mark.unit
def test_resolve_export_flags_all_none() -> None:
    """resolve_export_flags returns False for all when configs are None."""
    sj, bm, sm, gm = resolve_export_flags(None, None, None)  # type: ignore[arg-type]
    assert sj is False
    assert bm is False
    assert sm is False
    assert gm is False


# --- resolve_flat_structure_flags ---


@pytest.mark.unit
def test_resolve_flat_structure_flags_enabled() -> None:
    """resolve_flat_structure_flags returns True when both flag and yaml_paths set."""
    bronze = SimpleNamespace(flat_structure=True)
    silver = SimpleNamespace(flat_structure=False)
    gold = SimpleNamespace(flat_structure=True)
    b, s, g = resolve_flat_structure_flags(
        bronze_config=bronze,  # type: ignore[arg-type]
        silver_config=silver,  # type: ignore[arg-type]
        gold_config=gold,  # type: ignore[arg-type]
        use_yaml_paths=True,
    )
    assert b is True
    assert s is False
    assert g is True


@pytest.mark.unit
def test_resolve_flat_structure_flags_disabled_without_yaml_paths() -> None:
    """resolve_flat_structure_flags returns False when use_yaml_paths is False."""
    bronze = SimpleNamespace(flat_structure=True)
    b, s, g = resolve_flat_structure_flags(
        bronze_config=bronze,  # type: ignore[arg-type]
        silver_config=None,  # type: ignore[arg-type]
        gold_config=None,  # type: ignore[arg-type]
        use_yaml_paths=False,
    )
    assert b is False
    assert s is False
    assert g is False


# --- create_csv_exporter_from_config ---


@pytest.mark.unit
def test_create_csv_exporter_none_when_disabled() -> None:
    """create_csv_exporter_from_config returns None when disabled."""
    cfg = SimpleNamespace(enabled=False)
    result = create_csv_exporter_from_config(cfg, MagicMock())
    assert result is None


@pytest.mark.unit
def test_create_csv_exporter_none_when_cfg_is_none() -> None:
    """create_csv_exporter_from_config returns None when config is None."""
    result = create_csv_exporter_from_config(None, MagicMock())
    assert result is None


@pytest.mark.unit
def test_create_csv_exporter_none_when_no_path() -> None:
    """create_csv_exporter_from_config returns None when path unresolvable."""
    cfg = SimpleNamespace(enabled=True, path=None)
    result = create_csv_exporter_from_config(cfg, MagicMock())
    assert result is None


@pytest.mark.unit
def test_create_csv_exporter_from_config_with_path(tmp_path: Path) -> None:
    """create_csv_exporter_from_config creates exporter with config path."""
    cfg = SimpleNamespace(
        enabled=True,
        path=str(tmp_path),
        delimiter=";",
        header=True,
        encoding="utf-8",
    )
    logger = MagicMock()
    result = create_csv_exporter_from_config(cfg, logger)
    assert result is not None


@pytest.mark.unit
def test_create_csv_exporter_with_override_path(tmp_path: Path) -> None:
    """create_csv_exporter_from_config uses override_path when provided."""
    cfg = SimpleNamespace(
        enabled=True,
        path="/original",
        delimiter=",",
        header=True,
        encoding="utf-8",
    )
    override = tmp_path / "override"
    result = create_csv_exporter_from_config(cfg, MagicMock(), override_path=override)
    assert result is not None


# --- log_export_status ---


@pytest.mark.unit
def test_log_export_status_all_enabled() -> None:
    """log_export_status logs all active export settings."""
    logger = MagicMock()
    silver_csv = SimpleNamespace(base_path="/csv/silver")
    gold_csv = SimpleNamespace(base_path="/csv/gold")
    log_export_status(
        logger,
        save_json=True,
        silver_csv_exporter=silver_csv,  # type: ignore[arg-type]
        gold_csv_exporter=gold_csv,  # type: ignore[arg-type]
        bronze_save_metadata=True,
        silver_save_metadata=True,
        gold_save_metadata=True,
    )
    assert logger.info.call_count == 6


@pytest.mark.unit
def test_log_export_status_none_enabled() -> None:
    """log_export_status does not log when nothing is enabled."""
    logger = MagicMock()
    log_export_status(
        logger,
        save_json=False,
        silver_csv_exporter=None,
        gold_csv_exporter=None,
        bronze_save_metadata=False,
        silver_save_metadata=False,
        gold_save_metadata=False,
    )
    logger.info.assert_not_called()


# --- log_configured_export_status ---


@pytest.mark.unit
def test_log_configured_export_status_delegates() -> None:
    """log_configured_export_status resolves flags and logs."""
    logger = MagicMock()
    bronze = SimpleNamespace(save_json=True, save_metadata=False)
    log_configured_export_status(
        logger=logger,
        bronze_config=bronze,  # type: ignore[arg-type]
        silver_config=None,  # type: ignore[arg-type]
        gold_config=None,  # type: ignore[arg-type]
        silver_csv_exporter=None,
        gold_csv_exporter=None,
    )
    assert logger.info.call_count == 1  # save_json only
