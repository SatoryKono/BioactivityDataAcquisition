"""Snapshot-like tests for RunnerFactoryBuilderService RunOptions payloads."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime.composite_filter_extraction_service import (
    CompositeFilterExtractionService,
)
from bioetl.composition.bootstrap.runtime.runner_factory_builder_service import (
    RunnerFactoryBuilderService,
    resolve_bronze_opts,
)


class _RunOptionsRecorder:
    """Callable recorder used as RunOptions constructor replacement."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(**kwargs)


def _build_context(pipeline: str, options: object) -> dict[str, object]:
    return {"pipeline": pipeline, "options": options}


def _build_runner(ctx: dict[str, object]) -> dict[str, object]:
    return ctx


def _make_runtime(**overrides: object) -> CompositeRuntimeConfig:
    defaults = {
        "use_cached_bronze": False,
        "cached_bronze_path": None,
        "cached_bronze_date": None,
        "seed_limit": None,
    }
    defaults.update(overrides)
    return cast(CompositeRuntimeConfig, SimpleNamespace(**defaults))


@pytest.mark.unit
def test_seed_runoptions_snapshot() -> None:
    recorder = _RunOptionsRecorder()
    builder = RunnerFactoryBuilderService(
        logger=MagicMock(),
        run_options_cls=recorder,
        build_context=_build_context,
        pipeline_runner_builder=_build_runner,
        filter_extraction_service=CompositeFilterExtractionService(),
    )

    runtime = _make_runtime(
        seed_limit=123,
        use_cached_bronze=True,
        cached_bronze_path="data/bronze",
        cached_bronze_date="2026-03-04",
    )
    bronze_opts = resolve_bronze_opts(runtime, phase_override=None)

    factory = builder.build_seed_factory(
        seed_pipeline="chembl_publication",
        seed_limit=runtime.seed_limit,
        bronze_opts=bronze_opts,
    )
    _ = factory()

    assert recorder.calls[-1] == {
        "run_type": "incremental",
        "limit": 123,
        "skip_gold": True,
        "use_cached_bronze": True,
        "cached_bronze_path": "data/bronze",
        "cached_bronze_date": "2026-03-04",
    }


@pytest.mark.unit
def test_enricher_runoptions_snapshot() -> None:
    recorder = _RunOptionsRecorder()
    builder = RunnerFactoryBuilderService(
        logger=MagicMock(),
        run_options_cls=recorder,
        build_context=_build_context,
        pipeline_runner_builder=_build_runner,
        filter_extraction_service=CompositeFilterExtractionService(),
    )
    bronze_opts = {
        "use_cached_bronze": True,
        "cached_bronze_path": "data/bronze",
        "cached_bronze_date": "2026-03-04",
    }

    enrichers = [
        SimpleNamespace(
            pipeline="crossref_publication",
            join_keys=("doi", "title"),
            is_many_to_one=False,
        )
    ]
    keys = pl.DataFrame({"doi": [" 10.1000/TEST "], "title": [" Test title "]})

    factory = builder.build_enricher_factory(
        enrichers=list(enrichers), bronze_opts=bronze_opts
    )
    _ = factory("crossref_publication", keys)

    assert recorder.calls[-1] == {
        "run_type": "incremental",
        "limit": 1,
        "ignore_yaml_filter": True,
        "skip_gold": True,
        "filter_ids": ("10.1000/test",),
        "filter_field": "doi",
        "fallback_mapping": {"10.1000/test": " Test title "},
        "execution_context": "enricher",
        "use_cached_bronze": True,
        "cached_bronze_path": "data/bronze",
        "cached_bronze_date": "2026-03-04",
    }


@pytest.mark.unit
def test_dependency_runoptions_snapshot_single_and_multi_filter() -> None:
    recorder = _RunOptionsRecorder()
    builder = RunnerFactoryBuilderService(
        logger=MagicMock(),
        run_options_cls=recorder,
        build_context=_build_context,
        pipeline_runner_builder=_build_runner,
        filter_extraction_service=CompositeFilterExtractionService(),
    )
    bronze_opts = {
        "use_cached_bronze": False,
        "cached_bronze_path": None,
        "cached_bronze_date": None,
    }

    single_dep = SimpleNamespace(
        pipeline="pubchem_single",
        join_keys=("compound_id",),
        is_multi_field_filter=False,
        filter_field="cid",
        key_source=None,
    )
    multi_dep = SimpleNamespace(
        pipeline="pubchem_multi",
        join_keys=("compound_id", "document_id"),
        is_multi_field_filter=True,
        effective_filter_fields=("compound_id", "document_id"),
        filter_field=None,
        key_source="pubchem_single",
    )

    factory = builder.build_dependency_factory(
        dependencies=[single_dep, multi_dep],
        bronze_opts=bronze_opts,
    )

    _ = factory("pubchem_single", pl.DataFrame({"compound_id": [123]}))
    assert recorder.calls[-1] == {
        "run_type": "incremental",
        "limit": 1,
        "filter_ids": ("123",),
        "filter_field": "cid",
        "multi_filter_ids": None,
        "ignore_yaml_filter": True,
        "skip_gold": True,
        "execution_context": "dependency",
        "use_cached_bronze": False,
        "cached_bronze_path": None,
        "cached_bronze_date": None,
    }

    _ = factory(
        "pubchem_multi",
        pl.DataFrame({"compound_id": [123], "document_id": ["DOC-1"]}),
    )
    assert recorder.calls[-1] == {
        "run_type": "incremental",
        "limit": 1,
        "filter_ids": None,
        "filter_field": None,
        "multi_filter_ids": {
            "compound_id": ("123",),
            "document_id": ("DOC-1",),
        },
        "ignore_yaml_filter": True,
        "skip_gold": True,
        "execution_context": "dependency",
        "use_cached_bronze": False,
        "cached_bronze_path": None,
        "cached_bronze_date": None,
    }
