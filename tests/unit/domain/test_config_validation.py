from __future__ import annotations

import pytest

from bioetl.domain.config import DQConfig, PipelineConfig, TableConfig


pytestmark = pytest.mark.unit

def test_dq_config_rejects_soft_over_hard() -> None:
    with pytest.raises(ValueError, match="soft_fail_threshold must be strictly less"):
        DQConfig(soft_fail_threshold=0.2, hard_fail_threshold=0.2)


def test_dq_config_rejects_out_of_bounds() -> None:
    with pytest.raises(ValueError, match="soft_fail_threshold must be between"):
        DQConfig(soft_fail_threshold=-0.1, hard_fail_threshold=0.2)


def test_pipeline_config_propagates_dq_validation() -> None:
    with pytest.raises(ValueError, match="hard_fail_threshold must be between"):
        PipelineConfig(
            pipeline_name="test_pipeline",
            provider="chembl",
            entity_type="activity",
            table=TableConfig(
                primary_keys=["id"],
                silver_table="silver.table",
            ),
            dq=DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=1.5),
        )
