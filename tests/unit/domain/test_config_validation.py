# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
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
