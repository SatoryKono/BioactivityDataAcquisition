"""Behavioral coverage for small infrastructure guard branches in #10469."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.domain.composite.field_groups import FieldGroupId
from bioetl.infrastructure.config import config_root
from bioetl.infrastructure.config import contract_registry_loader as contract_loader
from bioetl.infrastructure.config import pipeline_payload_normalization as payload_normalization
from bioetl.infrastructure.config._base import Settings
from bioetl.infrastructure.config._composite_gold_schema_registry import (
    DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY,
)
from bioetl.infrastructure.config.field_group_loader import _parse_field
from bioetl.infrastructure.config.filter_config_loader import FilterConfigLoader
from bioetl.infrastructure.config.protein_class_target_type_loader import (
    ProteinClassTargetTypeMappingLoader,
)
from bioetl.infrastructure.control_plane import _durability
from bioetl.infrastructure.control_plane import file_run_ledger_store
from bioetl.infrastructure.observability import metrics_publisher_adapter
from bioetl.infrastructure.quality._decomposition_burndown_policy import (
    _validate_expiry_decomposition_targets_section,
)
from bioetl.infrastructure.quality._quarterly_targets_validation import (
    _validate_quarterly_targets_section,
)
from bioetl.infrastructure.schemas.base_schemas_pubchem import (
    BaseFilterColumnSchema,
    BaseInputFilterConfig,
)
from bioetl.infrastructure.schemas.source_profile_config import SourceProfileYamlConfig
from bioetl.infrastructure.storage.metadata_artifact_details import (
    resolve_artifact_semantics,
)
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.infrastructure.storage.support import retention
from bioetl.infrastructure.storage.versioned_table_resolver import (
    resolve_versioned_table_name,
)


def test_settings_normalizes_blank_optional_runtime_paths() -> None:
    settings = Settings(report_root="  ", runtime_source_id="", _env_file=None)

    assert settings.report_root is None
    assert settings.runtime_source_id is None


def test_lazy_composite_schema_registry_supports_iteration() -> None:
    names = tuple(DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY)

    assert names
    assert set(names) == set(DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY.keys())


def test_default_repo_root_uses_structural_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_module = tmp_path / "one" / "two" / "three" / "four" / "config_root.py"
    monkeypatch.setattr(config_root, "__file__", str(fake_module))

    assert config_root.get_default_repo_root() == fake_module.resolve().parents[4]


def test_contract_registry_rejects_non_mapping_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "registry.yaml"
    path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(contract_loader, "_load_yaml_with_timeout", lambda _path: [])

    with pytest.raises(ValueError, match="expected mapping root"):
        contract_loader.load_contract_registry_payload(path)


def test_field_mapping_rejects_non_list_columns() -> None:
    with pytest.raises(TypeError, match="columns.*must be a list"):
        _parse_field(
            {"base_name": "doi", "columns": "doi"},
            FieldGroupId.ID_AND_STATUS,
        )


def test_provider_filter_loader_accepts_legacy_top_level_shape(tmp_path: Path) -> None:
    provider_path = tmp_path / "providers" / "demo.yaml"
    provider_path.parent.mkdir(parents=True)
    provider_path.write_text("input_filter:\n  enabled: true\n", encoding="utf-8")

    loaded = FilterConfigLoader(tmp_path)._load_provider_layer("demo")

    assert loaded == {"input_filter": {"enabled": True}}


def test_source_section_treats_non_mapping_entity_source_as_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_config = SimpleNamespace(
        model_dump=lambda **_kwargs: {"source": {"api": "https://example.test"}}
    )
    monkeypatch.setattr(
        payload_normalization,
        "load_source_config_from_root",
        lambda *_args, **_kwargs: source_config,
    )
    config: dict[str, object] = {"provider": "demo", "source": "invalid"}

    payload_normalization.load_source_section(
        config, tmp_path / "configs" / "entities" / "demo" / "item.yaml"
    )

    assert config["source"] == {"api": "https://example.test"}


def test_protein_class_mapping_rejects_non_mapping_asset(tmp_path: Path) -> None:
    asset = tmp_path / "enums" / "protein_class_l1_target_type.asset.v1.json"
    asset.parent.mkdir(parents=True)
    asset.write_text(json.dumps([]), encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid protein class mapping asset"):
        ProteinClassTargetTypeMappingLoader(tmp_path).load()


def test_pubchem_filter_schema_converts_multiple_columns() -> None:
    config = BaseInputFilterConfig(
        enabled=True,
        source_path="ids.csv",
        columns=[
            BaseFilterColumnSchema(column_name="cid", filter_field="cid"),
            BaseFilterColumnSchema(column_name="sid", filter_field="sid"),
        ],
    )

    domain_config = config.to_domain()

    assert [column.column_name for column in domain_config.columns] == ["cid", "sid"]


def test_source_profile_accepts_absent_extraction_hash() -> None:
    assert SourceProfileYamlConfig(extraction_params_sha256=None).extraction_params_sha256 is None


def test_unknown_layer_has_explicit_unknown_artifact_semantics() -> None:
    assert (
        resolve_artifact_semantics(metadata=SimpleNamespace(), layer="experimental")
        == "unknown"
    )


def test_report_store_removes_file_target(tmp_path: Path) -> None:
    target = tmp_path / "run.json"
    target.write_text("{}", encoding="utf-8")

    FileRunReportStoreAdapter().remove_tree(str(target), root=str(tmp_path))

    assert not target.exists()


def test_retention_uses_explicit_short_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        retention,
        "get_settings",
        lambda: SimpleNamespace(test_mode=True, silver_dedup_timeout_seconds=3.5),
    )

    assert retention._resolve_deduplication_timeout_seconds() == 3.5


def test_versioned_table_rejects_blank_logical_name() -> None:
    with pytest.raises(ValueError, match="logical_table must be a non-empty string"):
        resolve_versioned_table_name("  ", "1.0.0")


def test_durability_flushes_when_policy_requires_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fsync = Mock()
    monkeypatch.setattr(_durability, "should_fsync_control_plane_writes", lambda: True)
    monkeypatch.setattr(_durability.os, "fsync", fsync)

    _durability.flush_control_plane_file_descriptor(17)

    fsync.assert_called_once_with(17)


def test_run_ledger_flushes_when_policy_requires_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fsync = Mock()
    monkeypatch.setattr(
        file_run_ledger_store, "_should_fsync_control_plane_writes", lambda: True
    )
    monkeypatch.setattr(file_run_ledger_store.os, "fsync", fsync)

    file_run_ledger_store._flush_file_descriptor(23)

    fsync.assert_called_once_with(23)


def test_metrics_adapter_delegates_delete_with_logger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegated = Mock(return_value=True)
    logger = Mock()
    monkeypatch.setattr(
        metrics_publisher_adapter, "delete_metrics_from_gateway", delegated
    )

    result = metrics_publisher_adapter.MetricsPublisherAdapter(logger).delete_from_gateway(
        gateway="http://push.test", run_label="run-1", grouping_key={"provider": "demo"}
    )

    assert result is True
    delegated.assert_called_once_with(
        gateway="http://push.test",
        run_label="run-1",
        grouping_key={"provider": "demo"},
        logger=logger,
    )


def test_expiry_targets_skip_invalid_quarter_before_budget_validation() -> None:
    errors: list[str] = []

    _validate_expiry_decomposition_targets_section(
        {
            "expiry_decomposition_targets": [
                {"quarter": "invalid", "max_entries_expiring_in_quarter": 1}
            ]
        },
        errors,
    )

    assert errors == [
        "expiry_decomposition_targets[0].quarter: expected 'YYYY-QN' format"
    ]


def test_quarterly_targets_skip_semantically_incomplete_entry() -> None:
    errors: list[str] = []

    _validate_quarterly_targets_section(
        {
            "quarterly_targets": [
                {
                    "quarter": "2026-Q1",
                    "max_total_exemptions": None,
                    "min_integral_score": 50,
                    "group_budgets": {},
                    "registry_budgets": {},
                }
            ]
        },
        group_names=set(),
        baseline_registry_names=set(),
        errors=errors,
    )

    assert errors == [
        "quarterly_targets[0].max_total_exemptions: expected int, got NoneType"
    ]
