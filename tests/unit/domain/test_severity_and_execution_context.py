"""Tests for FieldValidation severity_enricher and ExecutionContext.

Covers:
- FieldValidation.effective_severity() logic
- ExecutionContext enum values and is_enricher property
- FieldValidationConfig Pydantic schema with severity_enricher
- DQConfigFile.to_domain() mapping of severity_enricher
- PipelineRunContext with execution_context field
"""

from __future__ import annotations

import pytest

from bioetl.domain.config import FieldValidation
from bioetl.domain.types import ExecutionContext


class TestFieldValidationEffectiveSeverity:
    """Tests for FieldValidation.effective_severity()."""

    def test_default_severity_is_error(self) -> None:
        """FieldValidation without severity → effective_severity() = 'error'."""
        fv = FieldValidation(field="title", validation_type="required")
        assert fv.severity == "error"
        assert fv.effective_severity() == "error"

    def test_explicit_severity_warn(self) -> None:
        """FieldValidation(severity='warn') → effective_severity() = 'warn'."""
        fv = FieldValidation(field="title", validation_type="required", severity="warn")
        assert fv.effective_severity() == "warn"

    def test_severity_enricher_none_returns_base(self) -> None:
        """severity_enricher=None → effective_severity uses base severity."""
        fv = FieldValidation(
            field="title",
            validation_type="required",
            severity="error",
            severity_enricher=None,
        )
        assert fv.effective_severity(is_enricher=False) == "error"
        assert fv.effective_severity(is_enricher=True) == "error"

    def test_severity_enricher_override_when_enricher(self) -> None:
        """severity_enricher='warn' + is_enricher=True → 'warn'."""
        fv = FieldValidation(
            field="title",
            validation_type="required",
            severity="error",
            severity_enricher="warn",
        )
        assert fv.effective_severity(is_enricher=False) == "error"
        assert fv.effective_severity(is_enricher=True) == "warn"

    def test_severity_enricher_upgrade(self) -> None:
        """severity='warn', severity_enricher='error' → enricher gets 'error'."""
        fv = FieldValidation(
            field="title",
            validation_type="required",
            severity="warn",
            severity_enricher="error",
        )
        assert fv.effective_severity(is_enricher=False) == "warn"
        assert fv.effective_severity(is_enricher=True) == "error"

    def test_severity_enricher_default_is_none(self) -> None:
        """severity_enricher defaults to None."""
        fv = FieldValidation(field="x", validation_type="required")
        assert fv.severity_enricher is None

    def test_frozen_dataclass(self) -> None:
        """FieldValidation is frozen (immutable)."""
        fv = FieldValidation(field="x", validation_type="required")
        with pytest.raises(AttributeError):
            fv.severity = "warn"  # type: ignore[misc]
        with pytest.raises(AttributeError):
            fv.severity_enricher = "warn"  # type: ignore[misc]


class TestExecutionContext:
    """Tests for ExecutionContext enum."""

    def test_isolated_value(self) -> None:
        assert ExecutionContext.ISOLATED == "isolated"
        assert ExecutionContext.ISOLATED.value == "isolated"

    def test_enricher_value(self) -> None:
        assert ExecutionContext.ENRICHER == "enricher"
        assert ExecutionContext.ENRICHER.value == "enricher"

    def test_dependency_value(self) -> None:
        assert ExecutionContext.DEPENDENCY == "dependency"
        assert ExecutionContext.DEPENDENCY.value == "dependency"

    def test_is_enricher_property(self) -> None:
        assert ExecutionContext.ENRICHER.is_enricher is True
        assert ExecutionContext.ISOLATED.is_enricher is False
        assert ExecutionContext.DEPENDENCY.is_enricher is False

    def test_from_string(self) -> None:
        """ExecutionContext can be constructed from string."""
        assert ExecutionContext("isolated") == ExecutionContext.ISOLATED
        assert ExecutionContext("enricher") == ExecutionContext.ENRICHER
        assert ExecutionContext("dependency") == ExecutionContext.DEPENDENCY

    def test_invalid_value_raises(self) -> None:
        """Invalid string raises ValueError."""
        with pytest.raises(ValueError):
            ExecutionContext("unknown")


class TestFieldValidationWithExecutionContext:
    """Integration: FieldValidation.effective_severity with ExecutionContext."""

    def test_enricher_context_triggers_override(self) -> None:
        """ExecutionContext.ENRICHER.is_enricher maps to effective_severity."""
        fv = FieldValidation(
            field="title",
            validation_type="required",
            severity="error",
            severity_enricher="warn",
        )
        ctx = ExecutionContext.ENRICHER
        assert fv.effective_severity(is_enricher=ctx.is_enricher) == "warn"

    def test_isolated_context_uses_base(self) -> None:
        """ExecutionContext.ISOLATED.is_enricher=False → base severity."""
        fv = FieldValidation(
            field="title",
            validation_type="required",
            severity="error",
            severity_enricher="warn",
        )
        ctx = ExecutionContext.ISOLATED
        assert fv.effective_severity(is_enricher=ctx.is_enricher) == "error"

    def test_dependency_context_uses_base(self) -> None:
        """ExecutionContext.DEPENDENCY.is_enricher=False → base severity."""
        fv = FieldValidation(
            field="title",
            validation_type="required",
            severity="error",
            severity_enricher="warn",
        )
        ctx = ExecutionContext.DEPENDENCY
        assert fv.effective_severity(is_enricher=ctx.is_enricher) == "error"


class TestPipelineRunContextExecutionContext:
    """Tests for PipelineRunContext.execution_context field."""

    def test_default_is_isolated(self) -> None:
        """PipelineRunContext defaults to ISOLATED execution context."""
        from uuid import uuid4

        from bioetl.domain.context import PipelineRunContext
        from bioetl.domain.types import RunID, RunType

        ctx = PipelineRunContext(
            pipeline_name="test_pipeline",
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
        )
        assert ctx.execution_context == ExecutionContext.ISOLATED

    def test_enricher_execution_context(self) -> None:
        """PipelineRunContext can be created with ENRICHER context."""
        from uuid import uuid4

        from bioetl.domain.context import PipelineRunContext
        from bioetl.domain.types import RunID, RunType

        ctx = PipelineRunContext(
            pipeline_name="test_pipeline",
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            execution_context=ExecutionContext.ENRICHER,
        )
        assert ctx.execution_context == ExecutionContext.ENRICHER
        assert ctx.execution_context.is_enricher is True


class TestFieldValidationConfigSeverityEnricher:
    """Tests for FieldValidationConfig Pydantic schema with severity_enricher."""

    def test_severity_enricher_default_none(self) -> None:
        """severity_enricher defaults to None in Pydantic schema."""
        from bioetl.infrastructure.schemas.pipeline_config import FieldValidationConfig

        fv = FieldValidationConfig(field="test", type="required")
        assert fv.severity_enricher is None

    def test_severity_enricher_set_to_warn(self) -> None:
        """severity_enricher can be set to 'warn'."""
        from bioetl.infrastructure.schemas.pipeline_config import FieldValidationConfig

        fv = FieldValidationConfig(
            field="test", type="required", severity="error", severity_enricher="warn"
        )
        assert fv.severity == "error"
        assert fv.severity_enricher == "warn"

    def test_severity_enricher_set_to_error(self) -> None:
        """severity_enricher can be set to 'error'."""
        from bioetl.infrastructure.schemas.pipeline_config import FieldValidationConfig

        fv = FieldValidationConfig(
            field="test", type="required", severity="warn", severity_enricher="error"
        )
        assert fv.severity == "warn"
        assert fv.severity_enricher == "error"


class TestDQConfigFileToDomainSeverityEnricher:
    """Tests for DQConfigFile.to_domain() mapping of severity_enricher."""

    def test_to_domain_preserves_severity_enricher(self) -> None:
        """to_domain() maps severity_enricher from Pydantic to domain."""
        from bioetl.infrastructure.schemas.dq_config import DQConfigFile
        from bioetl.infrastructure.schemas.pipeline_config import FieldValidationConfig

        config = DQConfigFile(
            entity_field_validations=[
                FieldValidationConfig(
                    field="title",
                    type="required",
                    severity="error",
                    severity_enricher="warn",
                )
            ],
        )
        domain = config.to_domain()
        fv = domain.field_validations[0]
        assert fv.severity == "error"
        assert fv.severity_enricher == "warn"
        assert fv.effective_severity(is_enricher=False) == "error"
        assert fv.effective_severity(is_enricher=True) == "warn"

    def test_to_domain_severity_enricher_none_by_default(self) -> None:
        """to_domain() preserves None severity_enricher."""
        from bioetl.infrastructure.schemas.dq_config import DQConfigFile
        from bioetl.infrastructure.schemas.pipeline_config import FieldValidationConfig

        config = DQConfigFile(
            entity_field_validations=[
                FieldValidationConfig(field="title", type="required")
            ],
        )
        domain = config.to_domain()
        fv = domain.field_validations[0]
        assert fv.severity_enricher is None
        assert fv.effective_severity(is_enricher=True) == "error"

    def test_to_domain_conditional_preserves_severity_enricher(self) -> None:
        """Conditional validation nested FieldValidation gets severity_enricher."""
        from bioetl.infrastructure.schemas.dq_config import DQConfigFile
        from bioetl.infrastructure.schemas.pipeline_config import (
            ConditionalValidationConfig,
            FieldValidationConfig,
        )

        config = DQConfigFile(
            entity_conditional_validations=[
                ConditionalValidationConfig(
                    name="type_a_rule",
                    condition_field="type",
                    condition_value="A",
                    then_validations=[
                        FieldValidationConfig(
                            field="code",
                            type="required",
                            severity="error",
                            severity_enricher="warn",
                        )
                    ],
                )
            ],
        )
        domain = config.to_domain()
        cv = domain.conditional_validations[0]
        fv = cv.then_validations[0]
        assert fv.severity == "error"
        assert fv.severity_enricher == "warn"


class TestRunOptionsSeverityContext:
    """Tests for RunOptions execution_context field."""

    def test_default_execution_context(self) -> None:
        """RunOptions defaults to 'isolated' execution context."""
        from bioetl.application.services import RunOptions

        opts = RunOptions()
        assert opts.execution_context == "isolated"

    def test_enricher_execution_context(self) -> None:
        """RunOptions can be set to 'enricher' context."""
        from bioetl.application.services import RunOptions

        opts = RunOptions(execution_context="enricher")
        assert opts.execution_context == "enricher"

    def test_dependency_execution_context(self) -> None:
        """RunOptions can be set to 'dependency' context."""
        from bioetl.application.services import RunOptions

        opts = RunOptions(execution_context="dependency")
        assert opts.execution_context == "dependency"
