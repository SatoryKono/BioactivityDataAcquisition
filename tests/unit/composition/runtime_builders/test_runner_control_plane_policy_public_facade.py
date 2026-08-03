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
"""Unit tests for the public control-plane policy facade exports."""

from __future__ import annotations

from importlib import import_module

import pytest

from bioetl.composition.runtime_builders import (
    _runner_control_plane_policy as private_policy,
    runner_control_plane_assembly as public,
)

pytestmark = pytest.mark.unit


def test_runner_control_plane_policy_public_facade_exports_are_stable() -> None:
    """Cross-owner callers must import policy helpers from the public assembly module."""
    assert set(public.__all__) >= {
        "ControlPlaneSetupResult",
        "assemble_runner_control_plane",
        "resolve_required_artifact_lineage_layers",
        "validate_required_persistence_profile",
    }


def test_runner_control_plane_policy_public_facade_reexports_private_helpers() -> None:
    """Public facade must delegate to the runtime_builders private policy module."""
    assert (
        public.resolve_required_artifact_lineage_layers
        is private_policy.resolve_required_artifact_lineage_layers
    )
    assert (
        public.validate_required_persistence_profile
        is private_policy.validate_required_persistence_profile
    )


def test_runner_control_plane_policy_public_facade_is_importable_by_name() -> None:
    """Import-by-name must resolve the reviewed public assembly surface."""
    imported = import_module(
        "bioetl.composition.runtime_builders.runner_control_plane_assembly"
    )
    assert imported is public
