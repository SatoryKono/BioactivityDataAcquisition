"""Infrastructure schema mapping tests for severity_enricher fields."""

from __future__ import annotations


import pytest

pytestmark = pytest.mark.unit


class TestFieldValidationConfigSeverityEnricher:
    """Tests for FieldValidationConfig Pydantic schema with severity_enricher."""

    def test_severity_enricher_default_none(self) -> None:
        from bioetl.infrastructure.schemas.pipeline_config import FieldValidationConfig

        fv = FieldValidationConfig(field="test", type="required")
        assert fv.severity_enricher is None

    def test_severity_enricher_set_to_warn(self) -> None:
        from bioetl.infrastructure.schemas.pipeline_config import FieldValidationConfig

        fv = FieldValidationConfig(
            field="test", type="required", severity="error", severity_enricher="warn"
        )
        assert fv.severity == "error"
        assert fv.severity_enricher == "warn"

    def test_severity_enricher_set_to_error(self) -> None:
        from bioetl.infrastructure.schemas.pipeline_config import FieldValidationConfig

        fv = FieldValidationConfig(
            field="test", type="required", severity="warn", severity_enricher="error"
        )
        assert fv.severity == "warn"
        assert fv.severity_enricher == "error"


class TestDQConfigFileToDomainSeverityEnricher:
    """Tests for DQConfigFile.to_domain() mapping of severity_enricher."""

    def test_to_domain_preserves_severity_enricher(self) -> None:
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
