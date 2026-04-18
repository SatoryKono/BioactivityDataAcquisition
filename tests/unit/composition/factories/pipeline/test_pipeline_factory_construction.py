"""Unit tests for pipeline factory construction helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest

from bioetl.application.core.base_transformer import TransformerDependencyContext
from bioetl.composition.factories.pipeline.run_context_factory import (
    RunContextFactory,
)
from bioetl.composition.factories.pipeline.transformer_builder import (
    TransformerBuilder,
)
from bioetl.domain.config import PipelineConfig, RuntimeConfig
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.config.domain_config_resolver import (
    DomainConfigResolver,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _make_yaml_config(**overrides: object) -> PipelineYamlConfig:
    defaults = {
        "content_hash": SimpleNamespace(include=[], exclude=[]),
        "transform": SimpleNamespace(
            version="2.4.0", steps=["normalize", "validate", "hash"]
        ),
        "silver_filters": None,
        "gold_filters": None,
    }
    defaults.update(overrides)
    return cast(PipelineYamlConfig, SimpleNamespace(**defaults))


def _make_runtime(**overrides: object) -> RuntimeConfig:
    defaults = {"run_type": RunType.INCREMENTAL}
    defaults.update(overrides)
    return cast(RuntimeConfig, SimpleNamespace(**defaults))


def _make_domain_config(**overrides: object) -> PipelineConfig:
    defaults = {"silver_filters": None, "gold_filters": None}
    defaults.update(overrides)
    return cast(PipelineConfig, SimpleNamespace(**defaults))


@pytest.mark.unit
def test_run_context_factory_creates_expected_context() -> None:
    yaml_config = _make_yaml_config()
    runtime = _make_runtime(run_type=RunType.INCREMENTAL)
    factory = RunContextFactory(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type_extractor=lambda _: "activity",
        pipeline_version_getter=lambda _: "1.2.3",
        git_commit_getter=lambda: "abc1234",
        config_hash_getter=lambda _: "deadbeef",
        contract_identity_resolver=lambda *_: (
            "chembl.activity",
            "1.0.0",
            "schema-hash-123",
            "chembl.dq.v1",
            "dq-rules.v1.0",
        ),
    )

    context = factory.create(
        run_id=RunID(uuid4()),
        runtime=runtime,
        yaml_config=yaml_config,
    )

    assert context.provider == "chembl"
    assert context.entity == "activity"
    assert context.pipeline_name == "chembl_activity"
    assert context.transform_version == "2.4.0"
    assert context.transform_steps == ("normalize", "validate", "hash")
    assert context.pipeline_version == "1.2.3"
    assert context.git_commit == "abc1234"
    assert context.config_hash == "deadbeef"
    assert context.contract_ref == "chembl.activity"
    assert context.contract_version == "1.0.0"
    assert context.contract_schema_hash == "schema-hash-123"
    assert context.dq_policy_ref == "chembl.dq.v1"
    assert context.rule_bundle_version == "dq-rules.v1.0"


class _DummyLoader:
    def __init__(self, configs_root: Path, *, relaxed_dq: bool = False) -> None:
        self.configs_root = configs_root
        self.relaxed_dq = relaxed_dq

    def resolve_dq_config(self, _yaml_config: PipelineYamlConfig) -> str:
        return "resolved-dq"


@pytest.mark.unit
def test_domain_config_resolver_uses_loader_and_mapper() -> None:
    yaml_config = _make_yaml_config()
    captured: dict[str, object] = {}

    def _mapper(
        config: PipelineYamlConfig,
        resolved_dq_config: object = None,
    ) -> str:
        captured["config"] = config
        captured["resolved_dq_config"] = resolved_dq_config
        return "domain-config"

    resolver = DomainConfigResolver(
        configs_root=Path("configs"),
        loader_class=_DummyLoader,
        domain_mapper=_mapper,
    )
    result = resolver.resolve(yaml_config, relaxed_dq=True)

    assert result == "domain-config"
    assert captured["config"] is yaml_config
    assert captured["resolved_dq_config"] == "resolved-dq"


@pytest.mark.unit
def test_transformer_builder_returns_none_without_class() -> None:
    builder = TransformerBuilder(
        provider="chembl",
        pipeline_name="chembl_activity",
        entity_type_extractor=lambda _: "activity",
    )
    result = builder.build(
        transformer_class=None,
        yaml_config=_make_yaml_config(),
        domain_config=_make_domain_config(),
        pandera_silver_schema=None,
        tracer=None,
        metrics=None,
    )
    assert result is None


@pytest.mark.unit
def test_transformer_builder_builds_transformer_with_policy_fallback() -> None:
    built: dict[str, object] = {}

    class _Transformer:
        def __init__(self, **kwargs: object) -> None:
            built.update(kwargs)

    def _raise_policy_error(_provider: str, _entity: str) -> object:
        raise ValueError("missing policy")

    builder = TransformerBuilder(
        provider="chembl",
        pipeline_name="chembl_activity",
        entity_type_extractor=lambda _: "activity",
        contract_policy_loader=_raise_policy_error,
    )

    transformer = builder.build(
        transformer_class=_Transformer,
        yaml_config=_make_yaml_config(
            content_hash=SimpleNamespace(include=["a"], exclude=["b"])
        ),
        domain_config=_make_domain_config(
            silver_filters="silver-filter",
            gold_filters="gold-filter",
        ),
        pandera_silver_schema=None,
        tracer="tracer",
        metrics="metrics",
    )

    assert isinstance(transformer, _Transformer)
    assert built["provider"] == "chembl"
    assert built["entity_type"] == "activity"
    assert isinstance(built["dependencies"], TransformerDependencyContext)
    dependencies = built["dependencies"]
    assert dependencies.contract_policy is not None
    assert dependencies.structural_policy is not None
    assert built["silver_filters"] == "silver-filter"
    assert built["gold_filters"] == "gold-filter"


@pytest.mark.unit
def test_construction_module_reexports_canonical_helpers() -> None:
    from bioetl.composition.factories.pipeline import construction
    from bioetl.infrastructure.config.domain_config_resolver import (
        resolve_domain_pipeline_config,
    )

    assert construction.RunContextFactory is RunContextFactory
    assert construction.DomainConfigResolver is DomainConfigResolver
    assert construction.TransformerBuilder is TransformerBuilder
    assert construction.resolve_domain_pipeline_config is resolve_domain_pipeline_config
