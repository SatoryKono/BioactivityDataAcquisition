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
"""Unit tests for config CI governance constants."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.config import config_ci_contract


pytestmark = pytest.mark.unit


def test_pipeline_contract_sets_keep_expected_governance_keys() -> None:
    """Pipeline CI contract should expose active and retired key registries."""
    assert "pipeline_name" in config_ci_contract.PIPELINE_ALLOWED_KEYS
    assert "source" in config_ci_contract.PIPELINE_ALLOWED_KEYS
    assert "schema_file" in config_ci_contract.RETIRED_PIPELINE_KEYS
    assert "data_schema_file" in config_ci_contract.RETIRED_PIPELINE_KEYS
    assert config_ci_contract.TRANSITIONAL_PIPELINE_KEYS == frozenset()
    assert "full_scan_only" in config_ci_contract.VALID_LOADING_STRATEGIES


def test_provider_and_filter_contracts_expose_required_policy_fields() -> None:
    """Provider/auth/filter governance constants should stay importable and typed."""
    assert config_ci_contract.PROVIDER_AUTH_REQUIREMENTS["openalex"] == [
        "api_key_env",
        "mailto",
    ]
    assert config_ci_contract.PROVIDER_AUTH_REQUIREMENTS["pubmed"] == [
        "api_key_env",
        "email_env",
    ]
    assert "filter_rules" in config_ci_contract.FILTER_ALLOWED_KEYS
    assert "strict_validation" in config_ci_contract.QUALITY_ALLOWED_KEYS
    assert "contracts" in config_ci_contract.ENTITY_ALLOWED_KEYS
    assert "maintenance" in config_ci_contract.COMPOSITE_ALLOWED_KEYS


def test_extraction_param_allowlist_is_narrowed_by_entity_surface() -> None:
    """Entity-scoped extraction allowlist should retain explicit chembl-only keys."""
    activity_allowlist = config_ci_contract.EXTRACTION_PARAM_ALLOWLIST[
        "chembl/activity"
    ]
    assay_allowlist = config_ci_contract.EXTRACTION_PARAM_ALLOWLIST["chembl/assay"]

    assert "standard_type__in" in activity_allowlist
    assert "standard_units" in activity_allowlist
    assert "confidence_score__gte" in assay_allowlist
    assert "target_chembl_id__isnull" in assay_allowlist
    assert (
        "tax_id__isnull"
        in config_ci_contract.EXTRACTION_PARAM_ALLOWLIST["chembl/target"]
    )


def test_module_exports_cover_public_config_ci_contract_surface() -> None:
    """The explicit export list should include all supported governance constants."""
    exported = set(config_ci_contract.__all__)

    assert "PIPELINE_ALLOWED_KEYS" in exported
    assert "PROVIDER_AUTH_REQUIREMENTS" in exported
    assert "EXTRACTION_PARAM_ALLOWLIST" in exported
    assert "REQUIRED_ENTITY_SECTIONS" in exported
    assert exported.issubset(set(dir(config_ci_contract)))
