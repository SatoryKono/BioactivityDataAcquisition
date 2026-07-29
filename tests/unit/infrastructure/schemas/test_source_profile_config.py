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
"""Tests for source-profile YAML config schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bioetl.domain.models.filter import compute_extraction_params_sha256
from bioetl.infrastructure.schemas.source_profile_config import (
    SourceProfileYamlConfig,
)

pytestmark = pytest.mark.unit


def test_source_profile_config_normalizes_and_converts_to_domain() -> None:
    params = {"standard_units": "nM", "limit": 10, "include_inactive": False}
    digest = compute_extraction_params_sha256(params)

    config = SourceProfileYamlConfig(
        profile_id=" ChEMBL.Activity-Baseline ",
        version="v1.2.3",
        status="candidate",
        extraction_params_sha256=f"sha256:{digest}",
        description="Activity extraction baseline",
    )

    config.assert_matches_extraction_params(params)
    domain = config.to_domain()

    assert config.profile_id == "chembl.activity-baseline"
    assert config.version == "1.2.3"
    assert config.extraction_params_sha256 == digest
    assert domain.profile_id == "chembl.activity-baseline"
    assert domain.status == "candidate"


@pytest.mark.parametrize(
    ("field_name", "value", "match"),
    [
        ("profile_id", "Bad Profile", "lowercase dotted identifier"),
        ("version", "2026-06-15", "MAJOR.MINOR.PATCH"),
        ("extraction_params_sha256", "not-a-sha", "64-char SHA256"),
    ],
)
def test_source_profile_config_rejects_invalid_values(
    field_name: str,
    value: str,
    match: str,
) -> None:
    payload = {"profile_id": "default", "version": "1.0.0"}
    payload[field_name] = value

    with pytest.raises(ValidationError, match=match):
        SourceProfileYamlConfig(**payload)


def test_source_profile_config_fails_on_extraction_hash_drift() -> None:
    config = SourceProfileYamlConfig(
        extraction_params_sha256="0" * 64,
    )

    with pytest.raises(ValueError, match=r"does not match filters\.extraction_params"):
        config.assert_matches_extraction_params({"limit": 10})
