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
"""Unit tests for application-owned record normalization stage."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bioetl.application.core.config import (
    ContentHashPolicyByVersion,
    ContentHashVersionPolicy,
)
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    NormalizationContractError,
    RecordNormalizationProcessor,
)


@pytest.mark.unit
def build_normalization_processor(**kwargs):
    return RecordNormalizationProcessor(**kwargs)


__all__ = [
    "ContentHashPolicyByVersion",
    "ContentHashVersionPolicy",
    "HealthCheck",
    "MagicMock",
    "NormalizationContractError",
    "PreSilverRecord",
    "build_normalization_processor",
    "cast",
    "given",
    "pytest",
    "settings",
    "st",
]
