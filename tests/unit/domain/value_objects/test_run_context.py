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
"""Unit tests for RunContext value object."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

import pytest

from bioetl.domain.types import RunID, RunType
from bioetl.domain.value_objects.run_context import RunContext
from tests.helpers.clock import FIXED_TEST_TIME


def _make_run_id() -> RunID:
    return deterministic_run_uuid_from_callsite("test_run_context")


def _now_utc() -> datetime:
    return FIXED_TEST_TIME


@pytest.mark.unit
class TestRunContextCreation:
    """Tests for RunContext direct construction."""

    def test_run_context_creation__minimal_creation__f10895be(self) -> None:
        """Test creating RunContext with required fields only."""
        run_id = _make_run_id()
        started_at = _now_utc()
        ctx = RunContext(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            started_at=started_at,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
        )
        assert ctx.run_id == run_id
        assert ctx.run_type == RunType.INCREMENTAL
        assert ctx.started_at == started_at
        assert ctx.pipeline_name == "chembl_activity"
        assert ctx.provider == "chembl"
        assert ctx.entity == "activity"
        assert ctx.transform_version is None
        assert ctx.transform_steps == ()
        assert ctx.pipeline_version is None
        assert ctx.git_commit is None
        assert ctx.config_hash is None

    def test_run_context_creation__full_creation__d85e8674(self) -> None:
        """Test creating RunContext with all optional fields."""
        run_id = _make_run_id()
        started_at = _now_utc()
        ctx = RunContext(
            run_id=run_id,
            run_type=RunType.REBUILD,
            started_at=started_at,
            pipeline_name="pubchem_compound",
            provider="pubchem",
            entity="compound",
            transform_version="1.2.3",
            transform_steps=("normalize_values", "add_metadata"),
            pipeline_version="2.0.0",
            git_commit="abc123def456",
            config_hash="sha256:deadbeef",
        )
        assert ctx.transform_version == "1.2.3"
        assert ctx.transform_steps == ("normalize_values", "add_metadata")
        assert ctx.pipeline_version == "2.0.0"
        assert ctx.git_commit == "abc123def456"
        assert ctx.config_hash == "sha256:deadbeef"

    def test_run_context_creation__is_frozen__93f767f4(self) -> None:
        """Test that RunContext is immutable (frozen dataclass)."""
        ctx = RunContext(
            run_id=_make_run_id(),
            run_type=RunType.INCREMENTAL,
            started_at=_now_utc(),
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
        )
        with pytest.raises((AttributeError, TypeError)):
            ctx.provider = "pubchem"  # type: ignore[misc]


@pytest.mark.unit
class TestRunContextValidation:
    """Tests for RunContext post_init validation."""

    def test_naive_datetime_raises(self) -> None:
        """Test that naive (non-timezone-aware) datetime raises ValueError."""
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)  # No tzinfo
        with pytest.raises(ValueError, match="timezone-aware"):
            RunContext(
                run_id=_make_run_id(),
                run_type=RunType.INCREMENTAL,
                started_at=naive_dt,
                pipeline_name="chembl_activity",
                provider="chembl",
                entity="activity",
            )

    def test_run_context_validation__pipeline_name_raises__0970ebe9(self) -> None:
        """Test that empty pipeline_name raises ValueError."""
        with pytest.raises(ValueError, match="pipeline_name cannot be empty"):
            RunContext(
                run_id=_make_run_id(),
                run_type=RunType.INCREMENTAL,
                started_at=_now_utc(),
                pipeline_name="",
                provider="chembl",
                entity="activity",
            )

    def test_run_context_validation__provider_raises__ef3431e4(self) -> None:
        """Test that empty provider raises ValueError."""
        with pytest.raises(ValueError, match="provider cannot be empty"):
            RunContext(
                run_id=_make_run_id(),
                run_type=RunType.INCREMENTAL,
                started_at=_now_utc(),
                pipeline_name="chembl_activity",
                provider="",
                entity="activity",
            )

    def test_run_context_validation__empty_entity_raises__8e487248(self) -> None:
        """Test that empty entity raises ValueError."""
        with pytest.raises(ValueError, match="entity cannot be empty"):
            RunContext(
                run_id=_make_run_id(),
                run_type=RunType.INCREMENTAL,
                started_at=_now_utc(),
                pipeline_name="chembl_activity",
                provider="chembl",
                entity="",
            )

    def test_utc_timezone_accepted(self) -> None:
        """Test that UTC datetime is accepted."""
        ctx = RunContext(
            run_id=_make_run_id(),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
        )
        assert ctx.started_at.tzinfo is not None

    def test_non_utc_timezone_accepted(self) -> None:
        """Test that non-UTC timezone-aware datetime is also accepted."""
        tz = timezone(timedelta(hours=1), name="UTC+01:00")
        ctx = RunContext(
            run_id=_make_run_id(),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=tz),
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
        )
        assert ctx.started_at.tzinfo is not None


@pytest.mark.unit
class TestRunContextFactoryMethod:
    """Tests for RunContext.create() factory method."""

    def test_create_derives_pipeline_name(self) -> None:
        """Test that create() derives pipeline_name as '{provider}_{entity}'."""
        run_id = _make_run_id()
        started_at = _now_utc()
        ctx = RunContext.create(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            started_at=started_at,
            provider="chembl",
            entity="activity",
        )
        assert ctx.pipeline_name == "chembl_activity"
        assert ctx.provider == "chembl"
        assert ctx.entity == "activity"

    def test_create_with_all_options(self) -> None:
        """Test create() with all optional parameters."""
        run_id = _make_run_id()
        started_at = _now_utc()
        ctx = RunContext.create(
            run_id=run_id,
            run_type=RunType.BACKFILL,
            started_at=started_at,
            provider="pubchem",
            entity="compound",
            transform_version="1.0.0",
            transform_steps=("step_a", "step_b"),
            pipeline_version="3.0.0",
            git_commit="deadbeef",
            config_hash="sha256:abc",
            exact_replay=True,
            required_persistence_profile="replay_ready",
            replay_of_run_id="run-parent-1",
            replay_of_manifest_id="manifest-parent-1",
            input_snapshot_fingerprint="snapshot-fingerprint-1",
        )
        assert ctx.pipeline_name == "pubchem_compound"
        assert ctx.transform_version == "1.0.0"
        assert ctx.transform_steps == ("step_a", "step_b")
        assert ctx.pipeline_version == "3.0.0"
        assert ctx.git_commit == "deadbeef"
        assert ctx.config_hash == "sha256:abc"
        assert ctx.exact_replay is True
        assert ctx.required_persistence_profile == "replay_ready"
        assert ctx.replay_of_run_id == "run-parent-1"
        assert ctx.replay_of_manifest_id == "manifest-parent-1"
        assert ctx.input_snapshot_fingerprint == "snapshot-fingerprint-1"

    def test_create_none_transform_steps_defaults_to_empty(self) -> None:
        """Test that None transform_steps is normalized to empty tuple."""
        ctx = RunContext.create(
            run_id=_make_run_id(),
            run_type=RunType.INCREMENTAL,
            started_at=_now_utc(),
            provider="uniprot",
            entity="target",
            transform_steps=None,
        )
        assert ctx.transform_steps == ()

    def test_create_all_run_types(self) -> None:
        """Test create() with all RunType values."""
        for run_type in RunType:
            ctx = RunContext.create(
                run_id=_make_run_id(),
                run_type=run_type,
                started_at=_now_utc(),
                provider="chembl",
                entity="assay",
            )
            assert ctx.run_type == run_type

    def test_create_validates_naive_datetime(self) -> None:
        """Test that create() also validates timezone-aware requirement."""
        with pytest.raises(ValueError, match="timezone-aware"):
            RunContext.create(
                run_id=_make_run_id(),
                run_type=RunType.INCREMENTAL,
                started_at=datetime(2024, 1, 1),  # naive
                provider="chembl",
                entity="activity",
            )
