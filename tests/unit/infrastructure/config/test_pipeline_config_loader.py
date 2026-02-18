"""Unit tests for pipeline ConfigLoader DQ alias behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bioetl.domain.config import DQConfig
from bioetl.infrastructure.config.pipeline_config_loader import ConfigLoader
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
        "primary_keys": ["id"],
        "silver_table": "silver.test",
        "schema_file": "../../schemas/chembl/activity.yaml",
    }


@pytest.mark.unit
def test_resolve_dq_config_accepts_dq_overrides_key() -> None:
    """dq_overrides key should be passed as inline overrides."""
    dummy = _DummyDQLoader()
    loader = ConfigLoader(Path("configs"), dq_loader=dummy)

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
