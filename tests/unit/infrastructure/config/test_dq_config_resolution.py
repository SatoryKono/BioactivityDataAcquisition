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
"""Unit tests for canonical DQ config resolution helpers."""

from __future__ import annotations

from typing import Any

import pytest

from bioetl.domain.config import DQConfig
from bioetl.infrastructure.config.dq_config_resolution import (
    build_dq_cache_key,
    merge_dq_config_hierarchy,
    run_dq_config_flow,
)


@pytest.mark.unit
def test_build_dq_cache_key_includes_relaxed_flag() -> None:
    assert build_dq_cache_key("chembl", "activity", relaxed_dq=False) == (
        "chembl:activity:relaxed=False"
    )
    assert build_dq_cache_key("chembl", "activity", relaxed_dq=True) == (
        "chembl:activity:relaxed=True"
    )


@pytest.mark.unit
def test_merge_dq_config_hierarchy_applies_relaxed_thresholds_last() -> None:
    merged = merge_dq_config_hierarchy(
        "chembl",
        "activity",
        inline_overrides=None,
        load_defaults_layer=lambda: {
            "thresholds": {"soft_fail": 0.05, "hard_fail": 0.2}
        },
        load_provider_layer=lambda _provider: {"thresholds": {"hard_fail": 0.15}},
        load_entity_layer=lambda _provider, _entity: {},
        deep_merge=lambda base, override: {
            **base,
            **override,
            "thresholds": {
                **base.get("thresholds", {}),
                **override.get("thresholds", {}),
            },
        },
        relaxed_dq=True,
    )

    assert merged["thresholds"]["soft_fail"] == pytest.approx(0.99)
    assert merged["thresholds"]["hard_fail"] == pytest.approx(1.0)


@pytest.mark.unit
def test_run_dq_config_flow_uses_injected_stages() -> None:
    captured: dict[str, Any] = {}

    def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        result = dict(base)
        result.update(override)
        return result

    def _normalize(config: dict[str, Any]) -> dict[str, Any]:
        captured["normalized_input"] = config
        return {"normalized": config}

    def _validate(config: dict[str, Any]) -> dict[str, Any]:
        captured["validated_input"] = config
        return {"validated": config}

    def _map(config: dict[str, Any]) -> DQConfig:
        captured["mapped_input"] = config
        return DQConfig()

    result = run_dq_config_flow(
        "chembl",
        "activity",
        inline_overrides={"strict_validation": True},
        load_defaults_layer=lambda: {
            "thresholds": {"soft_fail": 0.05, "hard_fail": 0.2}
        },
        load_provider_layer=lambda _provider: {},
        load_entity_layer=lambda _provider, _entity: {},
        deep_merge=_merge,
        normalize_payload=_normalize,
        validate_payload=_validate,
        map_config=_map,
        relaxed_dq=False,
    )

    assert isinstance(result, DQConfig)
    assert captured["normalized_input"]["strict_validation"] is True
    assert captured["validated_input"]["normalized"]["strict_validation"] is True
    assert "validated" in captured["mapped_input"]
