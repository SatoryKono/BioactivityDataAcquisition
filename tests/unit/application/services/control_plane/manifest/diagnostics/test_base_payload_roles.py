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
"""Focused role-boundary tests for base manifest diagnostics payload sections."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.services.control_plane.manifest.diagnostics.base_provenance_payloads import (
    _build_base_summary_code_provenance_payload,
)


pytestmark = pytest.mark.unit


def test_code_provenance_payload_builder_lives_in_provenance_role_module() -> None:
    code_provenance = SimpleNamespace(
        config_hash="config-hash",
        resolved_config_hash="resolved-config-hash",
        effective_config_hash="effective-config-hash",
        source_fingerprint="source-fingerprint",
        pipeline_version="v1",
        git_commit="abc123",
        source_revision_state="clean",
        contract_ref="contract/ref",
        contract_version="1.0.0",
        normalization_profile_ref="normalization/ref",
        normalization_profile_version="2.0.0",
        normalization_profile_hash="normalization-hash",
        dq_policy_ref="dq/ref",
        rule_bundle_version="rules-v1",
        dq_contract_compatibility_hash="dq-compat-hash",
        effective_config_artifact_id="effective-config-artifact",
    )
    provenance_state = {"dependency_lock_state": "present"}

    payload = _build_base_summary_code_provenance_payload(
        code_provenance=code_provenance,
        dependency_lock_state="present",
        code_provenance_state=provenance_state,
    )

    assert payload == {
        "config_hash": "config-hash",
        "resolved_config_hash": "resolved-config-hash",
        "effective_config_hash": "effective-config-hash",
        "source_fingerprint": "source-fingerprint",
        "pipeline_version": "v1",
        "git_commit": "abc123",
        "source_revision_state": "clean",
        "dependency_lock_state": "present",
        "code_provenance_state": provenance_state,
        "contract_ref": "contract/ref",
        "contract_version": "1.0.0",
        "normalization_profile_ref": "normalization/ref",
        "normalization_profile_version": "2.0.0",
        "normalization_profile_hash": "normalization-hash",
        "dq_policy_ref": "dq/ref",
        "rule_bundle_version": "rules-v1",
        "dq_contract_compatibility_hash": "dq-compat-hash",
        "effective_config_artifact_id": "effective-config-artifact",
    }
