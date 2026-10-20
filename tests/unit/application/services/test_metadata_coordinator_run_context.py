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
"""RunContext tests extracted from MetadataCoordinator service coverage."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.application.services.lineage.manifest_successor import (
    adopt_live_manifest_successor,
)
from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types import RunID, RunType
from bioetl.domain.value_objects.run_context import RunContext
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

pytestmark = pytest.mark.unit

_FIXED_TIME = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def run_context() -> RunContext:
    """Create a test RunContext."""
    return RunContext.create(
        run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
        run_type=RunType.INCREMENTAL,
        started_at=_FIXED_TIME,
        provider="chembl",
        entity="activity",
    )


class TestRunContext:
    """Tests for RunContext value object."""

    def test_create_with_valid_data(self) -> None:
        """Test creating RunContext with valid data."""
        run_id = RunID(deterministic_uuid_from_callsite("replay-sensitive"))
        started_at = _FIXED_TIME

        context = RunContext.create(
            run_id=run_id,
            run_type=RunType.BACKFILL,
            started_at=started_at,
            provider="pubchem",
            entity="compound",
        )

        assert context.run_id == run_id
        assert context.run_type == RunType.BACKFILL
        assert context.started_at == started_at
        assert context.provider == "pubchem"
        assert context.entity == "compound"
        assert context.pipeline_name == "pubchem_compound"

    def test_create_with_naive_datetime_raises(self) -> None:
        """Test that naive datetime raises ValueError."""
        with pytest.raises(ValueError, match="timezone-aware"):
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.INCREMENTAL,
                started_at=datetime(2025, 1, 1, 12, 0),  # Naive datetime
                provider="chembl",
                entity="activity",
            )

    def test_create_with_empty_provider_raises(self) -> None:
        """Test that empty provider raises ValueError."""
        with pytest.raises(ValueError, match="provider cannot be empty"):
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.INCREMENTAL,
                started_at=_FIXED_TIME,
                provider="",
                entity="activity",
            )

    def test_create_with_empty_entity_raises(self) -> None:
        """Test that empty entity raises ValueError."""
        with pytest.raises(ValueError, match="entity cannot be empty"):
            RunContext.create(
                run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
                run_type=RunType.INCREMENTAL,
                started_at=_FIXED_TIME,
                provider="chembl",
                entity="",
            )

    def test_context_is_immutable(self, run_context: RunContext) -> None:
        """Test that RunContext is immutable (frozen)."""
        with pytest.raises(AttributeError):
            run_context.provider = "new_provider"  # type: ignore[misc]


def test_adopt_manifest_successor_rebinds_coordinator_and_launch(
    run_context: RunContext,
) -> None:
    coordinator = MetadataCoordinator(run_context)
    launch = run_context
    manifest = RunManifest(
        manifest_id="manifest-successor",
        execution_fingerprint="fp-successor",
        run_id=run_context.run_id,
        run_type=run_context.run_type,
        pipeline_name=run_context.pipeline_name,
        provider=run_context.provider,
        entity=run_context.entity,
    )

    class _Services:
        metadata_coordinator = coordinator

    updated = adopt_live_manifest_successor(
        launch_context=launch,
        services=_Services(),
        manifest=manifest,
    )

    assert updated is not None
    assert updated.manifest_id == "manifest-successor"
    assert updated.execution_fingerprint == "fp-successor"
    assert coordinator.run_context.manifest_id == "manifest-successor"
    assert coordinator.run_context.execution_fingerprint == "fp-successor"
    assert run_context.manifest_id != "manifest-successor"
