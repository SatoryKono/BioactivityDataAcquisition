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
"""Unit tests for pipeline PipelineConfigLoader DQ alias behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import bioetl.infrastructure.config.pipeline_config_loader as pipeline_config_loader_module

from bioetl.domain.config import DQConfig
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.config.pipeline_config_loader import PipelineConfigLoader
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class _DummyDQLoader:
    """Test double for DQ loader that captures inline overrides."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any] | None] = []

    def load(
        self,
        provider: str,
        entity: str,
        inline_overrides: dict[str, Any] | None = None,
    ) -> DQConfig:
        self.calls.append(inline_overrides)
        return DQConfig()


def _base_pipeline_dict() -> dict[str, Any]:
    return {
        "pipeline_name": "test_pipeline",
        "provider": "test_provider",
        "entity_type": "test_entity",
        "business_primary_keys": ["id"],
        "silver_table": "silver.test",
    }


@pytest.mark.unit
def test_resolve_dq_config_accepts_dq_overrides_key() -> None:
    """dq_overrides key should be passed as inline overrides."""
    dummy = _DummyDQLoader()
    loader = PipelineConfigLoader(Path("configs"), dq_loader=dummy)

    yaml_config = PipelineYamlConfig.model_validate(
        {
            **_base_pipeline_dict(),
            "dq_overrides": {
                "soft_fail_threshold": 0.06,
                "hard_fail_threshold": 0.19,
            },
        }
    )

    _ = loader.resolve_dq_config(yaml_config)

    assert dummy.calls
    assert dummy.calls[-1] is not None
    assert dummy.calls[-1]["thresholds"] == {"soft_fail": 0.06, "hard_fail": 0.19}


@pytest.mark.unit
def test_load_pipeline_config_uses_loader_configs_root() -> None:
    """Configured configs_root must be forwarded into the canonical YAML flow."""
    captured: dict[str, object] = {}
    loader = PipelineConfigLoader(Path("configs"), dq_loader=_DummyDQLoader())

    def _fake_load_yaml_config_uncached(
        pipeline_name: str,
        *,
        filter_loader: object | None = None,
        configs_root: Path | None = None,
    ) -> PipelineYamlConfig:
        captured["pipeline_name"] = pipeline_name
        captured["filter_loader"] = filter_loader
        captured["configs_root"] = configs_root
        return PipelineYamlConfig.model_validate(_base_pipeline_dict())

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        pipeline_config_loader_module,
        "load_yaml_config_uncached",
        _fake_load_yaml_config_uncached,
    )
    try:
        _ = loader.load_pipeline_config("chembl_activity")
    finally:
        monkeypatch.undo()

    assert captured["pipeline_name"] == "chembl_activity"
    assert captured["filter_loader"] is loader._filter_loader
    assert captured["configs_root"] == resolve_configs_root(Path("configs"))
