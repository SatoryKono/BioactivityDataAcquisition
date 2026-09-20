"""Stream B APP: leftover extractor, identity, and replay-state branches."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.helpers import (
    dependency_chained_key_resolver as chained,
)
from bioetl.application.composite.helpers import join_planner_identity as identity
from bioetl.application.core import _filtered_data_source_support as filt
from bioetl.application.pipelines.chembl import (
    target_protein_classification_summary as tpc,
)
from bioetl.application.pipelines.uniprot.extractors.genes import GeneExtractor
from bioetl.application.services.control_plane.manifest.diagnostics import (
    replay_state as replay,
)
from bioetl.application.services.run_reports import source_identity as src_id

pytestmark = pytest.mark.unit


def test_gene_extractor_skips_non_dict_nested_and_primary() -> None:
    genes = [
        {"synonyms": "not-a-list", "geneName": "x"},
        {"synonyms": [{"value": "syn"}], "geneName": {"value": "TP53"}},
        {"geneName": {"value": ""}},
    ]
    assert GeneExtractor._collect_named_values(genes, "synonyms") == ["syn"]
    assert GeneExtractor.extract_gene_names(genes) == ["TP53"]
    assert GeneExtractor.extract_primary_gene([{"geneName": "x"}]) is None


def test_join_planner_identity_fallbacks() -> None:
    assert identity.try_parse_pipeline_identity("nounderscore") is None
    assert identity.resolve_field_aliases_from_registry("nounderscore") is None
    assert identity.infer_silver_table("plain") == "silver/plain"
    assert (
        identity.infer_pipeline_from_table("silver/chembl/activity")
        == "chembl_activity"
    )
    assert identity.infer_pipeline_from_table("silver/only") is None


def test_classification_summary_empty_and_int_parsing() -> None:
    empty = pl.DataFrame({"target_id": pl.Series([], dtype=pl.Utf8)})
    summarized = tpc.summarize_target_protein_classification_dependency(empty)
    assert summarized.is_empty()
    assert (
        tpc._multifunctional_origin([{"component_id": 1}])
        == "multiple_informative_top_levels"
    )
    assert tpc._deduplicate_resolved_rows([{"leaf_id": None}]) == []
    assert tpc._int_or_none(1.5) is None
    assert tpc._int_or_none("  ") is None
    assert tpc._int_or_none("7") == 7
    assert tpc._int_or_none("nope") is None


def test_filtered_direct_multi_and_csv_column_paths() -> None:
    class _Src:
        async def __aenter__(self) -> _Src:
            return self

    state = SimpleNamespace(
        _data_source=_Src(),
        _filter_reader=object(),
        _filter_config=SimpleNamespace(
            enabled=True,
            direct_multi_filter_ids={"id": ("a",)},
            direct_valid_combinations=None,
            direct_filter_ids=None,
            source_path="x.csv",
            column_name=None,
            get_columns=lambda: ["id"],
        ),
        _metrics=None,
        _pipeline_name="p",
        _logger=MagicMock(),
        _filter_ids=None,
        _filter_result=None,
        _multi_filter_ids=None,
        _valid_combinations=None,
        _filter_fields=None,
        _fallback_mapping=None,
    )
    asyncio.run(filt.enter_filtered_data_source(state))  # type: ignore[arg-type]
    assert state._multi_filter_ids == {"id": ["a"]}

    loaded: list[str] = []

    async def _load(*_a: object, **_k: object) -> None:
        loaded.append("multi")

    state._filter_config.direct_multi_filter_ids = None
    state._filter_config.direct_filter_ids = None
    orig = filt._load_multi_column_filter
    filt._load_multi_column_filter = _load  # type: ignore[assignment]
    try:
        asyncio.run(filt.load_csv_filter_ids(state))  # type: ignore[arg-type]
    finally:
        filt._load_multi_column_filter = orig
    assert loaded == ["multi"]

    state._filter_config.get_columns = lambda: []
    with pytest.raises(ValueError, match="column_name"):
        asyncio.run(filt.load_csv_filter_ids(state))  # type: ignore[arg-type]


def test_source_identity_path_and_env_helpers(tmp_path: Path) -> None:
    assert src_id.RuntimeSourceIdentityComparisonResult(
        state=src_id.IDENTITY_STATE_ALIGNED, expected="a", actual="a"
    ).is_aligned
    assert src_id.normalize_runtime_path("", root=tmp_path) == ""
    assert src_id.runtime_path_to_local_path("", root=tmp_path) == Path(tmp_path)
    assert (
        src_id.compute_runtime_source_id(
            runtime_root=tmp_path, mounts={}, schema_version=" "
        )
        is None
    )
    assert src_id._strip_repository_env_inline_comment("v # c") == "v"
    assert src_id._parse_repository_env_line("K=v # c", {"K"}) == ("K", "v")
    env_paths = src_id._repository_env_paths(tmp_path, {"BIOETL_SKIP_ENV_LOCAL": "1"})
    assert env_paths == (tmp_path / ".env",)


def test_chained_key_filter_error_and_non_dataframe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = chained.ChainedKeyResolver.__new__(chained.ChainedKeyResolver)
    resolver._resolver_helper = SimpleNamespace(  # type: ignore[attr-defined]
        log_info=lambda *_a, **_k: None,
        log_warning=lambda *_a, **_k: None,
    )
    df = pl.DataFrame({"id": [1, 2]})
    dep = SimpleNamespace(key_filter="id = 1", pipeline="p", join_keys=("id",))
    monkeypatch.setattr(
        chained.pl,
        "sql_expr",
        lambda _sql: (_ for _ in ()).throw(ValueError("bad filter")),
    )
    kept = resolver._apply_key_filter(df, dep)  # type: ignore[arg-type]
    assert kept.equals(df)
    monkeypatch.setattr(chained.pl, "from_arrow", lambda _t: "nope")
    with pytest.raises(TypeError, match="Expected DataFrame"):
        resolver._to_source_keys(object(), "silver/p")


def test_replay_state_certified_and_incomplete_reasons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    family = SimpleNamespace(
        profile=SimpleNamespace(
            strict_exact_replay_supported=True,
            post_capture_replayable_parent_supported=False,
        )
    )
    policy = SimpleNamespace(
        snapshot_envelope=SimpleNamespace(full_snapshot_envelope=False)
    )
    monkeypatch.setattr(replay, "_collect_append_mode_semantic_sinks", lambda _m: False)
    monkeypatch.setattr(replay, "_has_partial_input_snapshot_envelope", lambda _e: True)
    monkeypatch.setattr(replay, "_is_composite_execution_context", lambda _m: False)
    monkeypatch.setattr(
        replay, "_build_replay_parentage", lambda _m: {"is_exact_replay": False}
    )
    assert (
        replay._resolve_replay_capability_reason(
            manifest=object(),  # type: ignore[arg-type]
            input_snapshots=[],
            resume_requested=False,
            policy_assessment=policy,  # type: ignore[arg-type]
            replay_family_context=family,  # type: ignore[arg-type]
        )
        == "partial_input_snapshot_envelope"
    )
    monkeypatch.setattr(
        replay, "_has_partial_input_snapshot_envelope", lambda _e: False
    )
    monkeypatch.setattr(
        replay, "_has_historical_composite_certified_snapshots", lambda _s: True
    )
    assert (
        replay._resolve_replay_occurrence_kind(
            manifest=object(),  # type: ignore[arg-type]
            input_snapshots=[{}],
            policy_assessment=policy,  # type: ignore[arg-type]
        )
        == "historical_composite_certification_incomplete"
    )
    monkeypatch.setattr(
        replay, "_has_historical_composite_certified_snapshots", lambda _s: False
    )
    monkeypatch.setattr(
        replay, "_has_historical_source_certified_snapshots", lambda _s: True
    )
    monkeypatch.setattr(
        replay, "_has_live_capture_materialized_snapshots", lambda _s: False
    )
    assert (
        replay._resolve_broader_historical_exact_replay_state(
            manifest=object(),  # type: ignore[arg-type]
            input_snapshots=[{}],
            policy_assessment=policy,  # type: ignore[arg-type]
        )
        == "historical_source_certification_incomplete"
    )
    assert (
        replay._resolve_historical_live_run_upgrade_state(
            manifest=object(),  # type: ignore[arg-type]
            input_snapshots=[{}],
            policy_assessment=policy,  # type: ignore[arg-type]
            replay_family_context=family,  # type: ignore[arg-type]
        )
        == "historical_source_certification_incomplete"
    )
