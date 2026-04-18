"""Unit tests for canonical domain-config resolution helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config.domain_config_resolver import (
    DomainConfigResolver,
    load_domain_pipeline_config,
    resolve_domain_pipeline_config,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _make_yaml_config() -> PipelineYamlConfig:
    return PipelineYamlConfig(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type="activity",
        business_primary_keys=["chembl_id"],
    )


class _DummyLoader:
    """Loader test double exposing the DQ resolver contract only."""

    def __init__(self, configs_root: Path, *, relaxed_dq: bool = False) -> None:
        self.configs_root = configs_root
        self.relaxed_dq = relaxed_dq

    def resolve_dq_config(self, _yaml_config: PipelineYamlConfig) -> str:
        return "resolved-dq"


@pytest.mark.unit
def test_domain_config_resolver_uses_loader_and_mapper() -> None:
    yaml_config = _make_yaml_config()
    captured: dict[str, object] = {}

    def _mapper(config: object, resolved_dq_config: object = None) -> str:
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
def test_load_domain_pipeline_config_uses_canonical_function_flow() -> None:
    yaml_config = _make_yaml_config()
    captured: dict[str, object] = {}

    def _yaml_loader(pipeline_name: str) -> PipelineYamlConfig:
        captured["pipeline_name"] = pipeline_name
        return yaml_config

    def _mapper(config: object, resolved_dq_config: object = None) -> str:
        captured["mapped_config"] = config
        captured["resolved_dq_config"] = resolved_dq_config
        return "domain-config"

    result = load_domain_pipeline_config(
        "chembl_activity",
        configs_root=Path("custom-configs"),
        relaxed_dq=True,
        yaml_loader=_yaml_loader,
        loader_class=_DummyLoader,
        domain_mapper=_mapper,
    )

    assert result == "domain-config"
    assert captured["pipeline_name"] == "chembl_activity"
    assert captured["mapped_config"] is yaml_config
    assert captured["resolved_dq_config"] == "resolved-dq"


@pytest.mark.unit
def test_resolve_domain_pipeline_config_uses_resolver_builder_and_mapper() -> None:
    yaml_config = _make_yaml_config()
    captured: dict[str, object] = {}

    def _mapper(config: object, resolved_dq_config: object = None) -> str:
        captured["mapped_config"] = config
        captured["resolved_dq_config"] = resolved_dq_config
        return "domain-config"

    result = resolve_domain_pipeline_config(
        yaml_config,
        configs_root=Path("custom-configs"),
        relaxed_dq=True,
        loader_class=_DummyLoader,
        domain_mapper=_mapper,
    )

    assert result == "domain-config"
    assert captured["mapped_config"] is yaml_config
    assert captured["resolved_dq_config"] == "resolved-dq"
