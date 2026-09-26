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
"""Extended unit tests for PipelineConfigLoader.

Covers uncovered paths:
- _normalize_inline_dq_overrides with field_validations
- _normalize_inline_dq_overrides with cross_field_validations
- _normalize_inline_dq_overrides with conditional_validations
- _field_validation_to_dict edge cases (with and without optional fields)
- _cross_field_validation_to_dict edge cases
- _conditional_validation_to_dict with list condition_value
- clear_cache() delegation
- resolve_dq_config() fallback to dq_overrides when FileNotFoundError
- _has_inline_dq_overrides() with default thresholds
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from bioetl.domain.config import DQConfig
import bioetl.infrastructure.config.pipeline_config_loader as pipeline_config_loader_module
from bioetl.infrastructure.config.pipeline_config_loader import PipelineConfigLoader
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------


def _base_pipeline_dict() -> dict[str, Any]:
    return {
        "pipeline_name": "test_pipeline",
        "provider": "test_provider",
        "entity_type": "test_entity",
        "business_primary_keys": ["id"],
        "silver_table": "silver.test",
    }


class _DummyDQLoader:
    """DQ loader test double that captures inline_overrides."""

    def __init__(self, raises: bool = False) -> None:
        self.calls: list[dict[str, Any] | None] = []
        self._raises = raises

    def load(
        self,
        provider: str,
        entity: str,
        inline_overrides: dict[str, Any] | None = None,
    ) -> DQConfig:
        if self._raises:
            raise FileNotFoundError("DQ hierarchy not available")
        self.calls.append(inline_overrides)
        return DQConfig()

    def clear_cache(self) -> None:
        # In-memory test double does not maintain a cache.
        return None


class _DummyFilterLoader:
    def clear_cache(self) -> None:
        # In-memory test double does not maintain a cache.
        return None


# ---------------------------------------------------------------------------
# _has_inline_dq_overrides
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHasInlineDqOverrides:
    """Tests for _has_inline_dq_overrides."""

    def test_returns_false_for_defaults(self) -> None:
        """Default DQ config has no inline overrides."""
        loader = PipelineConfigLoader(
            Path("configs"),
            dq_loader=_DummyDQLoader(),
            filter_loader=_DummyFilterLoader(),
        )
        yaml_config = PipelineYamlConfig.model_validate(_base_pipeline_dict())
        assert loader._has_inline_dq_overrides(yaml_config) is False

    def test_returns_true_for_custom_soft_fail(self) -> None:
        """Non-default soft_fail_threshold triggers inline override detection."""
        loader = PipelineConfigLoader(
            Path("configs"),
            dq_loader=_DummyDQLoader(),
            filter_loader=_DummyFilterLoader(),
        )
        yaml_config = PipelineYamlConfig.model_validate(
            {**_base_pipeline_dict(), "dq_overrides": {"soft_fail_threshold": 0.10}}
        )
        assert loader._has_inline_dq_overrides(yaml_config) is True

    def test_returns_true_for_field_validations(self) -> None:
        """Presence of field_validations triggers inline override detection."""
        loader = PipelineConfigLoader(
            Path("configs"),
            dq_loader=_DummyDQLoader(),
            filter_loader=_DummyFilterLoader(),
        )
        yaml_config = PipelineYamlConfig.model_validate(
            {
                **_base_pipeline_dict(),
                "dq_overrides": {
                    "field_validations": [{"field": "compound_id", "type": "not_null"}]
                },
            }
        )
        assert loader._has_inline_dq_overrides(yaml_config) is True


# ---------------------------------------------------------------------------
# _field_validation_to_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFieldValidationToDict:
    """Tests for PipelineConfigLoader._field_validation_to_dict()."""

    def _make_loader(self) -> PipelineConfigLoader:
        return PipelineConfigLoader(
            Path("configs"),
            dq_loader=_DummyDQLoader(),
            filter_loader=_DummyFilterLoader(),
        )

    def _make_fv(self, **kwargs: Any) -> Any:
        from bioetl.infrastructure.schemas.pipeline_config import FieldValidationConfig

        data = {"field": "compound_id", "type": "not_null", **kwargs}
        return FieldValidationConfig.model_validate(data)

    def test_minimal_required_fields(self) -> None:
        """Minimal FieldValidationConfig dict has required fields."""
        loader = self._make_loader()
        fv = self._make_fv()
        result = loader._field_validation_to_dict(fv)
        assert result["field"] == "compound_id"
        assert result["type"] == "not_null"
        assert "nullable" in result

    def test_includes_min_max_when_set(self) -> None:
        """min/max included in dict when set."""
        loader = self._make_loader()
        fv = self._make_fv(type="range", min=0.0, max=100.0)
        result = loader._field_validation_to_dict(fv)
        assert result["min"] == pytest.approx(0.0)
        assert result["max"] == pytest.approx(100.0)

    def test_excludes_min_max_when_none(self) -> None:
        """min/max excluded from dict when None."""
        loader = self._make_loader()
        fv = self._make_fv()
        result = loader._field_validation_to_dict(fv)
        assert "min" not in result
        assert "max" not in result

    def test_includes_pattern_when_set(self) -> None:
        """Pattern included when set."""
        loader = self._make_loader()
        fv = self._make_fv(type="pattern", pattern=r"^CHEMBL\d+$")
        result = loader._field_validation_to_dict(fv)
        assert result["pattern"] == r"^CHEMBL\d+$"

    def test_excludes_pattern_when_none(self) -> None:
        """Pattern excluded when None."""
        loader = self._make_loader()
        fv = self._make_fv()
        result = loader._field_validation_to_dict(fv)
        assert "pattern" not in result

    def test_includes_allowed_when_set(self) -> None:
        """Allowed values included when set."""
        loader = self._make_loader()
        fv = self._make_fv(type="enum", allowed=["A", "B", "C"])
        result = loader._field_validation_to_dict(fv)
        assert result["allowed"] == ["A", "B", "C"]

    def test_excludes_allowed_when_empty(self) -> None:
        """Empty allowed list excluded from dict."""
        loader = self._make_loader()
        fv = self._make_fv()
        result = loader._field_validation_to_dict(fv)
        assert "allowed" not in result

    def test_includes_validator_when_set(self) -> None:
        """Custom validator included when set."""
        loader = self._make_loader()
        fv = self._make_fv(type="custom", validator="my_validator")
        result = loader._field_validation_to_dict(fv)
        assert result["validator"] == "my_validator"

    def test_includes_error_message_when_set(self) -> None:
        """Error message included when set."""
        loader = self._make_loader()
        fv = self._make_fv(error_message="Value is invalid")
        result = loader._field_validation_to_dict(fv)
        assert result["error_message"] == "Value is invalid"

    def test_excludes_error_message_when_none(self) -> None:
        """Error message excluded when None."""
        loader = self._make_loader()
        fv = self._make_fv()
        result = loader._field_validation_to_dict(fv)
        assert "error_message" not in result


# ---------------------------------------------------------------------------
# _cross_field_validation_to_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCrossFieldValidationToDict:
    """Tests for _cross_field_validation_to_dict()."""

    def _make_loader(self) -> PipelineConfigLoader:
        return PipelineConfigLoader(
            Path("configs"),
            dq_loader=_DummyDQLoader(),
            filter_loader=_DummyFilterLoader(),
        )

    def _make_cfv(self, **kwargs: Any) -> Any:
        from bioetl.infrastructure.schemas.pipeline_config import (
            CrossFieldValidationConfig,
        )

        data = {
            "name": "cross_check",
            "fields": ["field_a", "field_b"],
            "condition": "all_present",
            **kwargs,
        }
        return CrossFieldValidationConfig.model_validate(data)

    def test_required_fields_in_result(self) -> None:
        """name, fields, condition always included."""
        loader = self._make_loader()
        cfv = self._make_cfv()
        result = loader._cross_field_validation_to_dict(cfv)
        assert result["name"] == "cross_check"
        assert result["fields"] == ["field_a", "field_b"]
        assert result["condition"] == "all_present"

    def test_default_severity_excluded(self) -> None:
        """severity excluded when it is the default 'error'."""
        loader = self._make_loader()
        cfv = self._make_cfv()
        result = loader._cross_field_validation_to_dict(cfv)
        assert "severity" not in result

    def test_non_default_severity_included(self) -> None:
        """Non-default severity 'warn' included in result."""
        loader = self._make_loader()
        cfv = self._make_cfv(severity="warn")
        result = loader._cross_field_validation_to_dict(cfv)
        assert result["severity"] == "warn"

    def test_trigger_field_included_when_set(self) -> None:
        """trigger_field included when set."""
        loader = self._make_loader()
        cfv = self._make_cfv(
            condition="conditional_required",
            trigger_field="source",
            required_field="target",
        )
        result = loader._cross_field_validation_to_dict(cfv)
        assert result["trigger_field"] == "source"
        assert result["required_field"] == "target"

    def test_validator_included_when_set(self) -> None:
        """Custom validator included when set."""
        loader = self._make_loader()
        cfv = self._make_cfv(condition="custom", validator="my_cross_validator")
        result = loader._cross_field_validation_to_dict(cfv)
        assert result["validator"] == "my_cross_validator"

    def test_error_message_included_when_set(self) -> None:
        """Error message included when set."""
        loader = self._make_loader()
        cfv = self._make_cfv(error_message="Cross-field error")
        result = loader._cross_field_validation_to_dict(cfv)
        assert result["error_message"] == "Cross-field error"


# ---------------------------------------------------------------------------
# _conditional_validation_to_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConditionalValidationToDict:
    """Tests for _conditional_validation_to_dict()."""

    def _make_loader(self) -> PipelineConfigLoader:
        return PipelineConfigLoader(
            Path("configs"),
            dq_loader=_DummyDQLoader(),
            filter_loader=_DummyFilterLoader(),
        )

    def _make_cv(self, **kwargs: Any) -> Any:
        from bioetl.infrastructure.schemas.pipeline_config import (
            ConditionalValidationConfig,
        )

        data = {
            "name": "cond_check",
            "condition_field": "status",
            "condition_value": "active",
            **kwargs,
        }
        return ConditionalValidationConfig.model_validate(data)

    def test_validation_to_dict__fields_in_result__564e2de2(self) -> None:
        """name, condition_field, condition_value, condition_operator always included."""
        loader = self._make_loader()
        cv = self._make_cv()
        result = loader._conditional_validation_to_dict(cv)
        assert result["name"] == "cond_check"
        assert result["condition_field"] == "status"
        assert result["condition_value"] == "active"
        assert result["condition_operator"] == "eq"

    def test_list_condition_value_converted_to_list(self) -> None:
        """List condition_value is kept as list in result."""
        loader = self._make_loader()
        cv = self._make_cv(
            condition_value=["active", "pending"], condition_operator="in"
        )
        result = loader._conditional_validation_to_dict(cv)
        assert isinstance(result["condition_value"], list)
        assert result["condition_value"] == ["active", "pending"]

    def test_string_condition_value_stays_string(self) -> None:
        """String condition_value stays as string in result."""
        loader = self._make_loader()
        cv = self._make_cv(condition_value="active")
        result = loader._conditional_validation_to_dict(cv)
        assert result["condition_value"] == "active"

    def test_then_validations_included_when_set(self) -> None:
        """then_validations included and converted when set."""
        loader = self._make_loader()
        cv = self._make_cv(
            then_validations=[{"field": "target_field", "type": "not_null"}]
        )
        result = loader._conditional_validation_to_dict(cv)
        assert "then_validations" in result
        assert len(result["then_validations"]) == 1
        assert result["then_validations"][0]["field"] == "target_field"

    def test_then_validations_excluded_when_empty(self) -> None:
        """Empty then_validations excluded from result."""
        loader = self._make_loader()
        cv = self._make_cv()
        result = loader._conditional_validation_to_dict(cv)
        assert "then_validations" not in result


# ---------------------------------------------------------------------------
# _normalize_inline_dq_overrides
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeInlineDqOverrides:
    """Tests for _normalize_inline_dq_overrides full pipeline."""

    def _make_loader(self) -> PipelineConfigLoader:
        return PipelineConfigLoader(
            Path("configs"),
            dq_loader=_DummyDQLoader(),
            filter_loader=_DummyFilterLoader(),
        )

    def test_thresholds_normalized(self) -> None:
        """Thresholds are normalized into nested dict."""
        loader = self._make_loader()
        yaml_config = PipelineYamlConfig.model_validate(
            {
                **_base_pipeline_dict(),
                "dq_overrides": {
                    "soft_fail_threshold": 0.03,
                    "hard_fail_threshold": 0.15,
                },
            }
        )
        result = loader._normalize_inline_dq_overrides(yaml_config.dq_overrides)
        assert result["thresholds"] == {"soft_fail": 0.03, "hard_fail": 0.15}

    def test_report_section_included(self) -> None:
        """Report config section is always included."""
        loader = self._make_loader()
        yaml_config = PipelineYamlConfig.model_validate(_base_pipeline_dict())
        result = loader._normalize_inline_dq_overrides(yaml_config.dq_overrides)
        assert "report" in result
        assert "enabled" in result["report"]
        assert "format" in result["report"]

    def test_field_validations_normalized(self) -> None:
        """field_validations are included when present."""
        loader = self._make_loader()
        yaml_config = PipelineYamlConfig.model_validate(
            {
                **_base_pipeline_dict(),
                "dq_overrides": {
                    "field_validations": [
                        {"field": "compound_id", "type": "not_null"},
                        {"field": "value", "type": "range", "min": 0.0, "max": 10.0},
                    ]
                },
            }
        )
        result = loader._normalize_inline_dq_overrides(yaml_config.dq_overrides)
        assert "entity_field_validations" in result
        assert len(result["entity_field_validations"]) == 2

    def test_cross_field_validations_normalized(self) -> None:
        """cross_field_validations are included when present."""
        loader = self._make_loader()
        yaml_config = PipelineYamlConfig.model_validate(
            {
                **_base_pipeline_dict(),
                "dq_overrides": {
                    "cross_field_validations": [
                        {
                            "name": "check_pair",
                            "fields": ["a", "b"],
                            "condition": "all_present",
                        }
                    ]
                },
            }
        )
        result = loader._normalize_inline_dq_overrides(yaml_config.dq_overrides)
        assert "entity_cross_field_validations" in result
        assert len(result["entity_cross_field_validations"]) == 1

    def test_conditional_validations_normalized(self) -> None:
        """conditional_validations are included when present."""
        loader = self._make_loader()
        yaml_config = PipelineYamlConfig.model_validate(
            {
                **_base_pipeline_dict(),
                "dq_overrides": {
                    "conditional_validations": [
                        {
                            "name": "if_active",
                            "condition_field": "status",
                            "condition_value": "active",
                            "then_validations": [
                                {"field": "target", "type": "not_null"}
                            ],
                        }
                    ]
                },
            }
        )
        result = loader._normalize_inline_dq_overrides(yaml_config.dq_overrides)
        assert "entity_conditional_validations" in result
        assert len(result["entity_conditional_validations"]) == 1

    def test_no_validations_excludes_lists(self) -> None:
        """When no validations, entity_*_validations keys absent."""
        loader = self._make_loader()
        yaml_config = PipelineYamlConfig.model_validate(_base_pipeline_dict())
        result = loader._normalize_inline_dq_overrides(yaml_config.dq_overrides)
        assert "entity_field_validations" not in result
        assert "entity_cross_field_validations" not in result
        assert "entity_conditional_validations" not in result


# ---------------------------------------------------------------------------
# resolve_dq_config — FileNotFoundError fallback
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolveDqConfigFallback:
    """Tests for resolve_dq_config FileNotFoundError fallback."""

    def test_falls_back_to_inline_overrides_on_file_not_found(self) -> None:
        """When DQ hierarchy raises FileNotFoundError, falls back to inline."""
        dq_loader = _DummyDQLoader(raises=True)
        loader = PipelineConfigLoader(
            Path("configs"),
            dq_loader=dq_loader,
            filter_loader=_DummyFilterLoader(),
        )
        yaml_config = PipelineYamlConfig.model_validate(_base_pipeline_dict())
        # Should not raise
        result = loader.resolve_dq_config(yaml_config)
        assert isinstance(result, DQConfig)


# ---------------------------------------------------------------------------
# clear_cache
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClearCache:
    """Tests for PipelineConfigLoader.clear_cache()."""

    def test_clear_cache_delegates_to_dq_loader(self) -> None:
        """clear_cache() calls clear_cache on dq_loader."""
        dq_loader = MagicMock()
        filter_loader = MagicMock()
        loader = PipelineConfigLoader(
            Path("configs"),
            dq_loader=dq_loader,
            filter_loader=filter_loader,
        )
        loader.clear_cache()
        dq_loader.clear_cache.assert_called_once()

    def test_clear_cache_delegates_to_filter_loader(self) -> None:
        """clear_cache() calls clear_cache on filter_loader."""
        dq_loader = MagicMock()
        filter_loader = MagicMock()
        loader = PipelineConfigLoader(
            Path("configs"),
            dq_loader=dq_loader,
            filter_loader=filter_loader,
        )
        loader.clear_cache()
        filter_loader.clear_cache.assert_called_once()


@pytest.mark.unit
def test_load_pipeline_config_forwards_injected_filter_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PipelineConfigLoader should reuse its injected filter loader."""
    dq_loader = _DummyDQLoader()
    filter_loader = MagicMock()
    expected = PipelineYamlConfig.model_validate(_base_pipeline_dict())
    captured: dict[str, object] = {}

    def _fake_load_pipeline_config_uncached(
        pipeline_name: str,
        *,
        filter_loader: object | None = None,
        configs_root: Path | None = None,
    ) -> PipelineYamlConfig:
        captured["pipeline_name"] = pipeline_name
        captured["filter_loader"] = filter_loader
        captured["configs_root"] = configs_root
        return expected

    monkeypatch.setattr(
        pipeline_config_loader_module,
        "load_yaml_config_uncached",
        _fake_load_pipeline_config_uncached,
    )

    loader = PipelineConfigLoader(
        Path("configs"),
        dq_loader=dq_loader,
        filter_loader=filter_loader,
    )

    result = loader.load_pipeline_config("test_provider_test_entity")

    assert result is expected
    assert captured["pipeline_name"] == "test_provider_test_entity"
    assert captured["filter_loader"] is filter_loader
    assert captured["configs_root"] == loader._configs_root
