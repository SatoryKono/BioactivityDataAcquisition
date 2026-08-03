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
"""Unit tests for FilterConfigFile extraction_params support.

Tests extraction_params field, validation, and to_domain() conversion.

Requirements:
- ADR-028 §3: Extraction-Level Filtering via extraction_params
"""

from __future__ import annotations

import pytest

from bioetl.domain.filtering import SilverFilterConfig
from bioetl.domain.models.filter import (
    ExtractionParams,
    compute_extraction_params_sha256,
)
from bioetl.infrastructure.schemas.filter_config import FilterConfigFile


pytestmark = pytest.mark.unit


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


class TestSourceProfileMetadata:
    """Tests for source-profile metadata bound to extraction_params."""

    def test_source_profile_hash_matches_extraction_params(self) -> None:
        params = {
            "standard_type__in": "IC50,Ki",
            "potential_duplicate": 0,
        }
        config = FilterConfigFile.model_validate(
            {
                "extraction_params": params,
                "source_profile": {
                    "profile_id": "chembl.activity.curated",
                    "version": "v1.0.0",
                    "status": "baseline",
                    "extraction_params_sha256": compute_extraction_params_sha256(
                        params
                    ),
                },
            }
        )

        assert config.source_profile.profile_id == "chembl.activity.curated"
        assert config.source_profile.version == "1.0.0"

    def test_source_profile_hash_drift_is_rejected(self) -> None:
        with pytest.raises(
            Exception, match=r"source_profile\.extraction_params_sha256"
        ):
            FilterConfigFile.model_validate(
                {
                    "extraction_params": {"standard_type__in": "IC50,Ki"},
                    "source_profile": {
                        "profile_id": "chembl.activity.curated",
                        "version": "1.0.0",
                        "status": "baseline",
                        "extraction_params_sha256": "0" * 64,
                    },
                }
            )


class TestSilverFilterMigration:
    """Tests for rejected Silver semantic rules at the schema boundary."""

    @pytest.mark.parametrize("semantic_key", ["columns", "ranges", "list_contains"])
    def test_semantic_silver_rules_are_rejected(
        self,
        semantic_key: str,
    ) -> None:
        with pytest.raises(Exception, match=r"Semantic filter keys.*silver_filters"):
            FilterConfigFile.model_validate(
                {
                    "silver_filters": {
                        "required_fields": ["activity_id"],
                        semantic_key: {"standard_type": ["IC50"]},
                    },
                    "gold_filters": {
                        "columns": {"standard_units": ["nM"]},
                    },
                }
            )

    def test_empty_semantic_silver_bucket_is_rejected(self) -> None:
        with pytest.raises(Exception, match=r"silver_filters\.columns"):
            FilterConfigFile.model_validate(
                {
                    "silver_filters": {
                        "required_fields": ["activity_id"],
                        "columns": {},
                    },
                }
            )
