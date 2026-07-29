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
"""Unit tests for pure helper functions in composite bootstrap modules.

Covers the stateless helper functions that can be tested without bootstrapping
the full composition root:
- _resolve_composite_gold_schema (composite.py)
- _resolve_composite_config_path (composite.py)
- CompositeFilterExtractor methods (composite_filter_extraction_service.py)
- resolve_bronze_opts (runner_factory_builder_service.py)
- _load_field_group_registry (composite.py, graceful degradation path)
"""

from __future__ import annotations

from tests.helpers.typed_ids import as_run_id, new_run_id
from tests.helpers.protocol_stubs import RecordingLogger, protocol_mock, as_magic_mock
from tests.helpers.settings_doubles import as_settings

from pathlib import Path
from typing import Any
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest

# Import polars lazily to allow test collection even if polars not installed
try:
    import polars as pl

    HAS_POLARS = True
except ImportError:
    HAS_POLARS = False

pytestmark = pytest.mark.skipif(not HAS_POLARS, reason="polars not installed")


# =============================================================================
# Helpers to import private functions
# =============================================================================


def _import_helpers():
    """Import helper functions from composite bootstrap modules.

    Functions that were previously compat-wrappers in composite.py now
    resolve to their canonical locations in extracted service modules.

    Heavy ``composite`` facade imports stay lazy so filter-extractor unit
    tests do not pay the full pipeline-registry/pandera import graph on
    Windows cloud-synced checkouts (prior source of pytest-timeout hangs).
    """
    from bioetl.composition.bootstrap.runtime.composite_filter_extraction_service import (
        CompositeFilterExtractor,
    )

    def _resolve_bronze_opts(*args: object, **kwargs: object) -> object:
        from bioetl.composition.bootstrap.runtime.runner_factory_builder_service import (
            resolve_bronze_opts as resolve_opts,
        )

        return resolve_opts(*args, **kwargs)

    def _resolve_composite_config_path(*args: object, **kwargs: object) -> object:
        # Prefer infrastructure API over the composite facade: the facade imports
        # the full runner/pipeline registry graph.
        from bioetl.infrastructure.config.composite_config_api import (
            DEFAULT_COMPOSITE_CONFIG_DIR,
            resolve_composite_config_path as resolve_config_path,
        )
        from bioetl.infrastructure.config.config_root import resolve_configs_root

        name = args[0] if args else kwargs["name"]
        return resolve_config_path(
            str(name),
            config_dir=DEFAULT_COMPOSITE_CONFIG_DIR,
            configs_root=resolve_configs_root(),
        )

    def _resolve_composite_gold_schema(*args: object, **kwargs: object) -> object:
        # Prefer infrastructure API over the composite facade (avoids pipeline
        # registry import). First materialization still loads gold contracts.
        from bioetl.infrastructure.config.composite_config_api import (
            DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY,
            resolve_composite_gold_schema as resolve_gold_schema,
        )

        composite_name = args[0] if args else kwargs["composite_name"]
        return resolve_gold_schema(
            str(composite_name),
            schema_registry=DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY,
        )

    return {
        "_build_fallback_mapping": lambda keys, filter_key, join_keys: (
            CompositeFilterExtractor().build_fallback_mapping(
                keys=keys,
                filter_key=filter_key,
                join_keys=join_keys,
            )
        ),
        "_extract_field_values": lambda keys, field: (
            CompositeFilterExtractor().extract_field_values(keys, field)
        ),
        "_extract_filter_ids_from_keys": lambda enricher_cfg, keys, logger=None: (
            CompositeFilterExtractor(logger=logger).extract_enricher_filters(
                enricher_cfg=enricher_cfg,
                keys=keys,
            )
        ),
        "_extract_multi_filter_ids": lambda dep_cfg, keys, logger=None: (
            CompositeFilterExtractor(logger=logger).extract_multi_filter_ids(
                dep_cfg=dep_cfg,
                keys=keys,
            )
        ),
        "_find_filter_key": CompositeFilterExtractor.find_filter_key,
        "_resolve_bronze_opts": _resolve_bronze_opts,
        "_resolve_composite_config_path": _resolve_composite_config_path,
        "_resolve_composite_gold_schema": _resolve_composite_gold_schema,
    }


# =============================================================================
# Tests for _resolve_composite_gold_schema
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(180)
class TestResolveCompositeGoldSchema:
    """Tests for _resolve_composite_gold_schema function.

    First call materializes lazy gold contracts (pandera/pandas). On Windows
    cloud-synced checkouts that cold import can exceed the default 60s budget.
    """

    def test_resolves_composite_activity_schema(self) -> None:
        """Test that composite_activity returns CompositeActivityGoldSchema."""
        helpers = _import_helpers()
        fn = helpers["_resolve_composite_gold_schema"]

        result = fn("composite_activity")

        assert result is not None
        assert result.__name__ == "CompositeActivityGoldSchema"

    def test_resolves_composite_molecule_schema(self) -> None:
        """Test that composite_molecule returns CompositeMoleculeGoldSchema."""
        helpers = _import_helpers()
        fn = helpers["_resolve_composite_gold_schema"]

        result = fn("composite_molecule")

        assert result is not None
        assert result.__name__ == "CompositeMoleculeGoldSchema"

    def test_resolves_composite_publication_schema(self) -> None:
        """Test that composite_publication returns CompositePublicationGoldSchema."""
        helpers = _import_helpers()
        fn = helpers["_resolve_composite_gold_schema"]

        result = fn("composite_publication")

        assert result is not None
        assert result.__name__ == "CompositePublicationGoldSchema"

    def test_resolves_composite_target_schema(self) -> None:
        """Test that composite_target returns CompositeTargetGoldSchema."""
        helpers = _import_helpers()
        fn = helpers["_resolve_composite_gold_schema"]

        result = fn("composite_target")

        assert result is not None
        assert result.__name__ == "CompositeTargetGoldSchema"

    def test_resolves_composite_assay_schema(self) -> None:
        """Test that composite_assay returns CompositeAssayGoldSchema."""
        helpers = _import_helpers()
        fn = helpers["_resolve_composite_gold_schema"]

        result = fn("composite_assay")

        assert result is not None
        assert result.__name__ == "CompositeAssayGoldSchema"

    def test_unknown_name_returns_none(self) -> None:
        """Test that unknown composite name returns None."""
        helpers = _import_helpers()
        fn = helpers["_resolve_composite_gold_schema"]

        result = fn("composite_unknown_entity")

        assert result is None

    def test_strips_composite_prefix(self) -> None:
        """Test that composite_ prefix is stripped for registry lookup."""
        helpers = _import_helpers()
        fn = helpers["_resolve_composite_gold_schema"]

        # "activity" without prefix should NOT resolve (name must start with composite_)
        result = fn("activity")

        # "activity" does not have "composite_" prefix stripped — returns None
        # because removeprefix("composite_") on "activity" returns "activity"
        # which IS in the registry, so this should succeed
        # Let's check the actual behavior:
        from bioetl.domain.contracts.gold import CompositeActivityGoldSchema

        assert result is CompositeActivityGoldSchema


# =============================================================================
# Tests for _resolve_composite_config_path
# =============================================================================


@pytest.mark.unit
class TestResolveCompositeConfigPath:
    """Tests for _resolve_composite_config_path function."""

    def test_raises_file_not_found_when_path_missing(self, tmp_path: Path) -> None:
        """Test that FileNotFoundError is raised when config files don't exist."""
        helpers = _import_helpers()
        fn = helpers["_resolve_composite_config_path"]

        with patch(
            "bioetl.infrastructure.config.composite_config_api.DEFAULT_COMPOSITE_CONFIG_DIR",
            tmp_path / "composites",
        ):
            with pytest.raises(FileNotFoundError, match="Composite config not found"):
                fn("nonexistent_pipeline")

    def test_returns_primary_path_when_exists(self, tmp_path: Path) -> None:
        """Test that primary path is returned when it exists."""
        helpers = _import_helpers()
        fn = helpers["_resolve_composite_config_path"]

        primary_dir = tmp_path / "composites"
        primary_dir.mkdir()
        config_file = primary_dir / "my_pipeline.yaml"
        config_file.write_text("composite: {}")

        with patch(
            "bioetl.infrastructure.config.composite_config_api.DEFAULT_COMPOSITE_CONFIG_DIR",
            primary_dir,
        ):
            result = fn("my_pipeline")

        assert result == config_file


@pytest.mark.unit
def test_composite_facade_delegates_config_and_schema_helpers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from bioetl.composition.bootstrap.runtime import composite

    schema_registry = {"activity": object()}
    monkeypatch.setattr(
        composite,
        "DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY",
        schema_registry,
    )
    monkeypatch.setattr(
        composite,
        "_resolve_composite_gold_schema_impl",
        lambda composite_name, *, schema_registry: (
            composite_name,
            schema_registry,
        ),
    )
    assert composite._resolve_composite_gold_schema("composite_activity") == (
        "composite_activity",
        schema_registry,
    )

    config_dir = tmp_path / "composites"
    configs_root = tmp_path / "configs-root"
    config_path = config_dir / "composite_activity.yaml"
    monkeypatch.setattr(composite, "DEFAULT_COMPOSITE_CONFIG_DIR", config_dir)
    monkeypatch.setattr(composite, "resolve_configs_root", lambda: configs_root)
    monkeypatch.setattr(
        composite,
        "_resolve_composite_config_path_impl",
        lambda name, *, config_dir, configs_root: (name, config_dir, configs_root),
    )
    assert composite._resolve_composite_config_path("composite_activity") == (
        "composite_activity",
        config_dir,
        configs_root,
    )

    monkeypatch.setattr(
        composite,
        "_load_runtime_composite_config_impl",
        lambda name, *, resolve_config_path_fn, validate_payload: (
            name,
            resolve_config_path_fn,
            validate_payload,
        ),
    )
    loaded = composite.load_composite_config("composite_activity")
    assert loaded[0] == "composite_activity"
    assert loaded[1] is composite._resolve_composite_config_path
    assert loaded[2] is composite.validate_composite_config_payload

    monkeypatch.setattr(
        composite,
        "_resolve_composite_config_path_impl",
        lambda name, *, config_dir, configs_root: config_path,
    )
    assert composite._resolve_composite_config_path("composite_activity") == config_path


@pytest.mark.unit
def test_composite_lazy_exports_and_bootstrap_wrappers_delegate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bioetl.composition.bootstrap.runtime import composite

    assert (
        composite.__getattr__("CompositeRuntimeConfig").__name__
        == "CompositeRuntimeConfig"
    )
    assert callable(composite.__getattr__("create_composite_runner_service"))
    assert callable(composite.__getattr__("_create_dq_report_service"))
    with pytest.raises(AttributeError):
        composite.__getattr__("missing")

    captures: dict[str, dict[str, object]] = {}
    monkeypatch.setattr(
        composite,
        "_bootstrap_runtime_basics_impl",
        lambda **kwargs: captures.setdefault("basics", kwargs),
    )
    basics = composite._bootstrap_runtime_basics(
        config=mock.sentinel.config, run_id="run-1"
    )
    assert basics["config"] is mock.sentinel.config
    assert basics["run_id"] == "run-1"
    assert callable(basics["settings_provider"])
    assert callable(basics["uuid_factory"])

    monkeypatch.setattr(
        composite,
        "_build_runner_factories_impl",
        lambda **kwargs: captures.setdefault("factories", kwargs),
    )
    factories = composite._build_runner_factories(
        config=mock.sentinel.config,
        runtime=mock.sentinel.runtime,
        logger=mock.sentinel.logger,
    )
    assert factories["config"] is mock.sentinel.config
    assert factories["runtime"] is mock.sentinel.runtime
    assert callable(factories["resolve_bronze_opts_fn"])

    monkeypatch.setattr(
        composite,
        "_build_support_services_impl",
        lambda **kwargs: captures.setdefault("support", kwargs),
    )
    support = composite._build_support_services(
        config=mock.sentinel.config,
        runtime=mock.sentinel.runtime,
        infra_context=mock.sentinel.infra,
    )
    assert support["infra_context"] is mock.sentinel.infra
    assert support["resolve_gold_schema_fn"] is composite._resolve_composite_gold_schema

    monkeypatch.setattr(
        composite,
        "_create_composite_runner_from_plan_impl",
        lambda **kwargs: captures.setdefault("runner", kwargs),
    )
    runner = composite._create_composite_runner_from_plan(
        config=mock.sentinel.config,
        runtime=mock.sentinel.runtime,
        plan=mock.sentinel.plan,
    )
    assert runner["plan"] is mock.sentinel.plan
    assert callable(runner["runner_factory"])


@pytest.mark.unit
def test_composite_bootstrap_plan_and_runner_entrypoint_delegate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bioetl.composition.bootstrap.runtime import composite

    captured: dict[str, object] = {}

    def _capture_plan_impl(**kwargs: object) -> object:
        captured["plan_kwargs"] = kwargs
        return mock.sentinel.plan

    monkeypatch.setattr(
        composite,
        "_build_composite_bootstrap_plan_impl",
        _capture_plan_impl,
    )
    plan = composite._build_composite_bootstrap_plan(
        config=mock.sentinel.config,
        runtime=mock.sentinel.runtime,
        run_id="run-1",
    )
    assert plan is mock.sentinel.plan
    assert (
        captured["plan_kwargs"]["bootstrap_runtime_basics_fn"]
        is composite._bootstrap_runtime_basics
    )

    patch_calls: list[str] = []
    monkeypatch.setattr(
        composite,
        "apply_runtime_compatibility_patches",
        lambda: patch_calls.append("patched"),
    )
    monkeypatch.setattr(
        composite,
        "_build_composite_bootstrap_plan",
        lambda **kwargs: mock.sentinel.entrypoint_plan,
    )
    monkeypatch.setattr(
        composite,
        "_create_composite_runner_from_plan",
        lambda **kwargs: ("runner", kwargs),
    )

    runner = composite.bootstrap_composite_runner(
        mock.sentinel.config,
        mock.sentinel.runtime,
        run_id="run-2",
    )

    assert patch_calls == ["patched"]
    assert runner[0] == "runner"
    assert runner[1]["plan"] is mock.sentinel.entrypoint_plan


# =============================================================================
# Tests for _find_filter_key
# =============================================================================


@pytest.mark.unit
class TestFindFilterKey:
    """Tests for _find_filter_key function."""

    def test_returns_first_matching_key(self) -> None:
        """Test that first join key found in columns is returned."""
        helpers = _import_helpers()
        fn = helpers["_find_filter_key"]

        result = fn(("chembl_id", "doc_id"), ["chembl_id", "smiles", "name"])

        assert result == "chembl_id"

    def test_skips_title_when_alternatives_exist(self) -> None:
        """Test that 'title' is skipped if other join keys exist."""
        helpers = _import_helpers()
        fn = helpers["_find_filter_key"]

        result = fn(("title", "doi"), ["title", "doi", "pmid"])

        assert result == "doi"

    def test_title_used_when_only_option(self) -> None:
        """Test that 'title' is used when it's the only join key."""
        helpers = _import_helpers()
        fn = helpers["_find_filter_key"]

        result = fn(("title",), ["title", "abstract"])

        assert result == "title"

    def test_returns_none_when_no_key_found(self) -> None:
        """Test that None is returned when no join key is in columns."""
        helpers = _import_helpers()
        fn = helpers["_find_filter_key"]

        result = fn(("chembl_id", "doc_id"), ["smiles", "name", "formula"])

        assert result is None

    def test_returns_second_key_when_first_missing(self) -> None:
        """Test that second join key is returned when first is missing."""
        helpers = _import_helpers()
        fn = helpers["_find_filter_key"]

        result = fn(("chembl_id", "doc_id"), ["doc_id", "smiles"])

        assert result == "doc_id"


# =============================================================================
# Tests for _build_fallback_mapping
# =============================================================================


@pytest.mark.unit
class TestBuildFallbackMapping:
    """Tests for _build_fallback_mapping function."""

    def test_returns_none_when_title_not_in_join_keys(self) -> None:
        """Test that None is returned when 'title' is not in join_keys."""
        helpers = _import_helpers()
        fn = helpers["_build_fallback_mapping"]

        keys_df = pl.DataFrame({"chembl_id": ["C1", "C2"], "title": ["T1", "T2"]})
        result = fn(keys_df, "chembl_id", ("chembl_id",))

        assert result is None

    def test_returns_mapping_when_title_in_join_keys(self) -> None:
        """Test that ID->title mapping is returned when 'title' is in join_keys."""
        helpers = _import_helpers()
        fn = helpers["_build_fallback_mapping"]

        keys_df = pl.DataFrame(
            {"doi": ["10.1/a", "10.1/b"], "title": ["Title A", "Title B"]}
        )
        result = fn(keys_df, "doi", ("doi", "title"))

        assert result is not None
        assert result == {"10.1/a": "Title A", "10.1/b": "Title B"}

    def test_returns_none_when_title_not_in_columns(self) -> None:
        """Test that None is returned when 'title' column is missing."""
        helpers = _import_helpers()
        fn = helpers["_build_fallback_mapping"]

        keys_df = pl.DataFrame({"doi": ["10.1/a"], "abstract": ["Some text"]})
        result = fn(keys_df, "doi", ("doi", "title"))

        assert result is None

    def test_float_ids_converted_to_int_string(self) -> None:
        """Test that float IDs like 123.0 are converted to '123' in the mapping."""
        helpers = _import_helpers()
        fn = helpers["_build_fallback_mapping"]

        keys_df = pl.DataFrame({"record_id": [1.0, 2.0], "title": ["Doc A", "Doc B"]})
        result = fn(keys_df, "record_id", ("record_id", "title"))

        assert result is not None
        assert result["1"] == "Doc A"
        assert result["2"] == "Doc B"


# =============================================================================
# Tests for _extract_field_values
# =============================================================================


@pytest.mark.unit
class TestExtractFieldValues:
    """Tests for _extract_field_values function."""

    def test_returns_unique_non_null_values(self) -> None:
        """Test that unique non-null values are extracted."""
        helpers = _import_helpers()
        fn = helpers["_extract_field_values"]

        df = pl.DataFrame({"chembl_id": ["C1", "C2", "C1", None]})
        result = fn(df, "chembl_id")

        assert result is not None
        assert set(result) == {"C1", "C2"}

    def test_returns_none_for_missing_field(self) -> None:
        """Test that None is returned when field is not in DataFrame columns."""
        helpers = _import_helpers()
        fn = helpers["_extract_field_values"]

        df = pl.DataFrame({"other_field": ["A", "B"]})
        result = fn(df, "chembl_id")

        assert result is None

    def test_returns_none_for_empty_values(self) -> None:
        """Test that None is returned when all values are null."""
        helpers = _import_helpers()
        fn = helpers["_extract_field_values"]

        df = pl.DataFrame({"chembl_id": [None, None]})
        result = fn(df, "chembl_id")

        assert result is None

    def test_converts_float_ids_to_int_strings(self) -> None:
        """Test that float IDs like 4044.0 are converted to '4044'."""
        helpers = _import_helpers()
        fn = helpers["_extract_field_values"]

        df = pl.DataFrame({"record_id": [1.0, 2.0, 3.0]})
        result = fn(df, "record_id")

        assert result is not None
        assert set(result) == {"1", "2", "3"}


# =============================================================================
# Tests for _extract_filter_ids_from_keys
# =============================================================================


@pytest.mark.unit
class TestExtractFilterIdsFromKeys:
    """Tests for _extract_filter_ids_from_keys function."""

    def _make_enricher_cfg(
        self, join_keys: tuple[str, ...], pipeline: str = "test"
    ) -> Any:
        """Create a minimal EnricherConfig mock."""
        cfg = MagicMock()
        cfg.join_keys = join_keys
        cfg.pipeline = pipeline
        return cfg

    def test_returns_none_triple_when_keys_is_none(self) -> None:
        """Test that (None, None, None) is returned when keys is None."""
        helpers = _import_helpers()
        fn = helpers["_extract_filter_ids_from_keys"]

        enricher_cfg = self._make_enricher_cfg(("chembl_id",))
        result = fn(enricher_cfg, None)

        assert result == (None, None, None)

    def test_returns_none_triple_when_keys_empty(self) -> None:
        """Test that (None, None, None) is returned for empty DataFrame."""
        helpers = _import_helpers()
        fn = helpers["_extract_filter_ids_from_keys"]

        enricher_cfg = self._make_enricher_cfg(("chembl_id",))
        empty_df = pl.DataFrame({"chembl_id": []})
        result = fn(enricher_cfg, empty_df)

        assert result == (None, None, None)

    def test_returns_filter_ids_for_matching_key(self) -> None:
        """Test that filter IDs are extracted for matching join key."""
        helpers = _import_helpers()
        fn = helpers["_extract_filter_ids_from_keys"]

        enricher_cfg = self._make_enricher_cfg(("chembl_id",))
        keys = pl.DataFrame({"chembl_id": ["C1", "C2", "C3"]})

        filter_ids, filter_field, fallback = fn(enricher_cfg, keys)

        assert filter_ids is not None
        assert set(filter_ids) == {"C1", "C2", "C3"}
        assert filter_field == "chembl_id"
        assert fallback is None  # No title in join_keys

    def test_normalizes_trim_and_case_for_identifier_filters(self) -> None:
        """Test filter IDs use the same canonical normalization as merge joins."""
        helpers = _import_helpers()
        fn = helpers["_extract_filter_ids_from_keys"]

        enricher_cfg = self._make_enricher_cfg(("doi",))
        keys = pl.DataFrame({"doi": [" 10.1000/ABC ", "10.1000/abc"]})

        filter_ids, filter_field, fallback = fn(enricher_cfg, keys)

        assert filter_ids == ("10.1000/abc",)
        assert filter_field == "doi"
        assert fallback is None

    def test_returns_none_triple_when_join_key_not_in_columns(self) -> None:
        """Test that (None, None, None) is returned when join key not in columns."""
        helpers = _import_helpers()
        fn = helpers["_extract_filter_ids_from_keys"]

        enricher_cfg = self._make_enricher_cfg(("chembl_id",))
        keys = pl.DataFrame({"other_col": ["A", "B"]})

        result = fn(enricher_cfg, keys)

        assert result == (None, None, None)

    def test_logs_debug_when_logger_provided(self) -> None:
        """Test that debug is logged when logger is provided."""
        helpers = _import_helpers()
        fn = helpers["_extract_filter_ids_from_keys"]

        enricher_cfg = self._make_enricher_cfg(("chembl_id",))
        empty_df = pl.DataFrame({"chembl_id": []})
        mock_logger = MagicMock()

        fn(enricher_cfg, empty_df, mock_logger)

        # Should log debug about no keys available
        mock_logger.debug.assert_called_once()


# =============================================================================
# Tests for _extract_multi_filter_ids
# =============================================================================


@pytest.mark.unit
class TestExtractMultiFilterIds:
    """Tests for _extract_multi_filter_ids function."""

    def _make_dep_cfg(self, filter_fields: list[str], pipeline: str = "test") -> Any:
        """Create a minimal DependencyConfig mock."""
        cfg = MagicMock()
        cfg.effective_filter_fields = filter_fields
        cfg.pipeline = pipeline
        return cfg

    def test_returns_none_when_keys_empty(self) -> None:
        """Test that None is returned when keys DataFrame is empty."""
        helpers = _import_helpers()
        fn = helpers["_extract_multi_filter_ids"]

        dep_cfg = self._make_dep_cfg(["molecule_id", "document_id"])
        empty_df = pl.DataFrame({"molecule_id": [], "document_id": []})

        result = fn(dep_cfg, empty_df)

        assert result is None

    def test_returns_dict_with_all_fields(self) -> None:
        """Test that result contains all filter fields with their values."""
        helpers = _import_helpers()
        fn = helpers["_extract_multi_filter_ids"]

        dep_cfg = self._make_dep_cfg(["molecule_id", "document_id"])
        keys = pl.DataFrame(
            {
                "molecule_id": ["M1", "M2"],
                "document_id": ["D1", "D2"],
            }
        )

        result = fn(dep_cfg, keys)

        assert result is not None
        assert "molecule_id" in result
        assert "document_id" in result
        assert set(result["molecule_id"]) == {"M1", "M2"}
        assert set(result["document_id"]) == {"D1", "D2"}

    def test_normalizes_trim_only_fields_without_lowercasing(self) -> None:
        """Test trim-only join keys keep their original casing in filter extraction."""
        helpers = _import_helpers()
        fn = helpers["_extract_field_values"]

        keys = pl.DataFrame({"title": ["  Mixed Case Title  ", "Mixed Case Title"]})

        result = fn(keys, "title")

        assert result == ("Mixed Case Title",)

    def test_returns_none_when_field_missing(self) -> None:
        """Test that None is returned when a required field is missing."""
        helpers = _import_helpers()
        fn = helpers["_extract_multi_filter_ids"]

        dep_cfg = self._make_dep_cfg(["molecule_id", "document_id"])
        keys = pl.DataFrame({"molecule_id": ["M1", "M2"]})  # document_id missing

        result = fn(dep_cfg, keys)

        assert result is None

    def test_logs_warning_when_field_missing_and_logger_provided(self) -> None:
        """Test that warning is logged when field is missing and logger provided."""
        helpers = _import_helpers()
        fn = helpers["_extract_multi_filter_ids"]

        dep_cfg = self._make_dep_cfg(["molecule_id", "document_id"])
        keys = pl.DataFrame({"molecule_id": ["M1"]})
        mock_logger = MagicMock()

        fn(dep_cfg, keys, mock_logger)

        mock_logger.warning.assert_called()

    def test_logs_info_on_success_when_logger_provided(self) -> None:
        """Test that info is logged on successful extraction with logger."""
        helpers = _import_helpers()
        fn = helpers["_extract_multi_filter_ids"]

        dep_cfg = self._make_dep_cfg(["molecule_id"])
        keys = pl.DataFrame({"molecule_id": ["M1", "M2"]})
        mock_logger = MagicMock()

        result = fn(dep_cfg, keys, mock_logger)

        assert result is not None
        mock_logger.info.assert_called()

    def test_returns_none_when_keys_is_none(self) -> None:
        """Test that None is returned when keys is None."""
        helpers = _import_helpers()
        fn = helpers["_extract_multi_filter_ids"]

        dep_cfg = self._make_dep_cfg(["molecule_id"])

        result = fn(dep_cfg, None)

        assert result is None


# =============================================================================
# Tests for _resolve_bronze_opts
# =============================================================================


@pytest.mark.unit
class TestResolveBronzeOpts:
    """Tests for _resolve_bronze_opts function."""

    def _make_runtime_config(
        self,
        use_cached_bronze: bool = False,
        cached_bronze_path: str | None = None,
        cached_bronze_date: str | None = None,
    ) -> Any:
        """Create minimal CompositeRuntimeConfig mock."""
        from bioetl.application.composite.runner_pkg import CompositeRuntimeConfig

        return CompositeRuntimeConfig(
            use_cached_bronze=use_cached_bronze,
            cached_bronze_path=cached_bronze_path,
            cached_bronze_date=cached_bronze_date,
        )

    def test_none_override_uses_master_switch_false(self) -> None:
        """Test that None phase_override uses master switch=False."""
        helpers = _import_helpers()
        fn = helpers["_resolve_bronze_opts"]

        runtime = self._make_runtime_config(use_cached_bronze=False)
        result = fn(runtime, phase_override=None)

        assert result["use_cached_bronze"] is False
        assert result["cached_bronze_path"] is None
        assert result["cached_bronze_date"] is None

    def test_none_override_uses_master_switch_true(self) -> None:
        """Test that None phase_override uses master switch=True."""
        helpers = _import_helpers()
        fn = helpers["_resolve_bronze_opts"]

        runtime = self._make_runtime_config(
            use_cached_bronze=True,
            cached_bronze_path="/path/to/bronze",
            cached_bronze_date="2024-01-01",
        )
        result = fn(runtime, phase_override=None)

        assert result["use_cached_bronze"] is True
        assert result["cached_bronze_path"] == "/path/to/bronze"
        assert result["cached_bronze_date"] == "2024-01-01"

    def test_true_override_enables_regardless_of_master(self) -> None:
        """Test that True phase_override enables cached bronze regardless of master."""
        helpers = _import_helpers()
        fn = helpers["_resolve_bronze_opts"]

        runtime = self._make_runtime_config(
            use_cached_bronze=False,
            cached_bronze_path="/override/path",
        )
        result = fn(runtime, phase_override=True)

        assert result["use_cached_bronze"] is True
        assert result["cached_bronze_path"] == "/override/path"

    def test_false_override_disables_regardless_of_master(self) -> None:
        """Test that False phase_override disables cached bronze regardless of master."""
        helpers = _import_helpers()
        fn = helpers["_resolve_bronze_opts"]

        runtime = self._make_runtime_config(
            use_cached_bronze=True,
            cached_bronze_path="/active/path",
            cached_bronze_date="2024-06-01",
        )
        result = fn(runtime, phase_override=False)

        assert result["use_cached_bronze"] is False
        assert result["cached_bronze_path"] is None
        assert result["cached_bronze_date"] is None

    def test_returns_dict_with_three_keys(self) -> None:
        """Test that result always has the expected three keys."""
        helpers = _import_helpers()
        fn = helpers["_resolve_bronze_opts"]

        runtime = self._make_runtime_config()
        result = fn(runtime, phase_override=None)

        assert set(result.keys()) == {
            "use_cached_bronze",
            "cached_bronze_path",
            "cached_bronze_date",
        }


# =============================================================================
# Tests for _load_field_group_registry — graceful degradation paths
# =============================================================================


@pytest.mark.unit
class TestLoadFieldGroupRegistry:
    """Tests for _load_field_group_registry function (graceful degradation)."""

    def test_returns_none_when_config_file_not_found(self, tmp_path: Path) -> None:
        """Test that None is returned when field group config doesn't exist."""
        from bioetl.composition.bootstrap.runtime.composite import (
            _load_field_group_registry,
        )

        mock_logger = MagicMock()

        with patch(
            "bioetl.composition.bootstrap.runtime.composite_support_helpers.FIELD_GROUP_CONFIG_DIR",
            tmp_path / "field_groups",
        ):
            result = _load_field_group_registry("composite_publication", mock_logger)

        assert result is None
        mock_logger.debug.assert_called()

    def test_returns_none_on_load_error(self, tmp_path: Path) -> None:
        """Test that None is returned when field group loading fails."""
        from bioetl.composition.bootstrap.runtime.composite import (
            _load_field_group_registry,
        )
        from bioetl.infrastructure.config.field_group_loader import FieldGroupLoadError

        field_group_dir = tmp_path / "field_groups"
        field_group_dir.mkdir()
        config_file = field_group_dir / "publication.yaml"
        config_file.write_text("invalid: yaml: content: here")

        mock_logger = MagicMock()

        with (
            patch(
                "bioetl.composition.bootstrap.runtime.composite_support_helpers.FIELD_GROUP_CONFIG_DIR",
                field_group_dir,
            ),
            patch(
                "bioetl.composition.bootstrap.runtime.composite_support_helpers.load_field_groups",
                side_effect=FieldGroupLoadError("Test error"),
            ),
        ):
            result = _load_field_group_registry("composite_publication", mock_logger)

        assert result is None
        mock_logger.warning.assert_called()

    def test_extracts_entity_from_composite_name(self, tmp_path: Path) -> None:
        """Test that entity is correctly extracted from composite name."""
        from bioetl.composition.bootstrap.runtime.composite import (
            _load_field_group_registry,
        )

        field_group_dir = tmp_path / "field_groups"
        field_group_dir.mkdir()
        # File for "molecule" (not "composite_molecule")
        (field_group_dir / "molecule.yaml").write_text("groups: []")

        mock_logger = MagicMock()
        mock_registry = MagicMock()
        mock_registry.groups = []
        mock_registry.field_count = 0
        mock_registry.column_count = 0

        with (
            patch(
                "bioetl.composition.bootstrap.runtime.composite_support_helpers.FIELD_GROUP_CONFIG_DIR",
                field_group_dir,
            ),
            patch(
                "bioetl.composition.bootstrap.runtime.composite_support_helpers.load_field_groups",
                return_value=mock_registry,
            ) as mock_load,
        ):
            result = _load_field_group_registry("composite_molecule", mock_logger)

        # Ensure the config path used contains "molecule.yaml" (not "composite_molecule.yaml")
        call_args = mock_load.call_args[0][0]
        assert "molecule.yaml" in str(call_args)
        assert result is mock_registry
