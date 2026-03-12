"""Unit tests for CompositeCheckpointService.

Covers load / save / delete / list_all async methods, filename format,
resume vs. fresh-start logic, warning on overwrite, error handling, and
CheckpointConflictError escalation.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from bioetl.application.composite.checkpoint.service import CompositeCheckpointService
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.composite.result import EnrichmentResult, SeedResult
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import CheckpointConflictError, StorageError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
) -> tuple[CompositeCheckpointService, MagicMock, MagicMock]:
    """Convenience factory — returns (service, storage_mock, logger_mock)."""
    s = storage if storage is not None else _make_storage()
    lg = logger if logger is not None else _make_logger()
    svc = CompositeCheckpointService(
        composite_name=composite_name,
        run_id=run_id,
        storage=s,
        logger=lg,
        resume=resume,
    )
    return svc, s, lg


def _serialized_state(
    composite_name: str = "my_composite",
    run_id: str = "run-001",
    state: CompositePipelineState = CompositePipelineState.SEED_COMPLETED,
    seed_completed: bool = True,
    with_seed_result: bool = True,
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
        "created_at": "2024-06-01T08:00:00+00:00",
        "updated_at": "2024-06-01T09:00:00+00:00",
    }
    return json.dumps(data)


def _enriched_serialized_state(
    composite_name: str = "my_composite",
    run_id: str = "run-001",
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
        svc, storage, _ = _make_service(
            composite_name="my_composite", run_id="run-001"
        )
        assert svc._checkpoint_filename == "composite_my_composite_run-001.json"

    def test_glob_pattern(self) -> None:
        """Glob pattern matches all run_ids for this composite."""
        svc, _, _ = _make_service(composite_name="my_composite")
        assert svc._glob_pattern() == "composite_my_composite_*.json"


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


# ---------------------------------------------------------------------------
# 3. load – resume mode (resume=True)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLoadResume:
    """Tests for load() with resume=True."""

    @pytest.mark.asyncio
    async def test_resume_loads_existing_checkpoint(self) -> None:
        """load(resume=True) reads and returns the existing checkpoint."""
        svc, storage, _ = _make_service(resume=True)
        content = _serialized_state(state=CompositePipelineState.SEED_COMPLETED)
        storage.exists.return_value = True
        storage.read.return_value = content

        state = await svc.load()

        assert state.state == CompositePipelineState.SEED_COMPLETED
        assert state.seed_completed is True

    @pytest.mark.asyncio
    async def test_resume_returns_fresh_when_no_checkpoint_exists(self) -> None:
        """load(resume=True) returns fresh state when no file is found."""
        svc, storage, _ = _make_service(resume=True)
        storage.exists.return_value = False
        storage.list_glob.return_value = []

        state = await svc.load()

        assert state.state == CompositePipelineState.NOT_STARTED

    @pytest.mark.asyncio
    async def test_resume_fallback_to_glob_when_exact_file_missing(self) -> None:
        """If exact filename missing, resume uses glob to find latest checkpoint."""
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

        state = await svc.load()

        # Should have loaded the older checkpoint via glob fallback
        assert state.state == CompositePipelineState.ENRICHING

    @pytest.mark.asyncio
    async def test_resume_handles_corrupted_json_gracefully(self) -> None:
        """Corrupted JSON during resume falls back to fresh state without raising."""
        svc, storage, _ = _make_service(resume=True)
        storage.exists.return_value = True
        storage.read.return_value = "NOT VALID JSON {"

        state = await svc.load()

        # Graceful degradation: returns fresh NOT_STARTED state
        assert state.state == CompositePipelineState.NOT_STARTED

    @pytest.mark.asyncio
    async def test_resume_handles_none_content_gracefully(self) -> None:
        """None returned by storage.read() during resume falls back to fresh state."""
        svc, storage, _ = _make_service(resume=True)
        storage.exists.return_value = True
        storage.read.return_value = None

        state = await svc.load()

        assert state.state == CompositePipelineState.NOT_STARTED


# ---------------------------------------------------------------------------
# 4. load – warns on overwrite (resume=False, existing checkpoint with progress)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLoadWarnOnOverwrite:
    """Tests for warning when resume=False and existing checkpoint has progress."""

    @pytest.mark.asyncio
    async def test_warns_when_existing_checkpoint_has_progress(self) -> None:
        """load(resume=False) warns if an existing checkpoint is resumable."""
        svc, storage, logger = _make_service(resume=False)
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
        fresh_json = json.dumps({
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
        })
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


# ---------------------------------------------------------------------------
# 5. save
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSave:
    """Tests for save() atomic write behaviour."""

    @pytest.mark.asyncio
    async def test_save_calls_write_atomic(self) -> None:
        """save() delegates to storage.write_atomic with the correct filename."""
        svc, storage, _ = _make_service(
            composite_name="my_composite", run_id="run-001"
        )
        checkpoint = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
            state=CompositePipelineState.ENRICHING,
            created_at=datetime.now(tz=UTC),
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
            created_at=datetime.now(tz=UTC),
        )

        await svc.save(checkpoint)

        content_arg = storage.write_atomic.call_args[0][1]
        parsed = json.loads(content_arg)
        assert parsed["composite_name"] == "my_composite"
        assert parsed["run_id"] == "run-001"

    @pytest.mark.asyncio
    async def test_save_logs_debug_on_success(self) -> None:
        """save() logs a debug message on successful write."""
        svc, storage, logger = _make_service()
        checkpoint = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
            created_at=datetime.now(tz=UTC),
        )

        await svc.save(checkpoint)

        debug_calls = [str(c) for c in logger.debug.call_args_list]
        assert any("Saved checkpoint" in c for c in debug_calls)

    @pytest.mark.asyncio
    async def test_save_raises_checkpoint_conflict_on_os_error(self) -> None:
        """save() wraps OSError as CheckpointConflictError."""
        svc, storage, _ = _make_service()
        storage.write_atomic.side_effect = OSError("disk full")
        checkpoint = CompositeCheckpointState(
            composite_name="my_composite",
            run_id="run-001",
            created_at=datetime.now(tz=UTC),
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
            created_at=datetime.now(tz=UTC),
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
            created_at=datetime.now(tz=UTC),
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
        svc, storage, _ = _make_service(
            composite_name="my_composite", run_id="run-001"
        )
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
