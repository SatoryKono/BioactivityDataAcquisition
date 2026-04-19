"""Unit tests for FilterConfigFile extraction_params support.

Tests extraction_params field, validation, and to_domain() conversion.

Requirements:
- ADR-028 §3: Extraction-Level Filtering via extraction_params
"""

from __future__ import annotations

import pytest

from bioetl.domain.filtering import SilverFilterConfig
from bioetl.domain.models.filter import ExtractionParams
from bioetl.infrastructure.schemas.filter_config import FilterConfigFile


class TestExtractionParamsDefault:
    """Tests for extraction_params default behavior."""

    def test_extraction_params_default_empty_dict(self) -> None:
        """Default extraction_params should be an empty dict."""
        config = FilterConfigFile()

        assert config.extraction_params == {}

    def test_extraction_params_parsed_from_yaml(self) -> None:
        """extraction_params should be parsed from YAML-like dict."""
        config = FilterConfigFile.model_validate(
            {
                "extraction_params": {
                    "standard_type__in": "IC50,Ki",
                    "pchembl_value__isnull": False,
                    "limit": 1000,
                },
            }
        )

        assert config.extraction_params == {
            "standard_type__in": "IC50,Ki",
            "pchembl_value__isnull": False,
            "limit": 1000,
        }


class TestExtractionParamsValidation:
    """Tests for extraction_params validation."""

    def test_extraction_params_invalid_key_empty_string(self) -> None:
        """Empty string key should raise ValidationError."""
        with pytest.raises(Exception, match="non-empty string"):
            FilterConfigFile.model_validate(
                {
                    "extraction_params": {"": "value"},
                }
            )

    def test_extraction_params_invalid_value_type_list(self) -> None:
        """List value should raise ValidationError."""
        with pytest.raises(Exception, match=r"extraction_params"):
            FilterConfigFile.model_validate(
                {
                    "extraction_params": {"key": ["a", "b"]},
                }
            )

    def test_extraction_params_invalid_value_type_dict(self) -> None:
        """Dict value should raise ValidationError."""
        with pytest.raises(Exception, match=r"extraction_params"):
            FilterConfigFile.model_validate(
                {
                    "extraction_params": {"key": {"nested": "dict"}},
                }
            )

    def test_extraction_params_valid_str_value(self) -> None:
        """String value should be accepted."""
        config = FilterConfigFile.model_validate(
            {"extraction_params": {"key": "value"}}
        )

        assert config.extraction_params["key"] == "value"

    def test_extraction_params_valid_int_value(self) -> None:
        """Integer value should be accepted."""
        config = FilterConfigFile.model_validate({"extraction_params": {"limit": 500}})

        assert config.extraction_params["limit"] == 500

    def test_extraction_params_valid_bool_value(self) -> None:
        """Boolean value should be accepted."""
        config = FilterConfigFile.model_validate(
            {"extraction_params": {"isnull": True}}
        )

        assert config.extraction_params["isnull"] is True


class TestExtractionParamsToDomain:
    """Tests for to_domain() with extraction_params."""

    def test_to_domain_returns_extraction_params(self) -> None:
        """to_domain() should return ExtractionParams as fourth element."""
        config = FilterConfigFile.model_validate(
            {
                "extraction_params": {
                    "standard_type__in": "IC50,Ki",
                    "pchembl_value__isnull": False,
                },
            }
        )

        _, _, _, extraction_params = config.to_domain()

        assert isinstance(extraction_params, ExtractionParams)
        assert extraction_params.params == {
            "standard_type__in": "IC50,Ki",
            "pchembl_value__isnull": False,
        }

    def test_to_domain_empty_extraction_params_returns_empty(self) -> None:
        """to_domain() with no extraction_params should return empty ExtractionParams."""
        config = FilterConfigFile()

        _, _, _, extraction_params = config.to_domain()

        assert isinstance(extraction_params, ExtractionParams)
        assert extraction_params.is_empty
        assert extraction_params.params == {}

    def test_to_domain_returns_silver_filter_config_type(self) -> None:
        """to_domain() should return SilverFilterConfig for silver filters."""
        config = FilterConfigFile()

        _, silver_filters, _, _ = config.to_domain()

        assert isinstance(silver_filters, SilverFilterConfig)

    def test_to_domain_returns_four_tuple(self) -> None:
        """to_domain() should return a 4-tuple."""
        config = FilterConfigFile()
        result = config.to_domain()

        assert len(result) == 4
