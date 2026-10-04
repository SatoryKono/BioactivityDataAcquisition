"""Gold-dependent derived stages must receive materialized upstream tables."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.composition.bootstrap.runtime.runner_factory_builder_service import (
    RunnerFactoryBuilder,
)
from bioetl.composition.bootstrap.runtime.runtime_basics import build_runner_factories


@pytest.mark.parametrize("phase", ["seed", "dependency", "enricher"])
@pytest.mark.parametrize("required", [False, True])
def test_gold_write_policy_reaches_each_runner(phase, required):
    extractor = MagicMock()
    extractor.extract_enricher_filters.return_value = (None, None, None)
    extractor.resolve_dependency_filter_inputs.return_value = (None, None, None)
    options = MagicMock(side_effect=lambda **kwargs: kwargs)
    builder = RunnerFactoryBuilder(
        logger=MagicMock(),
        run_options_cls=options,
        build_context=lambda _name, value: value,
        pipeline_runner_builder=lambda value: value,
        filter_extraction_service=extractor,
        gold_required_pipelines=frozenset({"chembl_target"})
        if required
        else frozenset(),
    )
    if phase == "seed":
        runner = builder.build_seed_factory(
            seed_pipeline="chembl_target", seed_limit=1000, bronze_opts={}
        )()
    elif phase == "dependency":
        runner = builder.build_dependency_factory(dependencies=[], bronze_opts={})(
            "chembl_target", pl.DataFrame({"target_id": ["CHEMBL1"]})
        )
    else:
        runner = builder.build_enricher_factory(enrichers=[], bronze_opts={})(
            "chembl_target", pl.DataFrame({"target_id": ["CHEMBL1"]})
        )
    assert runner["skip_gold"] is not required


@pytest.mark.parametrize("derived_phase", ["dependencies", "enrichers", None])
def test_only_gold_consuming_composites_enable_upstream_gold(
    monkeypatch, derived_phase
):
    module = "bioetl.composition.bootstrap.runtime.runtime_basics"
    monkeypatch.setattr(
        f"{module}.validate_join_key_normalization_policies", lambda _: None
    )
    config = SimpleNamespace(
        seed=SimpleNamespace(pipeline="chembl_target"), dependencies=[], enrichers=[]
    )
    if derived_phase:
        getattr(config, derived_phase).append(
            SimpleNamespace(pipeline="chembl_target_protein_classification")
        )
    builder = MagicMock()
    build_runner_factories(
        config=config,
        runtime=SimpleNamespace(
            replay_of_manifest_id=None,
            seed_limit=1000,
            cached_bronze_enrichers=False,
            cached_bronze_dependencies=False,
        ),
        logger=MagicMock(),
        runner_factory_builder_cls=builder,
        filter_extraction_service_cls=MagicMock(),
        pipeline_runner_builder=MagicMock(),
        resolve_bronze_opts_fn=MagicMock(return_value={}),
    )
    expected = (
        frozenset({"chembl_target", "chembl_target_component", "chembl_protein_class"})
        if derived_phase
        else frozenset()
    )
    assert builder.call_args.kwargs["gold_required_pipelines"] == expected
