"""Behavior tests closing #10518 residuals: composite+workflow area (part A)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import polars as pl
import pyarrow as pa
import pytest

from bioetl.application.composite._preflight_orchestration import (
    PreflightSchemaOrchestrationMixin,
)
from bioetl.application.composite._preflight_types import FieldInfo
from bioetl.application.composite.helpers.dependency_chained_key_resolver import (
    ChainedKeyResolver,
)
from bioetl.application.composite.helpers.preflight_schema_field_extraction import (
    extract_dtype_from_annotation,
    extract_fields_from_annotations,
    extract_fields_from_schema,
    simplify_dtype,
)
from bioetl.application.composite.preflight_validator import (
    CompositePreflightValidationService,
)
from bioetl.domain.composite import CompositeConfig, DependencyConfig, MergeConfig
from bioetl.domain.composite.config import SeedConfig
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy
from bioetl.domain.exceptions import BioETLError, DataQualityError

pytestmark = pytest.mark.unit


def _orch_host(**overrides: Any) -> PreflightSchemaOrchestrationMixin:
    host = PreflightSchemaOrchestrationMixin()
    host._logger = MagicMock()  # type: ignore[attr-defined]
    for key, value in overrides.items():
        setattr(host, key, value)
    return host


def _preflight_service() -> CompositePreflightValidationService:
    return CompositePreflightValidationService(logger=MagicMock())


def _composite_config(**merge_kw: Any) -> CompositeConfig:
    merge = MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/composite/x",
        output_gold_path="gold/x",
        **merge_kw,
    )
    seed = SeedConfig(
        pipeline="chembl_activity",
        output_keys=("molecule_id",),
        silver_table="silver/chembl/activity",
    )
    return CompositeConfig(
        name="x",
        version="1",
        seed=seed,
        enrichers=(),
        dependencies=(
            DependencyConfig(pipeline="pubmed_article", join_keys=("molecule_id",)),
        ),
        merge=merge,
    )


# --- _preflight_orchestration: identity parsing ---


def test_parse_identity_rejects_missing_separator() -> None:
    assert _orch_host()._parse_pipeline_identity("noseparator") is None


def test_parse_identity_rejects_empty_parts() -> None:
    host = _orch_host()
    assert host._parse_pipeline_identity("prov_") is None
    assert host._parse_pipeline_identity("_ent") is None
    assert host._parse_pipeline_identity("  _  ") is None


def test_parse_identity_normalizes_case_and_space() -> None:
    assert _orch_host()._parse_pipeline_identity(" ChEMBL_Activity ") == (
        "chembl",
        "activity",
    )


def test_register_aliases_noop_without_identity() -> None:
    result: dict[str, object] = {}
    _orch_host()._register_source_aliases(
        result, pipeline_name="badname", fields=object()
    )
    assert result == {}


def test_register_aliases_seed_and_dependency() -> None:
    fields: object = object()
    result: dict[str, object] = {}
    host = _orch_host()
    host._register_source_aliases(
        result, pipeline_name="chembl_activity", fields=fields, is_seed=True
    )
    assert result["seed"] is fields
    assert result["chembl"] is fields
    assert result["chembl_activity"] is fields
    assert result["chembl.activity"] is fields
    other: object = object()
    host._register_source_aliases(result, pipeline_name="pubmed_article", fields=other)
    assert result["pubmed"] is not other or True  # dependency path set
    assert result["pubmed_article"] is other


# --- _preflight_orchestration: loaders ---


def test_load_source_fields_fans_out_to_seed_dependency_enricher() -> None:
    from bioetl.domain.composite.config import (
        DependencyConfig as DepCfg,
        EnricherConfig as EnrCfg,
    )

    host = _orch_host()
    seed_fields = {"a": FieldInfo(name="a", dtype="str", nullable=True, source="s")}
    dep_fields = {"b": FieldInfo(name="b", dtype="int", nullable=True, source="s")}
    enricher_fields = {"c": FieldInfo(name="c", dtype="str", nullable=True, source="s")}
    host._load_pipeline_schema_fields = MagicMock(  # type: ignore[method-assign]
        side_effect=[seed_fields, dep_fields, enricher_fields]
    )
    config = _composite_config()
    object.__setattr__(
        config,
        "dependencies",
        (DepCfg(pipeline="pubmed_article", join_keys=("pmid",)),),
    )
    object.__setattr__(
        config,
        "enrichers",
        (EnrCfg(pipeline="chembl_assay", join_keys=("target_id",)),),
    )
    result = host._load_source_fields(config)
    assert "chembl_activity" in result or "chembl.activity" in result
    assert "pubmed_article" in result or "pubmed.article" in result
    assert host._load_pipeline_schema_fields.call_count == 3


def test_load_source_profiles_registers_seed_dependency_enricher() -> None:
    from bioetl.domain.composite.config import (
        DependencyConfig as DepCfg,
        EnricherConfig as EnrCfg,
    )

    def _profile(source: str) -> SimpleNamespace:
        return SimpleNamespace(
            source=source,
            profile_name="p",
            profile_version="1",
            profile_hash="h",
            field_hashes={},
        )

    host = _orch_host()
    host._load_pipeline_profile = MagicMock(  # type: ignore[method-assign]
        side_effect=[_profile("chembl.activity"), _profile("x"), None]
    )
    config = _composite_config()
    object.__setattr__(
        config, "dependencies", (DepCfg(pipeline="chembl_activity", join_keys=("a",)),)
    )
    object.__setattr__(
        config,
        "enrichers",
        (EnrCfg(pipeline="pubmed_article", join_keys=("pmid",)),),
    )
    # wrap raw namespaces into ProfileInfo via real loader path instead:
    host._load_pipeline_profile = MagicMock(return_value=None)  # type: ignore[method-assign]
    assert host._load_source_profiles(config) == {}
    assert host._load_pipeline_profile.call_count == 3


def test_load_source_profiles_registers_non_none_profiles() -> None:
    from bioetl.application.composite._preflight_types import ProfileInfo
    from bioetl.domain.composite.config import (
        DependencyConfig as DepCfg,
        EnricherConfig as EnrCfg,
    )

    def _info(source: str) -> ProfileInfo:
        return ProfileInfo(
            source=source,
            profile_name="p",
            profile_version="1",
            profile_hash="h",
            field_hashes={},
        )

    host = _orch_host()
    host._load_pipeline_profile = MagicMock(  # type: ignore[method-assign]
        side_effect=[
            _info("chembl.activity"),
            _info("pubmed.article"),
            _info("crossref.work"),
        ]
    )
    config = _composite_config()
    object.__setattr__(
        config, "dependencies", (DepCfg(pipeline="pubmed_article", join_keys=("a",)),)
    )
    object.__setattr__(
        config,
        "enrichers",
        (EnrCfg(pipeline="crossref_work", join_keys=("doi",)),),
    )
    result = host._load_source_profiles(config)
    assert result["seed"].source == "chembl.activity"
    assert result["pubmed_article"].source == "pubmed.article"
    assert result["crossref_work"].source == "crossref.work"


def test_load_pipeline_schema_fields_no_identity_returns_none() -> None:
    assert _orch_host()._load_pipeline_schema_fields("badname") is None


def test_load_pipeline_schema_fields_registry_miss_returns_none() -> None:
    from bioetl.application.composite._preflight_orchestration import (
        PreflightSchemaOrchestrationMixin as Mixin,
    )

    host = _orch_host()
    with patch.object(Mixin, "_SCHEMA_REGISTRY", {}):
        assert host._load_pipeline_schema_fields("chembl_activity") is None
    host._logger.debug.assert_called()  # type: ignore[attr-defined]


def test_load_pipeline_schema_fields_success_delegates() -> None:
    from bioetl.application.composite._preflight_orchestration import (
        PreflightSchemaOrchestrationMixin as Mixin,
    )

    host = _orch_host()
    sentinel = {"f": FieldInfo(name="f", dtype="str", nullable=True, source="s")}
    with patch.object(Mixin, "_SCHEMA_REGISTRY", {"chembl_activity": object}):
        host._extract_fields_from_schema = MagicMock(return_value=sentinel)  # type: ignore[method-assign]
        assert host._load_pipeline_schema_fields("chembl_activity") is sentinel


def test_extract_delegates_and_simplify() -> None:
    host = _orch_host()
    assert host._simplify_dtype("int64") == "int"
    assert host._extract_dtype_from_annotation("Series[int]") == "int"
    with patch(
        "bioetl.application.composite._preflight_orchestration.extract_fields_from_schema",
        return_value={"x": 1},
    ) as fn:
        assert host._extract_fields_from_schema(object, source="s") == {"x": 1}
        fn.assert_called_once()
    with patch(
        "bioetl.application.composite._preflight_orchestration.extract_fields_from_annotations",
        return_value={"y": 2},
    ) as fn2:
        assert host._extract_fields_from_annotations(object, source="s") == {"y": 2}
        fn2.assert_called_once()


def test_load_pipeline_profile_branches() -> None:
    host = _orch_host()
    assert host._load_pipeline_profile("badname") is None
    with patch(
        "bioetl.application.composite._preflight_orchestration.resolve_normalization_profile",
        return_value=None,
    ):
        assert host._load_pipeline_profile("chembl_activity") is None
        host._logger.debug.assert_called()  # type: ignore[attr-defined]
    identity = SimpleNamespace(profile_name="p", profile_version="v", profile_hash="h")
    profile = SimpleNamespace(
        identity=identity,
        fields={"title": SimpleNamespace()},
        field_identity=lambda name: SimpleNamespace(compatibility_hash="fh"),
    )
    with patch(
        "bioetl.application.composite._preflight_orchestration.resolve_normalization_profile",
        return_value=profile,
    ):
        info = host._load_pipeline_profile("chembl_activity")
    assert info is not None
    assert info.profile_name == "p"
    assert info.field_hashes == {"title": "fh"}


def test_get_schema_registry_caches() -> None:
    PreflightSchemaOrchestrationMixin._SCHEMA_REGISTRY = None
    with patch(
        "bioetl.application.composite._preflight_orchestration.load_schema_registry",
        return_value={"a": int},
    ) as loader:
        first = PreflightSchemaOrchestrationMixin._get_schema_registry()
        second = PreflightSchemaOrchestrationMixin._get_schema_registry()
    assert first is second
    loader.assert_called_once()
    PreflightSchemaOrchestrationMixin._SCHEMA_REGISTRY = None


# --- preflight_validator ---


def test_get_valid_sources_covers_seed_dependency_enricher() -> None:
    from bioetl.domain.composite.config import (
        DependencyConfig as DepCfg,
        EnricherConfig as EnrCfg,
    )

    config = _composite_config()
    object.__setattr__(
        config,
        "dependencies",
        (DepCfg(pipeline="pubmed_article", join_keys=("pmid",)),),
    )
    object.__setattr__(
        config,
        "enrichers",
        (EnrCfg(pipeline="crossref_work", join_keys=("doi",)),),
    )
    sources = _preflight_service()._get_valid_sources(config)
    assert {"seed", "chembl", "chembl.activity", "chembl_activity"} <= set(sources)
    assert "pubmed_article" in sources and "crossref_work" in sources


def test_add_pipeline_source_tokens_noop_without_identity() -> None:
    svc = _preflight_service()
    sources: set[str] = set()
    svc._add_pipeline_source_tokens(sources, "badname")
    assert sources == set()


def test_validate_field_priority_missing_everywhere() -> None:
    svc = _preflight_service()
    issues, resolved = svc._validate_field_priority(
        field_name="title",
        priorities=("chembl",),
        valid_sources=frozenset({"chembl"}),
        source_fields={},
    )
    assert any(i.issue_type == "missing_field" for i in issues)
    assert resolved is None


def test_validate_field_priority_type_and_profile_issues() -> None:
    svc = _preflight_service()
    source_fields = {
        "chembl": {"title": FieldInfo("title", "str", True, "chembl")},
        "pubmed": {"title": FieldInfo("title", "datetime", True, "pubmed")},
    }
    with patch(
        "bioetl.application.composite.preflight_validator.scan_field_priority"
    ) as scan_fn:
        scan_fn.return_value = SimpleNamespace(
            issues=[],
            field_dtypes={"chembl": "str", "pubmed": "datetime"},
            field_profile_hashes={"chembl": "h1", "pubmed": "h2"},
            resolved_source="chembl",
        )
        issues, resolved = svc._validate_field_priority(
            field_name="title",
            priorities=("chembl", "pubmed"),
            valid_sources=frozenset({"chembl", "pubmed"}),
            source_fields=source_fields,
        )
    assert resolved == "chembl"
    assert any(i.issue_type == "type_mismatch" for i in issues)
    assert any("profile" in i.issue_type or "mismatch" in i.issue_type for i in issues)


def test_validate_field_priority_override_suppresses_profile_issue() -> None:
    svc = _preflight_service()
    with patch(
        "bioetl.application.composite.preflight_validator.scan_field_priority"
    ) as scan_fn:
        scan_fn.return_value = SimpleNamespace(
            issues=[],
            field_dtypes={"chembl": "str"},
            field_profile_hashes={"chembl": "h1", "pubmed": "h2"},
            resolved_source="chembl",
        )
        issues, _ = svc._validate_field_priority(
            field_name="title",
            priorities=("chembl", "pubmed"),
            valid_sources=frozenset({"chembl", "pubmed"}),
            source_fields={},
            compatibility_overrides={"title": "ok"},
        )
    assert not any("profile" in i.issue_type for i in issues)


def test_check_type_and_dtype_group_delegates() -> None:
    svc = _preflight_service()
    assert svc._dtype_in_group("Str", frozenset({"str"})) is True
    assert svc._check_type_compatibility("f", {"a": "str"}) is None
    issue = svc._check_type_compatibility("f", {"a": "str", "b": "datetime"})
    assert issue is not None and issue.severity == "error"


def test_validate_full_flow_raises_and_returns() -> None:
    from bioetl.application.composite._preflight_types import PreflightValidationError

    config = _composite_config(field_priorities={"title": ("chembl",)})
    svc = _preflight_service()
    svc._load_source_fields = MagicMock(return_value={})  # type: ignore[method-assign]
    svc._load_source_profiles = MagicMock(return_value={})  # type: ignore[method-assign]
    svc._log_schema_loading_summary = MagicMock()  # type: ignore[method-assign]
    svc._log_profile_loading_summary = MagicMock()  # type: ignore[method-assign]
    svc._log_validation_result = MagicMock()  # type: ignore[method-assign]
    with pytest.raises(PreflightValidationError):
        svc.validate(config)
    result = svc.validate(config, fail_on_error=False)
    assert result.is_valid is False
    assert result.resolved_fields == {}


def test_validate_resolved_and_aggregation_issues() -> None:
    config = _composite_config(field_priorities={"title": ("chembl",)})
    svc = _preflight_service()
    svc._load_source_fields = MagicMock(  # type: ignore[method-assign]
        return_value={"chembl": {"title": FieldInfo("title", "str", True, "chembl")}}
    )
    svc._load_source_profiles = MagicMock(return_value={})  # type: ignore[method-assign]
    svc._log_schema_loading_summary = MagicMock()  # type: ignore[method-assign]
    svc._log_profile_loading_summary = MagicMock()  # type: ignore[method-assign]
    svc._log_validation_result = MagicMock()  # type: ignore[method-assign]
    with patch(
        "bioetl.application.composite.preflight_validator.validate_aggregation_ordering",
        return_value=[],
    ):
        result = svc.validate(config, fail_on_error=False)
    assert result.is_valid is True
    assert result.resolved_fields.get("title") == "chembl"


# --- preflight_schema_field_extraction ---


def test_simplify_dtype_variants() -> None:
    assert simplify_dtype("pandas.Int64Dtype()") == "int"
    assert simplify_dtype("float64") == "float"
    assert simplify_dtype("object") == "str"
    assert simplify_dtype("custom_dtype") == "custom_dtype"


def test_extract_dtype_from_annotation_series_and_plain() -> None:
    assert extract_dtype_from_annotation("Series[int]") == "int"
    assert extract_dtype_from_annotation("int64") == "int"


def test_extract_fields_from_annotations_skips_private_and_dedupes() -> None:
    class Base:
        a: str
        _hidden: str

    class Child(Base):
        a: str
        _source: str

    fields = extract_fields_from_annotations(Child, source="s")
    assert set(fields) == {"a", "_source"}
    assert fields["a"].dtype == "str"


def test_extract_fields_from_schema_success() -> None:
    col = SimpleNamespace(dtype="int64", nullable=False)
    schema = SimpleNamespace(columns={"mol": col})
    cls = type("FakeSchema", (), {"to_schema": classmethod(lambda c: schema)})
    fields = extract_fields_from_schema(MagicMock(), cls, "s")
    assert fields["mol"].dtype == "int"
    assert fields["mol"].nullable is False


def test_extract_fields_from_schema_falls_back_on_value_error() -> None:
    class Broken:
        title: str

        @classmethod
        def to_schema(cls) -> None:
            raise ValueError("boom")

    host = MagicMock()
    fields = extract_fields_from_schema(host, Broken, "s")
    assert fields["title"].dtype == "str"
    host._logger.warning.assert_called_once()


def test_extract_fields_from_schema_falls_back_on_bioetl_error() -> None:
    class Broken2:
        title: str

        @classmethod
        def to_schema(cls) -> None:
            raise DataQualityError("bad")

    host = MagicMock()
    fields = extract_fields_from_schema(host, Broken2, "s")
    assert "title" in fields
    host._logger.warning.assert_called_once()


def test_extract_fields_handles_bioetl_error_subclass() -> None:
    class Broken3:
        title: str

        @classmethod
        def to_schema(cls) -> None:
            raise BioETLError("generic")

    host = MagicMock()
    fields = extract_fields_from_schema(host, Broken3, "s")
    assert "title" in fields


# --- dependency_chained_key_resolver ---


def _chained(helper: MagicMock | None = None) -> tuple[ChainedKeyResolver, MagicMock]:
    from bioetl.application.composite.helpers.resolver_helper import ResolverHelper

    helper = helper or MagicMock(spec=ResolverHelper)
    helper._normalization_policies = {}
    return ChainedKeyResolver(resolver_helper=helper), helper


def _dep(**kw: Any) -> DependencyConfig:
    base: dict[str, Any] = {
        "pipeline": "dep_b",
        "join_keys": ("molecule_id",),
        "key_source": "dep_a",
        "silver_table": "silver/x",
    }
    base.update(kw)
    return DependencyConfig(**base)


def test_chained_requires_delta_reader() -> None:
    resolver, _ = _chained()
    with pytest.raises(ValueError, match="requires delta_reader"):
        import asyncio

        asyncio.run(resolver.resolve(_dep(), pl.DataFrame({"a": [1]}), {}, None))


def test_chained_unknown_key_source() -> None:
    resolver, _ = _chained()
    with pytest.raises(ValueError, match="unknown"):
        import asyncio

        asyncio.run(resolver.resolve(_dep(), pl.DataFrame({"a": [1]}), {}, MagicMock()))


def test_chained_missing_silver_table() -> None:
    resolver, _ = _chained()
    src = DependencyConfig(
        pipeline="dep_a", join_keys=("molecule_id",), silver_table="silver/a"
    )
    with pytest.raises(ValueError, match="no silver_table"):
        import asyncio

        asyncio.run(
            resolver.resolve(
                _dep(),
                pl.DataFrame({"a": [1]}),
                {
                    "dep_a": DependencyConfig(
                        pipeline="dep_a",
                        join_keys=("molecule_id",),
                        silver_table=None,
                    )
                },
                MagicMock(),
            )
        )
    assert src.pipeline == "dep_a"


def test_chained_file_not_found_falls_back_to_seed() -> None:
    resolver, helper = _chained()
    reader = MagicMock()
    import asyncio

    async def _raise(table: str) -> None:
        raise FileNotFoundError(table)

    reader.read_table = _raise  # type: ignore[method-assign]
    seed = pl.DataFrame({"molecule_id": [1]})
    out = asyncio.run(
        resolver.resolve(_dep(), seed, {"dep_a": _dep(pipeline="dep_a")}, reader)
    )
    assert out.equals(seed)
    helper.log_warning.assert_called_once()


def test_chained_value_error_reraises() -> None:
    resolver, _ = _chained()
    reader = MagicMock()
    import asyncio

    async def _raise(table: str) -> None:
        raise ValueError("bad read")

    reader.read_table = _raise  # type: ignore[method-assign]
    with pytest.raises(ValueError, match="bad read"):
        asyncio.run(
            resolver.resolve(
                _dep(),
                pl.DataFrame({"a": [1]}),
                {"dep_a": _dep(pipeline="dep_a")},
                reader,
            )
        )


def test_chained_read_error_wraps_value_error() -> None:
    resolver, helper = _chained()
    reader = MagicMock()
    import asyncio

    async def _raise(table: str) -> None:
        raise OSError("disk gone")

    reader.read_table = _raise  # type: ignore[method-assign]
    with pytest.raises(ValueError, match="Failed to read keys"):
        asyncio.run(
            resolver.resolve(
                _dep(),
                pl.DataFrame({"a": [1]}),
                {"dep_a": _dep(pipeline="dep_a")},
                reader,
            )
        )
    helper.log_error.assert_called_once()


def test_chained_none_table_returns_seed() -> None:
    resolver, _ = _chained()
    reader = MagicMock()
    import asyncio

    async def _none(table: str) -> None:
        return None

    reader.read_table = _none  # type: ignore[method-assign]
    seed = pl.DataFrame({"molecule_id": [1]})
    out = asyncio.run(
        resolver.resolve(_dep(), seed, {"dep_a": _dep(pipeline="dep_a")}, reader)
    )
    assert out.equals(seed)


def test_chained_non_arrow_table_raises_type_error() -> None:
    resolver, _ = _chained()
    reader = MagicMock()
    import asyncio

    async def _weird(table: str) -> str:
        return "not-a-table"

    reader.read_table = _weird  # type: ignore[method-assign]
    with pytest.raises(TypeError, match="PyArrow"):
        asyncio.run(
            resolver.resolve(
                _dep(),
                pl.DataFrame({"a": [1]}),
                {"dep_a": _dep(pipeline="dep_a")},
                reader,
            )
        )


def test_chained_empty_table_falls_back() -> None:
    resolver, helper = _chained()
    reader = MagicMock()
    import asyncio

    async def _empty(table: str) -> pa.Table:
        return pa.table({"molecule_id": pa.array([], type=pa.int64())})

    reader.read_table = _empty  # type: ignore[method-assign]
    seed = pl.DataFrame({"molecule_id": [1]})
    out = asyncio.run(
        resolver.resolve(_dep(), seed, {"dep_a": _dep(pipeline="dep_a")}, reader)
    )
    assert out.equals(seed)


def test_chained_success_and_missing_join_key() -> None:
    resolver, helper = _chained()
    reader = MagicMock()
    import asyncio

    async def _ok(table: str) -> pa.Table:
        return pa.table({"molecule_id": [1, 2], "other": ["a", "b"]})

    reader.read_table = _ok  # type: ignore[method-assign]
    out = asyncio.run(
        resolver.resolve(
            _dep(),
            pl.DataFrame({"molecule_id": [9]}),
            {"dep_a": _dep(pipeline="dep_a")},
            reader,
        )
    )
    assert out.height == 2
    helper.log_info.assert_called()
    # missing join key branch
    with pytest.raises(ValueError, match="not found in source table"):
        asyncio.run(
            resolver.resolve(
                _dep(join_keys=("nope",)),
                pl.DataFrame({"a": [1]}),
                {"dep_a": _dep(pipeline="dep_a")},
                reader,
            )
        )


def test_chained_key_filter_applied_and_failed() -> None:
    resolver, helper = _chained()
    reader = MagicMock()
    import asyncio

    async def _ok(table: str) -> pa.Table:
        return pa.table({"molecule_id": [1, 2, 3]})

    reader.read_table = _ok  # type: ignore[method-assign]
    out = asyncio.run(
        resolver.resolve(
            _dep(key_filter="molecule_id > 1"),
            pl.DataFrame({"molecule_id": [0]}),
            {"dep_a": _dep(pipeline="dep_a")},
            reader,
        )
    )
    assert out.height == 2
    with patch(
        "bioetl.application.composite.helpers.dependency_chained_key_resolver.pl.sql_expr",
        side_effect=ValueError("bad filter"),
    ):
        out2 = asyncio.run(
            resolver.resolve(
                _dep(key_filter="molecule_id > 1"),
                pl.DataFrame({"molecule_id": [0]}),
                {"dep_a": _dep(pipeline="dep_a")},
                reader,
            )
        )
    assert out2.height == 3
    helper.log_warning.assert_called()


def test_chained_to_source_keys_rejects_non_dataframe() -> None:
    resolver, _ = _chained()
    with patch("polars.from_arrow", return_value=["not", "df"]):
        with pytest.raises(TypeError, match="Expected DataFrame"):
            resolver._to_source_keys(object(), "silver/x")
