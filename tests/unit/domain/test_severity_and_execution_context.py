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


pytestmark = pytest.mark.unit

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

    def test_effective_severity__frozen_dataclass__5c0e4a68(self) -> None:
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

    def test_execution_context__from_string__49158376(self) -> None:
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

    def test_execution_context__execution_context__04fdcfb1(self) -> None:
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


# Infrastructure/application mapping checks were moved out of tests/unit/domain
# as part of P2-9 (domain purity). See:
# - tests/unit/infrastructure/schemas/test_severity_enricher_mapping.py
# - tests/unit/application/services/test_run_options_execution_context.py
