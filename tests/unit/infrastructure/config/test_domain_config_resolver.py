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
"""Unit tests for canonical domain-config resolution helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

import bioetl.infrastructure.config.domain_config_resolver as resolver_module
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
    """Loader test double exposing the canonical DQ load contract only."""

    def __init__(self, configs_root: Path, *, relaxed_dq: bool = False) -> None:
        self.configs_root = configs_root
        self.relaxed_dq = relaxed_dq

    def load(
        self,
        provider: str,
        entity: str,
        inline_overrides: object = None,
    ) -> str:
        assert provider
        assert entity
        assert inline_overrides is None
        return "resolved-dq"


@pytest.mark.unit
def test_domain_config_resolver__loader_and_mapper__c9a388f6() -> None:
    yaml_config = _make_yaml_config()
    captured: dict[str, object] = {}

    def _mapper(config: object, resolved_dq_config: object = None) -> str:
        captured["config"] = config
        captured["resolved_dq_config"] = resolved_dq_config
        return "domain-config"

    resolver = DomainConfigResolver(
        configs_root=Path("configs"),
        dq_resolver_provider=_DummyLoader,
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
        dq_resolver_provider=_DummyLoader,
        domain_mapper=_mapper,
    )

    assert result == "domain-config"
    assert captured["pipeline_name"] == "chembl_activity"
    assert captured["mapped_config"] is yaml_config
    assert captured["resolved_dq_config"] == "resolved-dq"


@pytest.mark.unit
def test_load_domain_pipeline_config_honors_explicit_configs_root_for_default_yaml_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    yaml_config = _make_yaml_config()
    captured: dict[str, object] = {}

    def _load_from_root(
        pipeline_name: str,
        *,
        configs_root: Path,
    ) -> PipelineYamlConfig:
        captured["pipeline_name"] = pipeline_name
        captured["configs_root"] = configs_root
        return yaml_config

    def _mapper(config: object, resolved_dq_config: object = None) -> str:
        captured["mapped_config"] = config
        captured["resolved_dq_config"] = resolved_dq_config
        return "domain-config"

    monkeypatch.setattr(
        resolver_module,
        "load_pipeline_config_from_root",
        _load_from_root,
    )

    result = load_domain_pipeline_config(
        "chembl_activity",
        configs_root=Path("custom-configs"),
        relaxed_dq=False,
        yaml_loader=resolver_module.load_pipeline_config,
        dq_resolver_provider=_DummyLoader,
        domain_mapper=_mapper,
    )

    assert result == "domain-config"
    assert captured["pipeline_name"] == "chembl_activity"
    assert captured["configs_root"] == Path("custom-configs")
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
        dq_resolver_provider=_DummyLoader,
        domain_mapper=_mapper,
    )

    assert result == "domain-config"
    assert captured["mapped_config"] is yaml_config
    assert captured["resolved_dq_config"] == "resolved-dq"
