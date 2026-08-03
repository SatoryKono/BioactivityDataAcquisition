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
"""Tests for manifest service scaffold time resolution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from bioetl.application.services.control_plane.manifest.service_scaffold import (
    ManifestServiceScaffoldMixin,
)
from bioetl.domain.context import MISSING_RUNTIME_TIMESTAMP
from tests.helpers.clock import FixedClock


@dataclass(kw_only=True)
class _ManifestScaffoldProbe(ManifestServiceScaffoldMixin):
    created_at_factory: Callable[[], datetime] | None = None


@pytest.mark.unit
def test_resolve_manifest_created_at_prefers_clock() -> None:
    clock_time = datetime(2026, 5, 21, 8, 0, tzinfo=UTC)
    factory_time = datetime(2026, 5, 21, 9, 0, tzinfo=UTC)
    probe = _ManifestScaffoldProbe(
        clock=FixedClock(clock_time),
        created_at_factory=lambda: factory_time,
    )

    assert probe._resolve_created_at() == clock_time


@pytest.mark.unit
def test_resolve_manifest_created_at_uses_factory_without_clock() -> None:
    factory_time = datetime(2026, 5, 21, 9, 0, tzinfo=UTC)
    probe = _ManifestScaffoldProbe(created_at_factory=lambda: factory_time)

    assert probe._resolve_created_at() == factory_time


@pytest.mark.unit
def test_resolve_manifest_created_at_uses_sentinel_without_time_seam() -> None:
    assert _ManifestScaffoldProbe()._resolve_created_at() == MISSING_RUNTIME_TIMESTAMP
