"""Focused two-line composition coverage for #10469."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import bioetl.composition.factories.dq as dq_factory
import bioetl.composition.factories.services.port_factories as port_factories
import bioetl.composition.bootstrap.runtime.composite_support_helpers as composite_support
import bioetl.composition.factories.pipeline._assembler_factory as assembler_factory
import bioetl.composition.observability_runtime as observability_runtime
from bioetl.composition import _workflow_services
from bioetl.composition.bootstrap.runtime.composite_support_helpers import (
    _composite_basics_uuid_factory,
    bootstrap_runtime_basics_facade,
)
from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.factories.datasource.adapter_helpers import (
    SyncAdapterHelperServices,
)
from bioetl.composition.factories.pipeline._assembler_factory import (
    GenericPipelineFactory,
    _optional_string_kwarg,
)
from bioetl.composition.factories.pipeline.registry import get_factory
from bioetl.composition.factories.pipeline.run_context_contract_identity import (
    _normalize_contract_identity_result,
    runtime_requires_strict_contract_identity,
)
from bioetl.composition.observability_runtime import (
    _ensure_publication_seeds,
    _seed_run_type,
)
from bioetl.composition.providers._chembl_target_protein_classification_helpers import (
    coerce_positive_int,
    leaf_ids_from_component_row,
)
from bioetl.composition.runtime_builders._effective_config_graph_support import (
    _load_config_graph_references,
    _resolve_config_graph_reference,
)
from bioetl.composition.runtime_builders.control_plane import attach_manifest_id


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "module_name",
    [
        "bioetl.application.services.control_plane.manifest.diagnostics.persistence",
        "bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.persistence_policy",
        "bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family",
        "bioetl.infrastructure.compat",
    ],
)
def test_marker_modules_are_importable(module_name: str) -> None:
    assert importlib.import_module(module_name).__name__ == module_name


def test_workflow_metrics_factory_rejects_invalid_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(port_factories, "create_metrics", object(), raising=False)

    with pytest.raises(TypeError, match="does not satisfy"):
        _workflow_services._create_workflow_metrics(MagicMock())


def test_workflow_ledger_factory_builds_bound_service() -> None:
    manifest = SimpleNamespace(
        manifest_id="manifest-1",
        workflow_run_id="run-1",
        workflow_name="workflow",
    )
    service = _workflow_services._create_workflow_ledger_service(MagicMock(), manifest)

    assert service.manifest_id == "manifest-1"


def test_composite_uuid_factory_returns_text_uuid() -> None:
    assert isinstance(_composite_basics_uuid_factory(), str)


def test_composite_runtime_facade_adapts_logger_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_logger = object()
    bootstrap = MagicMock(return_value=expected_logger)
    monkeypatch.setattr(composite_support, "bootstrap_logger", bootstrap)

    def implementation(**kwargs: object) -> object:
        logger_factory = kwargs["logger_bootstrapper"]
        return logger_factory("pipeline", MagicMock(), "INFO")

    result = bootstrap_runtime_basics_facade(
        config=MagicMock(), run_id=None, bootstrap_runtime_basics_impl=implementation
    )

    assert result is expected_logger


def test_filter_config_builder_direct_multi_id_paths() -> None:
    direct = FilterConfigBuilder.from_direct_multi_ids(
        multi_filter_ids={"field": ("A", "B")},
        valid_combinations=frozenset({("A", "B")}),
    )
    rebuilt = FilterConfigBuilder.build(
        yaml_filter=SimpleNamespace(batch_size=10),
        direct_multi_filter_ids={"field": ("A", "B")},
        direct_valid_combinations=frozenset({("A", "B")}),
    )

    assert direct.enabled and rebuilt.enabled


def test_sync_adapter_helper_services_build_context_and_kwargs() -> None:
    services = SyncAdapterHelperServices(
        metrics=MagicMock(),
        error_handler=MagicMock(),
        request_collector=MagicMock(),
    )

    assert services.build_dependency_context().metrics is services.metrics
    assert services.as_injection_kwargs()["error_handler"] is services.error_handler


def test_dq_factory_facade_reports_dir_and_unknown_attribute() -> None:
    assert dq_factory.__dir__() == sorted(dq_factory.__dir__())
    with pytest.raises(AttributeError):
        dq_factory.__getattr__("missing_export")


def test_pipeline_factory_helpers_cover_optional_and_unknown_paths() -> None:
    assert _optional_string_kwarg({"value": "x"}, "value") == "x"
    with pytest.raises(KeyError, match="Unknown pipeline"):
        get_factory("definitely_missing_pipeline")


def test_generic_pipeline_factory_builds_request_from_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = object.__new__(GenericPipelineFactory)
    factory.pipeline_name = "chembl_activity"
    factory.silver_schema = object()
    factory.gold_schema = object()
    built_request = MagicMock()
    expected = object()
    monkeypatch.setattr(
        assembler_factory,
        "_build_pipeline_create_runner_request_from_kwargs",
        MagicMock(return_value=built_request),
    )
    monkeypatch.setattr(
        assembler_factory,
        "build_create_factory_runner_request",
        MagicMock(return_value=built_request),
    )
    monkeypatch.setattr(
        assembler_factory,
        "create_runner_from_factory",
        MagicMock(return_value=expected),
    )

    assert factory.create_runner(settings=MagicMock()) is expected


def test_contract_identity_helpers_reject_shape_and_detect_strict_profile() -> None:
    with pytest.raises(RuntimeError, match="legacy 5-field"):
        _normalize_contract_identity_result(("only",))
    assert runtime_requires_strict_contract_identity(
        SimpleNamespace(required_persistence_profile="replay_ready")
    )


def test_observability_seed_run_type_handles_unknown_workflow_context() -> None:
    assert _seed_run_type(None, "workflow") == ""


def test_publication_seed_refresh_skips_empty_workflow_run_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refresh = MagicMock()
    ensure = MagicMock()
    monkeypatch.setattr(
        observability_runtime, "refresh_control_plane_integrity_metrics", refresh
    )
    monkeypatch.setattr(
        observability_runtime,
        "ensure_required_control_plane_publication_series",
        ensure,
    )

    assert (
        _ensure_publication_seeds(
            settings=object(),
            pipeline_name="chembl_activity",
            run_type=None,
            pipeline_names=(),
            workflow_name="workflow",
            logger=None,
        )
        == {}
    )
    ensure.assert_not_called()
    refresh.assert_called_once()


def test_protein_classification_helpers_cover_direct_leaf_and_invalid_integer() -> None:
    assert leaf_ids_from_component_row({"protein_classification_ids": [1, 2]}) == (
        1,
        2,
    )
    assert coerce_positive_int(object()) is None


def test_effective_config_graph_rejects_escape_and_non_yaml(tmp_path: Path) -> None:
    assert (
        _resolve_config_graph_reference(raw_value="../../escape.yaml", base_dir="x")
        is None
    )
    file_path = tmp_path / "config.txt"
    file_path.write_text("ignored", encoding="utf-8")
    assert (
        _load_config_graph_references(relative_path="config.txt", repo_root=tmp_path)
        == []
    )


def test_attach_manifest_id_rejects_missing_and_unsupported_context() -> None:
    with pytest.raises(TypeError, match="requires either"):
        attach_manifest_id(object(), manifest_id=None)
    with pytest.raises(TypeError, match="must support"):
        attach_manifest_id(object(), manifest_id="manifest-1")
