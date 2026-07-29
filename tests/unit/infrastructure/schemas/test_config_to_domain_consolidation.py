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
"""Tests for Pydantic schema to domain conversion contracts."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unit


class TestConsolidationPattern:
    """Tests for to_domain mapping behavior on infrastructure schemas."""

    def test_dqconfig_to_domain(self) -> None:
        from bioetl.infrastructure.schemas.pipeline_config import (
            DQYamlConfig as PydanticDQConfig,
        )

        pydantic_config = PydanticDQConfig(
            soft_fail_threshold=0.10,
            hard_fail_threshold=0.30,
            strict_validation=True,
        )
        domain_config = pydantic_config.to_domain()

        assert domain_config.soft_fail_threshold == pytest.approx(0.10)
        assert domain_config.hard_fail_threshold == pytest.approx(0.30)
        assert domain_config.strict_validation is True

    def test_circuit_breaker_to_domain(self) -> None:
        from bioetl.infrastructure.schemas.pipeline_config import (
            CircuitBreakerYamlConfig as PydanticCBConfig,
        )

        pydantic_config = PydanticCBConfig(
            failure_threshold=3,
            recovery_timeout=60,
        )
        domain_config = pydantic_config.to_domain()

        assert domain_config.failure_threshold == 3
        assert domain_config.recovery_timeout == 60

    def test_input_filter_config_to_domain_disabled(self) -> None:
        from bioetl.infrastructure.schemas.pipeline_config import (
            InputFilterYamlConfig as PydanticIFConfig,
        )

        pydantic_config = PydanticIFConfig(enabled=False)
        domain_config = pydantic_config.to_domain()

        assert domain_config.enabled is False
        assert domain_config.column_name is None
        assert domain_config.filter_field is None

    def test_input_filter_config_to_domain_enabled(self) -> None:
        from bioetl.infrastructure.schemas.pipeline_config import (
            InputFilterYamlConfig as PydanticIFConfig,
        )

        pydantic_config = PydanticIFConfig(
            enabled=True,
            source_path="/path/to/file.csv",
            column_name="chembl_id",
            filter_field="molecule_id",
            batch_size=50,
        )
        domain_config = pydantic_config.to_domain()

        assert domain_config.enabled is True
        assert domain_config.source_path == "/path/to/file.csv"
        assert domain_config.column_name == "chembl_id"
        assert domain_config.filter_field == "molecule_id"
        assert domain_config.batch_size == 50
