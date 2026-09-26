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
"""Unit tests for CompositeCheckpointService.

Covers load / save / delete / list_all async methods, filename format,
resume vs. fresh-start logic, warning on overwrite, error handling, and
CheckpointConflictError escalation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

import pytest

from bioetl.application.composite.checkpoint.service import (
    CompositeCheckpointService,
    CompositeCheckpointServiceContext,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.composite.result import SeedResult
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.exceptions import CheckpointConflictError, StorageError
from tests.helpers.clock import FixedClock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXED_CHECKPOINT_TIME = datetime(2024, 6, 2, 12, 0, tzinfo=UTC)
VALID_EFFECTIVE_HASH = "a" * 64
ALTERNATE_EFFECTIVE_HASH = "b" * 64
_DEFAULT_CLOCK = object()


@dataclass(frozen=True)
class _ExpectedCheckpointAnchors:
    effective_config_hash: str | None = None
    effective_config_artifact_id: str | None = None
    execution_fingerprint: str | None = None
    dq_contract_compatibility_hash: str | None = None
    input_snapshot_fingerprint: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    manifest_id: str | None = None


def _anchors(
    *,
    effective_config_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    execution_fingerprint: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    input_snapshot_fingerprint: str | None = None,
    contract_ref: str | None = None,
    contract_version: str | None = None,
    manifest_id: str | None = None,
) -> _ExpectedCheckpointAnchors:
    return _ExpectedCheckpointAnchors(
        effective_config_hash=effective_config_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        execution_fingerprint=execution_fingerprint,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        contract_ref=contract_ref,
        contract_version=contract_version,
        manifest_id=manifest_id,
    )


def _make_logger() -> MagicMock:
    """Create a mock LoggerPort (accepts **kwargs via MagicMock)."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


def _make_storage() -> MagicMock:
    """Create a mock CompositeCheckpointPort."""
    storage = MagicMock()
    storage.read = MagicMock(return_value=None)
    storage.write_atomic = MagicMock()
    storage.delete = MagicMock(return_value=False)
    storage.list_glob = MagicMock(return_value=[])
    storage.exists = MagicMock(return_value=False)
    return storage


def _make_service(
    composite_name: str = "my_composite",
    run_id: str = "run-001",
    storage: MagicMock | None = None,
    logger: MagicMock | None = None,
    resume: bool = False,
    expected_anchors: _ExpectedCheckpointAnchors | None = None,
    run_ledger_port: MagicMock | None = None,
    metrics: MagicMock | None = None,
    clock: FixedClock | object | None = _DEFAULT_CLOCK,
) -> tuple[CompositeCheckpointService, MagicMock, MagicMock]:
    """Convenience factory — returns (service, storage_mock, logger_mock)."""
    s = storage if storage is not None else _make_storage()
    lg = logger if logger is not None else _make_logger()
    mt = metrics if metrics is not None else MagicMock()
    anchors = expected_anchors or _ExpectedCheckpointAnchors()
    resolved_clock = (
        FixedClock(FIXED_CHECKPOINT_TIME) if clock is _DEFAULT_CLOCK else clock
    )
    svc = CompositeCheckpointService(
        CompositeCheckpointServiceContext(
            composite_name=composite_name,
            run_id=run_id,
            storage=s,
            logger=lg,
            resume=resume,
            expected_effective_config_hash=anchors.effective_config_hash,
            expected_effective_config_artifact_id=anchors.effective_config_artifact_id,
            expected_execution_fingerprint=anchors.execution_fingerprint,
            expected_dq_contract_compatibility_hash=(
                anchors.dq_contract_compatibility_hash
            ),
            expected_input_snapshot_fingerprint=anchors.input_snapshot_fingerprint,
            expected_contract_ref=anchors.contract_ref,
            expected_contract_version=anchors.contract_version,
            expected_manifest_id=anchors.manifest_id,
            run_ledger_port=run_ledger_port,
            metrics=mt,
            clock=resolved_clock,
        )
    )
    return svc, s, lg


def _serialized_state(
    composite_name: str = "my_composite",
    run_id: str = "run-001",
    state: CompositePipelineState = CompositePipelineState.SEED_COMPLETED,
    seed_completed: bool = True,
    with_seed_result: bool = True,
    composite_run_identity: str | None = None,
    last_event_id: str | None = None,
    last_event_occurred_at: str | None = None,
) -> str:
    """Return a JSON string that can be returned by storage.read()."""
    sr = None
    if with_seed_result:
        sr = {
            "pipeline_name": "chembl_activity",
            "records_extracted": 100,
            "records_silver": 95,
            "keys_generated": 90,
            "duration_seconds": 10.5,
            "resumed": False,
        }
    data = {
        "composite_name": composite_name,
        "run_id": run_id,
        "state": state.value,
        "seed_completed": seed_completed,
        "seed_result": sr,
        "completed_dependencies": [],
        "dependency_results": {},
        "completed_enrichers": [],
        "enrichment_results": {},
        "composite_run_identity": composite_run_identity or run_id,
        "last_event_id": last_event_id,
        "last_event_occurred_at": last_event_occurred_at,
        "created_at": "2024-06-01T08:00:00+00:00",
        "updated_at": "2024-06-01T09:00:00+00:00",
    }
    return json.dumps(data)


def _make_run_ledger_entry(
    *,
    entry_id: str,
    manifest_id: str = "manifest-123",
    event_type: str = "stage_completed",
    stage: str | None = None,
    occurred_at: datetime | None = None,
    status: str = "completed",
    details: dict[str, object] | None = None,
) -> RunLedgerEntry:
    return RunLedgerEntry(
        entry_id=entry_id,
        manifest_id=manifest_id,
        run_id=deterministic_run_uuid_from_callsite("test_checkpoint_service"),
        event_type=event_type,
        stage=stage,
        occurred_at=occurred_at or FIXED_CHECKPOINT_TIME,
        status=status,
        details=details,
    )


def _enriched_serialized_state(
    composite_name: str = "my_composite",
    run_id: str = "run-001",
    composite_run_identity: str | None = None,
) -> str:
    """Return JSON with enricher progress (is_resumable=True)."""
    data = {
        "composite_name": composite_name,
        "run_id": run_id,
        "state": CompositePipelineState.ENRICHING.value,
        "seed_completed": True,
        "seed_result": {
            "pipeline_name": "chembl_activity",
            "records_extracted": 100,
            "records_silver": 95,
            "keys_generated": 90,
            "duration_seconds": 10.5,
            "resumed": False,
        },
        "completed_dependencies": [],
        "dependency_results": {},
        "completed_enrichers": ["crossref"],
        "enrichment_results": {
            "crossref": {
                "enricher_name": "crossref",
                "status": "success",
                "records_input": 100,
                "records_enriched": 95,
                "records_not_found": 5,
                "records_errored": 0,
                "dq_error_rate": 0.0,
                "duration_seconds": 10.0,
                "error_message": None,
            }
        },
        "composite_run_identity": composite_run_identity or run_id,
        "created_at": "2024-06-01T08:00:00+00:00",
        "updated_at": "2024-06-01T09:00:00+00:00",
    }
    return json.dumps(data)


# ---------------------------------------------------------------------------
# 1. Filename format
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilenameFormat:
    """Tests that the checkpoint filename follows the expected pattern."""

    def test_filename_format(self) -> None:
        """Filename is composite_{name}_{run_id}.json."""
        svc, _, _ = _make_service(composite_name="my_composite", run_id="run-001")
        assert svc._checkpoint_filename == "composite_my_composite_run-001.json"

    def test_glob_pattern(self) -> None:
        """Glob pattern matches all run_ids for this composite."""
        svc, _, _ = _make_service(composite_name="my_composite")
        assert svc._glob_pattern() == "composite_my_composite_*.json"

    def test_exposes_expected_anchor_properties(self) -> None:
        """Expected checkpoint anchors stay readable for dependent helpers."""
        svc, _, _ = _make_service(
            expected_anchors=_anchors(
                effective_config_hash=VALID_EFFECTIVE_HASH,
                effective_config_artifact_id="artifact-123",
                execution_fingerprint="fingerprint-123",
                dq_contract_compatibility_hash="dq-hash-123",
                input_snapshot_fingerprint="snapshot-fp-123",
                contract_ref="composite_publication",
                contract_version="2.1.0",
                manifest_id="manifest-123",
            ),
        )

        assert svc.expected_effective_config_hash == VALID_EFFECTIVE_HASH
        assert svc.expected_effective_config_artifact_id == "artifact-123"
        assert svc.expected_execution_fingerprint == "fingerprint-123"
        assert svc.expected_dq_contract_compatibility_hash == "dq-hash-123"
        assert svc.expected_input_snapshot_fingerprint == "snapshot-fp-123"
        assert svc.expected_contract_ref == "composite_publication"
        assert svc.expected_contract_version == "2.1.0"
        assert svc.expected_manifest_id == "manifest-123"

    def test_normalizes_expected_anchor_properties(self) -> None:
        """Expected checkpoint anchors are canonicalized on service construction."""
        svc, _, _ = _make_service(
            expected_anchors=_anchors(
                effective_config_hash=f" SHA256:{'A' * 64} ",
                effective_config_artifact_id=" artifact-123 ",
                execution_fingerprint=" fingerprint-123 ",
                dq_contract_compatibility_hash=" DQ-HASH-123 ",
                input_snapshot_fingerprint=" SNAPSHOT-FP-123 ",
                contract_ref=" Composite_Publication ",
                contract_version=" v2 ",
                manifest_id=" manifest-123 ",
            ),
        )

        assert svc.expected_effective_config_hash == VALID_EFFECTIVE_HASH
        assert svc.expected_effective_config_artifact_id == "artifact-123"
        assert svc.expected_execution_fingerprint == "fingerprint-123"
        assert svc.expected_dq_contract_compatibility_hash == "dq-hash-123"
        assert svc.expected_input_snapshot_fingerprint == "snapshot-fp-123"
        assert svc.expected_contract_ref == "composite_publication"
        assert svc.expected_contract_version == "2.0.0"
        assert svc.expected_manifest_id == "manifest-123"


# ---------------------------------------------------------------------------
# 2. load – fresh start (resume=False)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadFreshStart:
    """Tests for load() with resume=False."""

    @pytest.mark.asyncio
    async def test_fresh_load_returns_not_started_state(self) -> None:
        """load(resume=False) with no existing checkpoint returns NOT_STARTED state."""
        svc, storage, _ = _make_service(resume=False)
        storage.list_glob.return_value = []

        state = await svc.load()

        assert isinstance(state, CompositeCheckpointState)
        assert state.state == CompositePipelineState.NOT_STARTED

    @pytest.mark.asyncio
    async def test_fresh_load_sets_composite_name_and_run_id(self) -> None:
        """Fresh state carries the service's composite_name and run_id."""
        svc, storage, _ = _make_service(
            composite_name="my_composite", run_id="run-fresh", resume=False
        )
        storage.list_glob.return_value = []

        state = await svc.load()

        assert state.composite_name == "my_composite"
        assert state.run_id == "run-fresh"

    @pytest.mark.asyncio
    async def test_fresh_load_sets_created_at(self) -> None:
        """Fresh state has a non-None created_at."""
        svc, storage, _ = _make_service(resume=False)
        storage.list_glob.return_value = []

        state = await svc.load()

        assert state.created_at is not None

    @pytest.mark.asyncio
    async def test_fresh_load_uses_injected_clock_for_created_at(self) -> None:
        """Fresh checkpoint bootstrap should use the injected ClockPort."""
        fixed_time = datetime(2026, 4, 23, 11, 0, tzinfo=UTC)
        svc, storage, _ = _make_service(
            resume=False,
            clock=FixedClock(fixed_time),
        )
        storage.list_glob.return_value = []

        state = await svc.load()

        assert state.created_at == fixed_time

    @pytest.mark.asyncio
    async def test_fresh_load_carries_expected_manifest_id(self) -> None:
        """Fresh checkpoint state should retain manifest anchor from bootstrap."""
        svc, storage, _ = _make_service(
            resume=False,
            expected_anchors=_anchors(manifest_id="manifest-123"),
        )
        storage.list_glob.return_value = []

        state = await svc.load()

        assert state.manifest_id == "manifest-123"


# ---------------------------------------------------------------------------
# 3. load – resume mode (resume=True)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadResume:
    """Tests for load() with resume=True."""

    @pytest.mark.asyncio
    async def test_resume_loads_existing_checkpoint(self) -> None:
        """load(resume=True) reads and returns the existing checkpoint."""
        metrics = MagicMock()
        svc, storage, _ = _make_service(resume=True, metrics=metrics)
        content = _serialized_state(state=CompositePipelineState.SEED_COMPLETED)
        storage.exists.return_value = True
        storage.read.return_value = content

        state = await svc.load()

        assert state.state == CompositePipelineState.SEED_COMPLETED
        assert state.seed_completed is True
        metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "my_composite", "status": "loaded"},
        )
        metrics.set_gauge.assert_called_once_with(
            "bioetl_checkpoint_saved_at_seconds",
            datetime(2024, 6, 1, 9, 0, tzinfo=UTC).timestamp(),
            {"pipeline": "my_composite"},
        )

    @pytest.mark.asyncio
    async def test_resume_preserves_replay_watermark(self) -> None:
        """load(resume=True) preserves persisted replay watermark fields."""
        svc, storage, _ = _make_service(resume=True)
        storage.exists.return_value = True
        storage.read.return_value = _serialized_state(
            state=CompositePipelineState.SEED_COMPLETED,
            last_event_id="evt-123",
            last_event_occurred_at="2024-06-01T09:30:00+00:00",
        )

        state = await svc.load()

        assert state.last_event_id == "evt-123"
        assert state.last_event_occurred_at == datetime(
            2024,
            6,
            1,
            9,
            30,
            tzinfo=UTC,
        )

    @pytest.mark.asyncio
    async def test_resume_returns_fresh_when_no_checkpoint_exists(self) -> None:
        """load(resume=True) returns fresh state when no file is found."""
        metrics = MagicMock()
        svc, storage, _ = _make_service(resume=True, metrics=metrics)
        storage.exists.return_value = False
        storage.list_glob.return_value = []

        state = await svc.load()

        assert state.state == CompositePipelineState.NOT_STARTED
        metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "my_composite", "status": "missing"},
        )

    @pytest.mark.asyncio
    async def test_resume_blocks_glob_fallback_from_different_run_identity(
        self,
    ) -> None:
        """If exact filename missing, resume rejects a checkpoint from another run."""
        svc, storage, _ = _make_service(
            composite_name="my_composite",
            run_id="run-new",
            resume=True,
        )
        latest_filename = "composite_my_composite_run-old.json"
        content = _serialized_state(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
        )

        # Exact file does not exist; glob returns an older file
        def exists_side_effect(path: str) -> bool:
            return path == latest_filename

        storage.exists.side_effect = exists_side_effect
        storage.list_glob.return_value = [latest_filename]
        storage.read.return_value = content

        with pytest.raises(CheckpointConflictError):
            await svc.load()

    @pytest.mark.asyncio
    async def test_resume_handles_corrupted_json_gracefully(self) -> None:
        """Corrupted JSON during resume falls back to fresh state without raising."""
        metrics = MagicMock()
        svc, storage, _ = _make_service(resume=True, metrics=metrics)
        storage.exists.return_value = True
        storage.read.return_value = "NOT VALID JSON {"

        state = await svc.load()

        # Graceful degradation: returns fresh NOT_STARTED state
        assert state.state == CompositePipelineState.NOT_STARTED
        metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "my_composite", "status": "failed"},
        )

    @pytest.mark.asyncio
    async def test_resume_handles_none_content_gracefully(self) -> None:
        """None returned by storage.read() during resume falls back to fresh state."""
        svc, storage, _ = _make_service(resume=True)
        storage.exists.return_value = True
        storage.read.return_value = None

        state = await svc.load()

        assert state.state == CompositePipelineState.NOT_STARTED

    @pytest.mark.asyncio
    async def test_resume_blocks_on_contract_ref_mismatch(self) -> None:
        """Resume is blocked when checkpoint contract_ref mismatches expected anchor."""
        svc, storage, logger = _make_service(
            resume=True,
            run_id="run-old",
            expected_anchors=_anchors(contract_ref="composite_publication"),
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            contract_ref="composite_activity",
            contract_version="1.0.0",
            composite_run_identity="run-old",
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        with pytest.raises(CheckpointConflictError):
            await svc.load()

        error_calls = [str(c) for c in logger.error.call_args_list]
        assert any("checkpoint_resume_incompatible" in c for c in error_calls)

    @pytest.mark.asyncio
    async def test_resume_blocks_on_contract_version_mismatch(self) -> None:
        """Resume is blocked when checkpoint contract_version mismatches expected anchor."""
        svc, storage, _ = _make_service(
            resume=True,
            run_id="run-old",
            expected_anchors=_anchors(
                contract_ref="composite_publication",
                contract_version="2.0.0",
            ),
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            contract_ref="composite_publication",
            contract_version="1.0.0",
            composite_run_identity="run-old",
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        with pytest.raises(CheckpointConflictError):
            await svc.load()

    @pytest.mark.asyncio
    async def test_resume_blocks_when_effective_hash_missing(self) -> None:
        """Missing effective_config_hash anchor blocks resume when expected."""
        svc, storage, _ = _make_service(
            resume=True,
            run_id="run-old",
            expected_anchors=_anchors(
                contract_ref="composite_publication",
                effective_config_hash=VALID_EFFECTIVE_HASH,
            ),
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            contract_ref="composite_publication",
            contract_version="1.0.0",
            effective_config_hash="",
            composite_run_identity="run-old",
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        with pytest.raises(CheckpointConflictError):
            await svc.load()

    @pytest.mark.asyncio
    async def test_resume_blocks_on_effective_hash_mismatch(self) -> None:
        """Resume is blocked when checkpoint effective_config_hash mismatches expected."""
        svc, storage, _ = _make_service(
            resume=True,
            run_id="run-old",
            expected_anchors=_anchors(
                contract_ref="composite_publication",
                effective_config_hash=VALID_EFFECTIVE_HASH,
            ),
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            contract_ref="composite_publication",
            contract_version="1.0.0",
            effective_config_hash=ALTERNATE_EFFECTIVE_HASH,
            composite_run_identity="run-old",
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        with pytest.raises(CheckpointConflictError):
            await svc.load()

    @pytest.mark.asyncio
    async def test_resume_blocks_when_execution_fingerprint_missing(self) -> None:
        """Resume is blocked when a checkpoint lacks an expected fingerprint."""
        svc, storage, _ = _make_service(
            resume=True,
            run_id="run-old",
            expected_anchors=_anchors(execution_fingerprint="fingerprint-current"),
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            composite_run_identity="run-old",
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        with pytest.raises(CheckpointConflictError):
            await svc.load()

    @pytest.mark.asyncio
    async def test_resume_blocks_on_full_semantic_anchor_mismatch(self) -> None:
        """Resume is blocked when explicit semantic identity anchors mismatch."""
        svc, storage, _ = _make_service(
            resume=True,
            run_id="run-old",
            expected_anchors=_anchors(
                execution_fingerprint="fingerprint-current",
                effective_config_artifact_id="artifact-current",
                dq_contract_compatibility_hash="dq-current",
                input_snapshot_fingerprint="snapshot-current",
            ),
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            execution_fingerprint="fingerprint-old",
            effective_config_artifact_id="artifact-old",
            dq_contract_compatibility_hash="dq-old",
            input_snapshot_fingerprint="snapshot-old",
            composite_run_identity="run-old",
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        with pytest.raises(CheckpointConflictError):
            await svc.load()

    @pytest.mark.asyncio
    async def test_resume_blocks_on_input_snapshot_fingerprint_mismatch(self) -> None:
        """Resume is blocked when both sides carry different input snapshot anchors."""
        svc, storage, _ = _make_service(
            resume=True,
            run_id="run-old",
            expected_anchors=_anchors(
                input_snapshot_fingerprint="snapshot-current",
            ),
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            input_snapshot_fingerprint="snapshot-old",
            composite_run_identity="run-old",
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        with pytest.raises(CheckpointConflictError, match="input_snapshot_fingerprint"):
            await svc.load()

    @pytest.mark.asyncio
    async def test_resume_blocks_missing_input_snapshot_fingerprint_for_strict_checkpoint(
        self,
    ) -> None:
        """Strict replay resume is blocked when old checkpoints omit snapshot anchors."""
        svc, storage, _ = _make_service(
            resume=True,
            run_id="run-old",
            expected_anchors=_anchors(
                input_snapshot_fingerprint="snapshot-current",
            ),
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            composite_run_identity="run-old",
        )
        payload = state_data.to_dict()
        payload.pop("input_snapshot_fingerprint")
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(payload)

        with pytest.raises(CheckpointConflictError, match="input_snapshot_fingerprint"):
            await svc.load()

    @pytest.mark.asyncio
    async def test_resume_replays_only_ledger_entries_after_checkpoint_watermark(
        self,
    ) -> None:
        """Resume replays only the suffix after the checkpoint watermark."""
        ledger_port = MagicMock()
        metrics = MagicMock()
        first_replayed = _make_run_ledger_entry(
            entry_id="entry-2",
            stage="dependencies",
            occurred_at=datetime(2024, 6, 1, 10, 0, tzinfo=UTC),
        )
        second_replayed = _make_run_ledger_entry(
            entry_id="entry-3",
            event_type="run_finished",
            occurred_at=datetime(2024, 6, 1, 11, 0, tzinfo=UTC),
        )
        ledger_port.list_entries_after.return_value = [first_replayed, second_replayed]
        svc, storage, _ = _make_service(
            resume=True,
            run_id="run-old",
            expected_anchors=_anchors(manifest_id="manifest-123"),
            run_ledger_port=ledger_port,
            metrics=metrics,
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            manifest_id="manifest-123",
            composite_run_identity="run-old",
            last_event_id="entry-1",
            last_event_occurred_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        state = await svc.load()

        ledger_port.list_entries_after.assert_called_once_with(
            "manifest-123",
            "entry-1",
        )
        assert state.state == CompositePipelineState.COMPLETED
        assert state.seed_completed is True
        assert state.last_event_id == "entry-3"
        assert state.last_event_occurred_at == second_replayed.occurred_at
        metrics.increment_counter.assert_any_call(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "my_composite", "status": "loaded"},
        )
        metrics.increment_counter.assert_any_call(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "my_composite", "status": "replayed"},
        )

    @pytest.mark.asyncio
    async def test_resume_replay_preserves_snapshot_payloads_while_applying_flags(
        self,
    ) -> None:
        """Resume replay should update coarse progress without fabricating payloads."""
        ledger_port = MagicMock()
        ledger_port.list_entries_after.return_value = [
            _make_run_ledger_entry(
                entry_id="entry-2",
                stage="merge",
                occurred_at=datetime(2024, 6, 1, 10, 0, tzinfo=UTC),
            ),
            _make_run_ledger_entry(
                entry_id="entry-3",
                event_type="run_failed",
                occurred_at=datetime(2024, 6, 1, 10, 30, tzinfo=UTC),
            ),
        ]
        svc, storage, _ = _make_service(
            resume=True,
            run_id="run-old",
            expected_anchors=_anchors(manifest_id="manifest-123"),
            run_ledger_port=ledger_port,
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHMENT_COMPLETED,
            seed_completed=True,
            seed_result=SeedResult(
                pipeline_name="chembl_activity",
                records_extracted=100,
                records_silver=95,
                keys_generated=90,
                duration_seconds=10.5,
            ),
            completed_enrichers=frozenset({"crossref"}),
            enrichment_results={},
            manifest_id="manifest-123",
            composite_run_identity="run-old",
            last_event_id="entry-1",
            last_event_occurred_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
            merge_completed=False,
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        state = await svc.load()

        assert state.state == CompositePipelineState.FAILED
        assert state.seed_completed is True
        assert state.seed_result == state_data.seed_result
        assert state.completed_enrichers == frozenset({"crossref"})
        assert state.merge_completed is True
        assert state.last_event_id == "entry-3"

    @pytest.mark.asyncio
    async def test_resume_replay_reconstructs_rich_composite_payloads(
        self,
    ) -> None:
        """Resume replay reconstructs bounded dependency/enricher/merge payloads."""
        ledger_port = MagicMock()
        ledger_port.list_entries_after.return_value = [
            _make_run_ledger_entry(
                entry_id="entry-2",
                event_type="composite_dependency_completed",
                occurred_at=datetime(2024, 6, 1, 10, 0, tzinfo=UTC),
                status="success",
                details={
                    "dependency_name": "chembl_molecule",
                    "pipeline_name": "chembl_molecule",
                    "status": "success",
                    "records_extracted": 8,
                    "records_silver": 7,
                    "duration_seconds": 1.5,
                },
            ),
            _make_run_ledger_entry(
                entry_id="entry-3",
                event_type="composite_enricher_completed",
                occurred_at=datetime(2024, 6, 1, 10, 1, tzinfo=UTC),
                status="partial",
                details={
                    "enricher_name": "pubmed_publication",
                    "status": "partial",
                    "records_input": 10,
                    "records_enriched": 6,
                    "records_not_found": 3,
                    "records_errored": 1,
                    "dq_error_rate": 0.1,
                    "duration_seconds": 2.0,
                },
            ),
            _make_run_ledger_entry(
                entry_id="entry-4",
                event_type="composite_merge_completed",
                occurred_at=datetime(2024, 6, 1, 10, 2, tzinfo=UTC),
                status="completed",
                details={
                    "records_merged": 10,
                    "records_enriched": 6,
                    "output_silver_path": "silver/composite/publication",
                },
            ),
        ]
        svc, storage, _ = _make_service(
            resume=True,
            run_id="run-old",
            expected_anchors=_anchors(manifest_id="manifest-123"),
            run_ledger_port=ledger_port,
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.SEED_COMPLETED,
            seed_completed=True,
            manifest_id="manifest-123",
            composite_run_identity="run-old",
            last_event_id="entry-1",
            last_event_occurred_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        state = await svc.load()

        assert state.completed_dependencies == frozenset({"chembl_molecule"})
        assert state.dependency_results["chembl_molecule"].records_silver == 7
        assert state.completed_enrichers == frozenset({"pubmed_publication"})
        assert state.enrichment_results["pubmed_publication"].records_errored == 1
        assert state.merge_completed is True
        assert state.merge_result == {
            "output_silver_path": "silver/composite/publication",
            "records_enriched": 6,
            "records_merged": 10,
        }
        assert state.last_event_id == "entry-4"

    @pytest.mark.asyncio
    async def test_resume_emits_replay_not_needed_when_no_suffix_entries_exist(
        self,
    ) -> None:
        """Resume should surface that no ledger suffix replay was necessary."""
        ledger_port = MagicMock()
        metrics = MagicMock()
        ledger_port.list_entries_after.return_value = []
        svc, storage, _ = _make_service(
            resume=True,
            run_id="run-old",
            expected_anchors=_anchors(manifest_id="manifest-123"),
            run_ledger_port=ledger_port,
            metrics=metrics,
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            manifest_id="manifest-123",
            composite_run_identity="run-old",
            last_event_id="entry-1",
            last_event_occurred_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        state = await svc.load()

        assert state.last_event_id == "entry-1"
        metrics.increment_counter.assert_any_call(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "my_composite", "status": "loaded"},
        )
        metrics.increment_counter.assert_any_call(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "my_composite", "status": "replay_not_needed"},
        )

    @pytest.mark.asyncio
    async def test_resume_raises_conflict_when_ledger_watermark_is_missing(
        self,
    ) -> None:
        """Resume fails fast when checkpoint watermark cannot be found in ledger."""
        ledger_port = MagicMock()
        metrics = MagicMock()
        ledger_port.list_entries_after.side_effect = ValueError("missing watermark")
        svc, storage, _ = _make_service(
            resume=True,
            run_id="run-old",
            expected_anchors=_anchors(manifest_id="manifest-123"),
            run_ledger_port=ledger_port,
            metrics=metrics,
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            manifest_id="manifest-123",
            composite_run_identity="run-old",
            last_event_id="entry-missing",
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        with pytest.raises(CheckpointConflictError):
            await svc.load()
        metrics.increment_counter.assert_any_call(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "my_composite", "status": "loaded"},
        )
        metrics.increment_counter.assert_any_call(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "my_composite", "status": "replay_conflict"},
        )

    @pytest.mark.asyncio
    async def test_resume_raises_conflict_when_suffix_contains_unsupported_replay_entry(
        self,
    ) -> None:
        """Resume fails closed when bounded suffix projector lacks coverage."""
        ledger_port = MagicMock()
        metrics = MagicMock()
        ledger_port.list_entries_after.return_value = [
            _make_run_ledger_entry(
                entry_id="entry-future",
                event_type="future_resume_delta",
                occurred_at=datetime(2024, 6, 1, 10, 0, tzinfo=UTC),
            ),
        ]
        svc, storage, logger = _make_service(
            resume=True,
            run_id="run-old",
            expected_anchors=_anchors(manifest_id="manifest-123"),
            run_ledger_port=ledger_port,
            metrics=metrics,
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            manifest_id="manifest-123",
            composite_run_identity="run-old",
            last_event_id="entry-1",
            last_event_occurred_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        with pytest.raises(
            CheckpointConflictError, match="unsupported replay-relevant ledger entries"
        ):
            await svc.load()

        logger.error.assert_any_call(
            "Checkpoint replay suffix is outside bounded projector coverage",
            composite="my_composite",
            manifest_id="manifest-123",
            checkpoint_run_id="run-old",
            projection_contract="checkpoint_snapshot_plus_ledger_suffix_resume",
            unsupported_replay_entries=[
                {
                    "entry_id": "entry-future",
                    "event_type": "future_resume_delta",
                    "stage": None,
                }
            ],
            reason_code="checkpoint_replay_projection_incomplete",
        )
        metrics.increment_counter.assert_any_call(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "my_composite", "status": "loaded"},
        )
        metrics.increment_counter.assert_any_call(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "my_composite", "status": "replay_conflict"},
        )

    @pytest.mark.asyncio
    async def test_resume_blocks_on_manifest_id_mismatch(self) -> None:
        """Resume is blocked when checkpoint manifest_id mismatches expected anchor."""
        svc, storage, _ = _make_service(
            resume=True,
            run_id="run-old",
            expected_anchors=_anchors(manifest_id="manifest-current"),
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            manifest_id="manifest-old",
            composite_run_identity="run-old",
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        with pytest.raises(CheckpointConflictError):
            await svc.load()

    @pytest.mark.asyncio
    async def test_resume_blocks_on_composite_run_identity_mismatch(self) -> None:
        """Resume is blocked when checkpoint composite_run_identity mismatches."""
        svc, storage, logger = _make_service(
            resume=True,
            run_id="run-current",
            expected_anchors=_anchors(manifest_id="manifest-current"),
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            manifest_id="manifest-current",
            composite_run_identity="run-old",
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        with pytest.raises(CheckpointConflictError):
            await svc.load()

        error_calls = [str(c) for c in logger.error.call_args_list]
        assert any("composite_run_identity" in c for c in error_calls)

    @pytest.mark.asyncio
    async def test_resume_blocks_when_composite_run_identity_missing(self) -> None:
        """Resume is blocked when checkpoint misses composite_run_identity anchor."""
        svc, storage, logger = _make_service(
            resume=True,
            run_id="run-current",
            expected_anchors=_anchors(manifest_id="manifest-current"),
        )
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-old",
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            manifest_id="manifest-current",
            composite_run_identity="",
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())

        with pytest.raises(CheckpointConflictError):
            await svc.load()

        error_calls = [str(c) for c in logger.error.call_args_list]
        assert any("missing composite_run_identity" in c for c in error_calls)


# ---------------------------------------------------------------------------
# 4. load – warns on overwrite (resume=False, existing checkpoint with progress)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadWarnOnOverwrite:
    """Tests for warning when resume=False and existing checkpoint has progress."""

    @pytest.mark.asyncio
    async def test_warns_when_existing_checkpoint_has_progress(self) -> None:
        """load(resume=False) warns if an existing checkpoint is resumable."""
        metrics = MagicMock()
        svc, storage, logger = _make_service(resume=False, metrics=metrics)
        latest_filename = "composite_my_composite_run-old.json"
        storage.list_glob.return_value = [latest_filename]
        storage.exists.return_value = True
        storage.read.return_value = _enriched_serialized_state()

        await svc.load()

        warning_calls = [str(c) for c in logger.warning.call_args_list]
        assert any(
            "Existing checkpoint with progress will be overwritten" in c
            for c in warning_calls
        )
        metrics.set_gauge.assert_called_once_with(
            "bioetl_checkpoint_saved_at_seconds",
            datetime(2024, 6, 1, 9, 0, tzinfo=UTC).timestamp(),
            {"pipeline": "my_composite"},
        )

    @pytest.mark.asyncio
    async def test_no_warn_when_no_existing_checkpoint(self) -> None:
        """load(resume=False) does not warn when no checkpoint file exists."""
        svc, storage, logger = _make_service(resume=False)
        storage.list_glob.return_value = []

        await svc.load()

        warning_calls = [str(c) for c in logger.warning.call_args_list]
        assert not any(
            "Existing checkpoint with progress will be overwritten" in c
            for c in warning_calls
        )

    @pytest.mark.asyncio
    async def test_no_warn_when_checkpoint_has_no_progress(self) -> None:
        """load(resume=False) does not warn if existing checkpoint is not resumable."""
        svc, storage, logger = _make_service(resume=False)
        latest_filename = "composite_my_composite_run-old.json"
        storage.list_glob.return_value = [latest_filename]
        storage.exists.return_value = True
        # A fresh NOT_STARTED checkpoint is not resumable
        fresh_json = json.dumps(
            {
                "composite_name": "my_composite",
                "run_id": "run-old",
                "state": "not_started",
                "seed_completed": False,
                "seed_result": None,
                "completed_dependencies": [],
                "dependency_results": {},
                "completed_enrichers": [],
                "enrichment_results": {},
                "created_at": None,
                "updated_at": None,
            }
        )
        storage.read.return_value = fresh_json

        await svc.load()

        warning_calls = [str(c) for c in logger.warning.call_args_list]
        assert not any(
            "Existing checkpoint with progress will be overwritten" in c
            for c in warning_calls
        )

    @pytest.mark.asyncio
    async def test_debug_logged_when_checkpoint_unreadable(self) -> None:
        """If existing checkpoint cannot be parsed, a debug log is emitted (not warning)."""
        svc, storage, logger = _make_service(resume=False)
        latest_filename = "composite_my_composite_run-old.json"
        storage.list_glob.return_value = [latest_filename]
        storage.exists.return_value = True
        storage.read.return_value = "BROKEN JSON"

        await svc.load()

        debug_calls = [str(c) for c in logger.debug.call_args_list]
        assert any("cannot be parsed" in c for c in debug_calls)

    @pytest.mark.asyncio
    async def test_fresh_state_carries_expected_compatibility_anchors(self) -> None:
        """Fresh load should seed expected compatibility anchors into checkpoint state."""
        svc, storage, _ = _make_service(
            resume=False,
            expected_anchors=_anchors(
                effective_config_hash=VALID_EFFECTIVE_HASH,
                effective_config_artifact_id="artifact-123",
                execution_fingerprint="fingerprint-123",
                dq_contract_compatibility_hash="dq-hash-123",
                input_snapshot_fingerprint="snapshot-fp-123",
                contract_ref="composite_publication",
                contract_version="2.1.0",
            ),
        )
        storage.list_glob.return_value = []

        state = await svc.load()

        assert state.effective_config_hash == VALID_EFFECTIVE_HASH
        assert state.effective_config_artifact_id == "artifact-123"
        assert state.execution_fingerprint == "fingerprint-123"
        assert state.dq_contract_compatibility_hash == "dq-hash-123"
        assert state.input_snapshot_fingerprint == "snapshot-fp-123"
        assert state.contract_ref == "composite_publication"
        assert state.contract_version == "2.1.0"
        assert state.composite_run_identity == "run-001"


# ---------------------------------------------------------------------------
# 5. save
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSave:
    """Tests for save() atomic write behaviour."""

    @pytest.mark.asyncio
    async def test_save_calls_write_atomic(self) -> None:
        """save() delegates to storage.write_atomic with the correct filename."""
        svc, storage, _ = _make_service(composite_name="my_composite", run_id="run-001")
        checkpoint = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
            state=CompositePipelineState.ENRICHING,
            created_at=FIXED_CHECKPOINT_TIME,
        )

        await svc.save(checkpoint)

        storage.write_atomic.assert_called_once()
        call_args = storage.write_atomic.call_args
        filename_arg = call_args[0][0]
        assert filename_arg == "composite_my_composite_run-001.json"

    @pytest.mark.asyncio
    async def test_save_content_is_valid_json(self) -> None:
        """Content passed to write_atomic is valid JSON."""
        svc, storage, _ = _make_service()
        checkpoint = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
            created_at=FIXED_CHECKPOINT_TIME,
        )

        await svc.save(checkpoint)

        content_arg = storage.write_atomic.call_args[0][1]
        parsed = json.loads(content_arg)
        assert parsed["composite_name"] == "my_composite"
        assert parsed["run_id"] == "run-001"
        assert parsed["last_event_id"] is None
        assert parsed["last_event_occurred_at"] is None

    @pytest.mark.asyncio
    async def test_save_logs_debug_on_success(self) -> None:
        """save() logs a debug message on successful write."""
        svc, _, logger = _make_service()
        checkpoint = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
            created_at=FIXED_CHECKPOINT_TIME,
        )

        await svc.save(checkpoint)

        debug_calls = [str(c) for c in logger.debug.call_args_list]
        assert any("Saved checkpoint" in c for c in debug_calls)

    @pytest.mark.asyncio
    async def test_save_sets_checkpoint_saved_at_gauge_from_state_timestamp(
        self,
    ) -> None:
        """save() publishes checkpoint freshness from persisted state timestamps."""
        metrics = MagicMock()
        svc, _, _ = _make_service(metrics=metrics)
        checkpoint = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
            created_at=FIXED_CHECKPOINT_TIME,
        )

        await svc.save(checkpoint)

        metrics.set_gauge.assert_called_once_with(
            "bioetl_checkpoint_saved_at_seconds",
            FIXED_CHECKPOINT_TIME.timestamp(),
            {"pipeline": "my_composite"},
        )

    @pytest.mark.asyncio
    async def test_save_raises_checkpoint_conflict_on_os_error(self) -> None:
        """save() wraps OSError as CheckpointConflictError."""
        svc, storage, _ = _make_service()
        storage.write_atomic.side_effect = OSError("disk full")
        checkpoint = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
            created_at=FIXED_CHECKPOINT_TIME,
        )

        with pytest.raises(CheckpointConflictError):
            await svc.save(checkpoint)

    @pytest.mark.asyncio
    async def test_save_raises_checkpoint_conflict_on_storage_error(self) -> None:
        """save() wraps StorageError as CheckpointConflictError."""
        svc, storage, _ = _make_service()
        storage.write_atomic.side_effect = StorageError("backend unavailable")
        checkpoint = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
            created_at=FIXED_CHECKPOINT_TIME,
        )

        with pytest.raises(CheckpointConflictError):
            await svc.save(checkpoint)

    @pytest.mark.asyncio
    async def test_save_logs_error_before_raising(self) -> None:
        """save() logs an error message before re-raising as CheckpointConflictError."""
        svc, storage, logger = _make_service()
        storage.write_atomic.side_effect = OSError("permission denied")
        checkpoint = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
            created_at=FIXED_CHECKPOINT_TIME,
        )

        with pytest.raises(CheckpointConflictError):
            await svc.save(checkpoint)

        error_calls = [str(c) for c in logger.error.call_args_list]
        assert any("Failed to save checkpoint" in c for c in error_calls)


# ---------------------------------------------------------------------------
# 6. delete
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDelete:
    """Tests for delete() checkpoint removal."""

    @pytest.mark.asyncio
    async def test_delete_calls_storage_delete(self) -> None:
        """delete() delegates to storage.delete with the correct filename."""
        svc, storage, _ = _make_service(composite_name="my_composite", run_id="run-001")
        storage.delete.return_value = True

        await svc.delete()

        storage.delete.assert_called_once_with("composite_my_composite_run-001.json")

    @pytest.mark.asyncio
    async def test_delete_logs_info_when_deleted(self) -> None:
        """delete() logs an info message when the file is deleted."""
        svc, storage, logger = _make_service()
        storage.delete.return_value = True

        await svc.delete()

        info_calls = [str(c) for c in logger.info.call_args_list]
        assert any("Deleted checkpoint" in c for c in info_calls)

    @pytest.mark.asyncio
    async def test_delete_does_not_log_when_nothing_deleted(self) -> None:
        """delete() does not log info when storage.delete returns False."""
        svc, storage, logger = _make_service()
        storage.delete.return_value = False

        await svc.delete()

        info_calls = [str(c) for c in logger.info.call_args_list]
        assert not any("Deleted checkpoint" in c for c in info_calls)


# ---------------------------------------------------------------------------
# 7. list_all
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListAll:
    """Tests for list_all() checkpoint enumeration."""

    @pytest.mark.asyncio
    async def test_list_all_returns_storage_glob_results(self) -> None:
        """list_all() returns whatever storage.list_glob returns."""
        svc, storage, _ = _make_service(composite_name="my_composite")
        storage.list_glob.return_value = [
            "composite_my_composite_run-001.json",
            "composite_my_composite_run-002.json",
        ]

        result = await svc.list_all()

        assert result == [
            "composite_my_composite_run-001.json",
            "composite_my_composite_run-002.json",
        ]

    @pytest.mark.asyncio
    async def test_list_all_uses_correct_glob_pattern(self) -> None:
        """list_all() passes the correct glob pattern to storage."""
        svc, storage, _ = _make_service(composite_name="my_composite")
        storage.list_glob.return_value = []

        await svc.list_all()

        storage.list_glob.assert_called_once_with("composite_my_composite_*.json")

    @pytest.mark.asyncio
    async def test_list_all_returns_empty_when_no_checkpoints(self) -> None:
        """list_all() returns empty list when no checkpoints exist."""
        svc, storage, _ = _make_service()
        storage.list_glob.return_value = []

        result = await svc.list_all()

        assert result == []

    # ---------------------------------------------------------------------------
    # 8. Stale Checkpoint Detection
    # ---------------------------------------------------------------------------

    @pytest.mark.unit
    class TestStaleCheckpointDetection:
        """Tests for _warn_if_checkpoint_stale staleness detection."""

    @pytest.mark.asyncio
    async def test_stale_checkpoint_emits_warning(self) -> None:
        """Resuming a 48h-old checkpoint emits a staleness warning."""
        storage = _make_storage()
        logger = _make_logger()
        current_time = datetime(2024, 6, 3, 12, 0, tzinfo=UTC)
        old_time = current_time - timedelta(hours=48)
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
            state=CompositePipelineState.ENRICHING,
            created_at=old_time,
            updated_at=old_time,
            seed_completed=True,
            composite_run_identity="run-001",
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())
        storage.list_glob.return_value = ["composite_my_composite_run-001.json"]

        svc = CompositeCheckpointService(
            CompositeCheckpointServiceContext(
                composite_name="my_composite",
                run_id="run-001",
                storage=storage,
                logger=logger,
                resume=True,
                clock=FixedClock(current_time),
            )
        )
        await svc.load()

        warning_calls = [str(c) for c in logger.warning.call_args_list]
        assert any("stale" in c.lower() for c in warning_calls)

    @pytest.mark.asyncio
    async def test_fresh_checkpoint_no_staleness_warning(self) -> None:
        """A 1h-old checkpoint does not trigger staleness warning."""
        storage = _make_storage()
        logger = _make_logger()
        current_time = datetime(2024, 6, 3, 12, 0, tzinfo=UTC)
        recent_time = current_time - timedelta(hours=1)
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
            state=CompositePipelineState.ENRICHING,
            created_at=recent_time,
            updated_at=recent_time,
            seed_completed=True,
            composite_run_identity="run-001",
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())
        storage.list_glob.return_value = ["composite_my_composite_run-001.json"]

        svc = CompositeCheckpointService(
            CompositeCheckpointServiceContext(
                composite_name="my_composite",
                run_id="run-001",
                storage=storage,
                logger=logger,
                resume=True,
                clock=FixedClock(current_time),
            )
        )
        await svc.load()

        warning_calls = [str(c) for c in logger.warning.call_args_list]
        assert not any("stale" in c.lower() for c in warning_calls)

    @pytest.mark.asyncio
    async def test_staleness_check_disabled_with_zero_threshold(self) -> None:
        """Setting threshold to 0 disables staleness warnings."""
        storage = _make_storage()
        logger = _make_logger()
        current_time = datetime(2024, 6, 3, 12, 0, tzinfo=UTC)
        old_time = current_time - timedelta(hours=48)
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
            state=CompositePipelineState.ENRICHING,
            created_at=old_time,
            updated_at=old_time,
            seed_completed=True,
            composite_run_identity="run-001",
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())
        storage.list_glob.return_value = ["composite_my_composite_run-001.json"]

        svc = CompositeCheckpointService(
            CompositeCheckpointServiceContext(
                composite_name="my_composite",
                run_id="run-001",
                storage=storage,
                logger=logger,
                resume=True,
                stale_checkpoint_threshold_hours=0,
                clock=FixedClock(current_time),
            )
        )
        await svc.load()

        warning_calls = [str(c) for c in logger.warning.call_args_list]
        assert not any("stale" in c.lower() for c in warning_calls)

    def test_default_threshold_is_24_hours(self) -> None:
        """Default stale threshold is 24 hours."""
        assert (
            CompositeCheckpointService._DEFAULT_STALE_THRESHOLD_HOURS
            == pytest.approx(24.0)
        )

    @pytest.mark.asyncio
    async def test_resume_staleness_check_requires_clock_when_reference_time_missing(
        self,
    ) -> None:
        """Replay-critical stale-checks must not fall back to wall-clock time."""
        storage = _make_storage()
        logger = _make_logger()
        old_time = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
        state_data = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
            state=CompositePipelineState.ENRICHING,
            created_at=old_time,
            updated_at=old_time,
            seed_completed=True,
            composite_run_identity="run-001",
        )
        storage.exists.return_value = True
        storage.read.return_value = json.dumps(state_data.to_dict())
        storage.list_glob.return_value = ["composite_my_composite_run-001.json"]

        svc = CompositeCheckpointService(
            CompositeCheckpointServiceContext(
                composite_name="my_composite",
                run_id="run-001",
                storage=storage,
                logger=logger,
                resume=True,
                clock=None,
            )
        )

        with pytest.raises(RuntimeError, match="ClockPort is required"):
            await svc.load()


# ---------------------------------------------------------------------------
# 9. Delete Orphaned
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeleteOrphaned:
    """Tests for delete_orphaned() orphan cleanup."""

    @pytest.mark.asyncio
    async def test_deletes_other_run_checkpoints(self) -> None:
        """delete_orphaned() deletes checkpoints from other runs."""
        svc, storage, _ = _make_service(composite_name="my_composite", run_id="run-002")
        storage.list_glob.return_value = [
            "composite_my_composite_run-001.json",
            "composite_my_composite_run-002.json",
        ]
        storage.delete.return_value = True

        deleted = await svc.delete_orphaned()

        assert deleted == 1
        storage.delete.assert_called_once_with("composite_my_composite_run-001.json")

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_orphans(self) -> None:
        """delete_orphaned() returns 0 when only current checkpoint exists."""
        svc, storage, _ = _make_service(composite_name="my_composite", run_id="run-001")
        storage.list_glob.return_value = [
            "composite_my_composite_run-001.json",
        ]

        deleted = await svc.delete_orphaned()

        assert deleted == 0

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_checkpoints(self) -> None:
        """delete_orphaned() returns 0 when no checkpoints exist."""
        svc, storage, _ = _make_service()
        storage.list_glob.return_value = []

        deleted = await svc.delete_orphaned()

        assert deleted == 0
