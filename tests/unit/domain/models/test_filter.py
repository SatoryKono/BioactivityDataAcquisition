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
"""Tests for ExtractionParams frozen dataclass.

Part of ADR-028 §3: Extraction-Level Filtering.
"""

from __future__ import annotations

import pytest

from bioetl.domain.models.filter import (
    ExtractionParams,
    SourceProfile,
    compute_extraction_params_sha256,
)


@pytest.mark.unit
class TestExtractionParams:
    """Tests for ExtractionParams value object."""

    def test_to_query_dict_returns_mutable_copy(self) -> None:
        """GIVEN ExtractionParams with params WHEN to_query_dict THEN returns mutable dict copy."""
        original = {"standard_type__in": "IC50,Ki", "standard_units": "nM"}
        ep = ExtractionParams(params=original)
        result = ep.to_query_dict()

        assert result == original
        assert isinstance(result, dict)
        # Mutating the result must not affect the original
        result["new_key"] = "new_value"
        assert "new_key" not in ep.params

    def test_to_query_string_sorted_deterministic(self) -> None:
        """GIVEN params with multiple keys WHEN to_query_string THEN keys are sorted."""
        ep = ExtractionParams(
            params={
                "z_param": "last",
                "a_param": "first",
                "m_param": "middle",
            }
        )
        result = ep.to_query_string()

        assert result == "a_param=first&m_param=middle&z_param=last"

    def test_is_empty_true_for_empty_params(self) -> None:
        """GIVEN empty params WHEN is_empty THEN returns True."""
        ep = ExtractionParams(params={})

        assert ep.is_empty is True

    def test_is_empty_false_for_non_empty(self) -> None:
        """GIVEN non-empty params WHEN is_empty THEN returns False."""
        ep = ExtractionParams(params={"key": "value"})

        assert ep.is_empty is False

    def test_empty_factory_method(self) -> None:
        """GIVEN ExtractionParams.empty() WHEN called THEN returns empty instance."""
        ep = ExtractionParams.empty()

        assert ep.is_empty is True
        assert ep.to_query_dict() == {}
        assert ep.to_query_string() == ""

    def test_extraction_params__frozen_immutability__4a0c0e3d(self) -> None:
        """GIVEN frozen ExtractionParams WHEN mutating params THEN raises error."""
        ep = ExtractionParams(params={"key": "value"})

        with pytest.raises(AttributeError):
            ep.params = {}  # type: ignore[misc]

    def test_to_query_string_with_bool_values(self) -> None:
        """GIVEN params with bool values WHEN to_query_string THEN serializes correctly."""
        ep = ExtractionParams(
            params={
                "pchembl_value__isnull": False,
                "target_organism__isnull": True,
            }
        )
        result = ep.to_query_string()

        assert result == "pchembl_value__isnull=False&target_organism__isnull=True"

    def test_to_query_dict_with_mixed_value_types(self) -> None:
        """GIVEN params with str, int, bool values WHEN to_query_dict THEN preserves types."""
        ep = ExtractionParams(
            params={
                "standard_type__in": "IC50,Ki",
                "limit": 1000,
                "pchembl_value__isnull": False,
            }
        )
        result = ep.to_query_dict()

        assert result["standard_type__in"] == "IC50,Ki"
        assert result["limit"] == 1000
        assert result["pchembl_value__isnull"] is False

    def test_to_query_string_empty(self) -> None:
        """GIVEN empty params WHEN to_query_string THEN returns empty string."""
        ep = ExtractionParams(params={})

        assert ep.to_query_string() == ""

    def test_extraction_params__equality__b95388e9(self) -> None:
        """GIVEN two ExtractionParams with same params WHEN compared THEN equal."""
        ep1 = ExtractionParams(params={"key": "value"})
        ep2 = ExtractionParams(params={"key": "value"})

        assert ep1 == ep2


@pytest.mark.unit
class TestSourceProfile:
    """Tests for source-profile extraction policy metadata."""

    def test_extraction_params_sha256_is_key_order_stable(self) -> None:
        """Equivalent extraction params must hash identically regardless of order."""
        left = {"standard_type__in": "IC50,Ki", "potential_duplicate": 0}
        right = {"potential_duplicate": 0, "standard_type__in": "IC50,Ki"}

        assert compute_extraction_params_sha256(left) == (
            compute_extraction_params_sha256(right)
        )

    def test_extraction_params_sha256_changes_when_profile_policy_changes(self) -> None:
        """Changing source-side query policy must perturb the source-profile hash."""
        baseline = {"standard_type__in": "IC50,Ki"}
        widened = {"standard_type__in": "IC50,Ki,Kd"}

        assert compute_extraction_params_sha256(baseline) != (
            compute_extraction_params_sha256(widened)
        )

    def test_source_profile_defaults_to_baseline(self) -> None:
        """SourceProfile defaults describe an unversioned no-op source policy."""
        profile = SourceProfile()

        assert profile.profile_id == "default"
        assert profile.version == "1.0.0"
        assert profile.status == "baseline"
