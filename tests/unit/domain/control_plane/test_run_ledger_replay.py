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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for deterministic run-ledger replay projection."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.control_plane._run_ledger_replay_policy import (
    PASS_THROUGH_EVENT_TYPES,
    STAGE_COMPLETION_UPDATES,
    TERMINAL_STATES,
)
from bioetl.domain.control_plane.run_ledger import (
    ARTIFACT_PUBLISHED_EVENT,
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
    COMPOSITE_ENRICHER_COMPLETED_EVENT,
    COMPOSITE_MERGE_COMPLETED_EVENT,
    COMPOSITE_RUN_LEDGER_STAGE_NAMES,
    DQ_POLICY_APPLIED_EVENT,
    INPUT_SNAPSHOT_PUBLISHED_EVENT,
    MANIFEST_CREATED_EVENT,
    ORDINARY_RUN_LEDGER_STAGE_NAMES,
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_SHUTDOWN_EVENT,
    RUN_STARTED_EVENT,
    RunLedgerEntry,
    STAGE_STARTED_EVENT,
    project_run_ledger_replay,
)
from bioetl.domain.types import RunID

TEST_RUN_ID = RunID(UUID("12345678-1234-5678-1234-567812345678"))


def _entry(
    *,
    entry_id: str,
    event_type: str,
    stage: str | None = None,
    occurred_at: datetime,
    details: dict[str, object] | None = None,
) -> RunLedgerEntry:
    return RunLedgerEntry(
        entry_id=entry_id,
        manifest_id="manifest-123",
        run_id=TEST_RUN_ID,
        event_type=event_type,
        stage=stage,
        occurred_at=occurred_at,
        details=details,
    )


@pytest.mark.unit
class TestRunLedgerReplayProjection:
    """Replay should produce deterministic coarse-grained checkpoint deltas."""

    def test_projects_completed_stages_and_terminal_state_in_append_order(self) -> None:
        projection = project_run_ledger_replay(
            [
                _entry(
                    entry_id="entry-1",
                    event_type="stage_completed",
                    stage="seed",
                    occurred_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
                ),
                _entry(
                    entry_id="entry-2",
                    event_type="stage_completed",
                    stage="dependencies",
                    occurred_at=datetime(2024, 6, 1, 10, 0, tzinfo=UTC),
                ),
                _entry(
                    entry_id="entry-3",
                    event_type="stage_completed",
                    stage="enrichment",
                    occurred_at=datetime(2024, 6, 1, 11, 0, tzinfo=UTC),
                ),
                _entry(
                    entry_id="entry-4",
                    event_type="run_finished",
                    occurred_at=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
                ),
            ]
        )

        assert projection.state == CompositePipelineState.COMPLETED
        assert projection.seed_completed is True
        assert projection.merge_completed is None
        assert projection.last_event_id == "entry-4"
        assert projection.last_event_occurred_at == datetime(
            2024,
            6,
            1,
            12,
            0,
            tzinfo=UTC,
        )
        assert projection.replayed_entry_count == 4

    def test_projects_merge_completion_without_fabricating_terminal_state(self) -> None:
        projection = project_run_ledger_replay(
            [
                _entry(
                    entry_id="entry-merge",
                    event_type="stage_completed",
                    stage="merge",
                    occurred_at=datetime(2024, 6, 1, 13, 0, tzinfo=UTC),
                )
            ]
        )

        assert projection.state == CompositePipelineState.MERGING
        assert projection.seed_completed is None
        assert projection.merge_completed is True
        assert projection.last_event_id == "entry-merge"

    @pytest.mark.parametrize(
        ("stage", "expected_state"),
        [
            ("dependencies", CompositePipelineState.DEPENDENCIES_COMPLETED),
            ("enrichment", CompositePipelineState.ENRICHMENT_COMPLETED),
        ],
    )
    def test_projects_intermediate_composite_stage_completion(
        self,
        stage: str,
        expected_state: CompositePipelineState,
    ) -> None:
        projection = project_run_ledger_replay(
            [
                _entry(
                    entry_id=f"entry-{stage}",
                    event_type="stage_completed",
                    stage=stage,
                    occurred_at=datetime(2024, 6, 1, 13, 0, tzinfo=UTC),
                )
            ]
        )

        assert projection.state == expected_state
        assert projection.last_event_id == f"entry-{stage}"

    def test_ignores_non_progress_events_except_for_watermark_advance(self) -> None:
        projection = project_run_ledger_replay(
            [
                _entry(
                    entry_id="entry-1",
                    event_type="run_started",
                    occurred_at=datetime(2024, 6, 1, 8, 0, tzinfo=UTC),
                ),
                _entry(
                    entry_id="entry-2",
                    event_type="run_shutdown",
                    occurred_at=datetime(2024, 6, 1, 8, 30, tzinfo=UTC),
                ),
            ]
        )

        assert projection.state is None
        assert projection.seed_completed is None
        assert projection.merge_completed is None
        assert projection.last_event_id == "entry-2"
        assert projection.replayed_entry_count == 2
        assert projection.projector_coverage_complete is True
        assert projection.unsupported_replay_entries == ()

    def test_empty_projection_has_no_state_delta(self) -> None:
        projection = project_run_ledger_replay([])

        assert projection.state is None
        assert projection.seed_completed is None
        assert projection.merge_completed is None
        assert projection.last_event_id is None
        assert projection.last_event_occurred_at is None
        assert projection.replayed_entry_count == 0

    def test_stage_events_are_canonicalized_on_entry_creation(self) -> None:
        entry = _entry(
            entry_id="entry-stage",
            event_type="stage_completed",
            stage=" Seed ",
            occurred_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
        )

        assert entry.stage == COMPOSITE_RUN_LEDGER_STAGE_NAMES[0]

    def test_non_stage_event_preserves_non_pipeline_stage_vocabulary(self) -> None:
        entry = _entry(
            entry_id="entry-artifact",
            event_type="artifact_published",
            stage="silver",
            occurred_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
        )

        assert entry.stage == "silver"

    def test_canonical_stage_names_include_ordinary_execution_baseline(self) -> None:
        assert ORDINARY_RUN_LEDGER_STAGE_NAMES == (
            "preflight",
            "prepare_medallion_layers",
            "execute_pipeline",
            "postrun",
            "checkpoint_finalize",
        )

    def test_replay_policy_stage_completion_updates_are_contract_frozen(self) -> None:
        assert STAGE_COMPLETION_UPDATES == {
            "seed": {
                "state": CompositePipelineState.SEED_COMPLETED,
                "seed_completed": True,
            },
            "dependencies": {
                "state": CompositePipelineState.DEPENDENCIES_COMPLETED,
            },
            "enrichment": {
                "state": CompositePipelineState.ENRICHMENT_COMPLETED,
            },
            "merge": {
                "state": CompositePipelineState.MERGING,
                "merge_completed": True,
            },
        }

    def test_replay_policy_event_type_sets_are_contract_frozen(self) -> None:
        assert PASS_THROUGH_EVENT_TYPES == frozenset(
            {
                ARTIFACT_PUBLISHED_EVENT,
                DQ_POLICY_APPLIED_EVENT,
                MANIFEST_CREATED_EVENT,
                RUN_SHUTDOWN_EVENT,
                RUN_STARTED_EVENT,
                STAGE_STARTED_EVENT,
            }
        )
        assert TERMINAL_STATES == {
            RUN_FAILED_EVENT: CompositePipelineState.FAILED,
            RUN_FINISHED_EVENT: CompositePipelineState.COMPLETED,
        }

    @pytest.mark.parametrize("event_type", sorted(PASS_THROUGH_EVENT_TYPES))
    def test_policy_pass_through_events_advance_watermark_only(
        self,
        event_type: str,
    ) -> None:
        projection = project_run_ledger_replay(
            [
                _entry(
                    entry_id=f"entry-{event_type}",
                    event_type=event_type,
                    occurred_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
                )
            ]
        )

        assert projection.state is None
        assert projection.seed_completed is None
        assert projection.merge_completed is None
        assert projection.completed_dependencies == frozenset()
        assert projection.completed_enrichers == frozenset()
        assert projection.merge_result is None
        assert projection.last_event_id == f"entry-{event_type}"
        assert projection.projector_coverage_complete is True

    def test_legacy_entry_payload_without_idempotency_key_deserializes(self) -> None:
        entry = RunLedgerEntry.from_dict(
            {
                "entry_id": "entry-legacy",
                "manifest_id": "manifest-123",
                "run_id": str(TEST_RUN_ID),
                "event_type": "run_started",
                "occurred_at": "2024-06-01T09:00:00+00:00",
            }
        )

        assert entry.idempotency_key is None
        assert entry.to_dict()["idempotency_key"] is None

    def test_entry_idempotency_key_is_trimmed_on_creation(self) -> None:
        entry = RunLedgerEntry(
            entry_id="entry-keyed",
            manifest_id="manifest-123",
            run_id=TEST_RUN_ID,
            event_type="run_started",
            occurred_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
            idempotency_key=" sha256:abc ",
        )

        assert entry.idempotency_key == "sha256:abc"

    def test_projects_rich_composite_payloads_deterministically(self) -> None:
        projection = project_run_ledger_replay(
            [
                _entry(
                    entry_id="entry-dependency",
                    event_type=COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
                    occurred_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
                    details={
                        "dependency_name": "chembl_molecule",
                        "pipeline_name": "chembl_molecule",
                        "status": "success",
                        "records_extracted": 8,
                        "records_silver": 7,
                        "duration_seconds": 1.5,
                    },
                ),
                _entry(
                    entry_id="entry-enricher",
                    event_type=COMPOSITE_ENRICHER_COMPLETED_EVENT,
                    occurred_at=datetime(2024, 6, 1, 9, 1, tzinfo=UTC),
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
                _entry(
                    entry_id="entry-merge",
                    event_type=COMPOSITE_MERGE_COMPLETED_EVENT,
                    occurred_at=datetime(2024, 6, 1, 9, 2, tzinfo=UTC),
                    details={
                        "records_merged": 10,
                        "records_enriched": 6,
                        "output_silver_path": "silver/composite/publication",
                    },
                ),
            ]
        )

        assert projection.completed_dependencies == frozenset({"chembl_molecule"})
        assert projection.dependency_results["chembl_molecule"].records_silver == 7
        assert projection.completed_enrichers == frozenset({"pubmed_publication"})
        assert projection.enrichment_results["pubmed_publication"].records_errored == 1
        assert projection.merge_completed is True
        assert projection.merge_result == {
            "output_silver_path": "silver/composite/publication",
            "records_enriched": 6,
            "records_merged": 10,
        }

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [(1, 1), (1.0, 1), ("1", 1), ("not-an-integer", 0)],
    )
    def test_replays_integer_fields_without_stringifying_json_numbers(
        self,
        raw_value: object,
        expected: int,
    ) -> None:
        projection = project_run_ledger_replay(
            [
                _entry(
                    entry_id="entry-dependency",
                    event_type=COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
                    occurred_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
                    details={
                        "dependency_name": "chembl_molecule",
                        "pipeline_name": "chembl_molecule",
                        "status": "success",
                        "records_extracted": raw_value,
                    },
                )
            ]
        )

        result = projection.dependency_results["chembl_molecule"]
        assert result.records_extracted == expected

    def test_projects_input_snapshot_publication_events_deterministically(self) -> None:
        projection = project_run_ledger_replay(
            [
                _entry(
                    entry_id="entry-snapshot-b",
                    event_type=INPUT_SNAPSHOT_PUBLISHED_EVENT,
                    occurred_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
                    details={
                        "snapshot_id": "snapshot-b",
                        "content_hash": "sha256:b",
                        "immutable_uri": "file:///bronze/b.jsonl",
                    },
                ),
                _entry(
                    entry_id="entry-snapshot-a",
                    event_type=INPUT_SNAPSHOT_PUBLISHED_EVENT,
                    occurred_at=datetime(2024, 6, 1, 9, 1, tzinfo=UTC),
                    details={
                        "snapshot_id": "snapshot-a",
                        "content_hash": "sha256:a",
                        "immutable_uri": "file:///bronze/a.jsonl",
                    },
                ),
            ]
        )

        assert [item["snapshot_id"] for item in projection.input_snapshots] == [
            "snapshot-a",
            "snapshot-b",
        ]

    def test_marks_projection_incomplete_for_unknown_replay_relevant_event_type(
        self,
    ) -> None:
        projection = project_run_ledger_replay(
            [
                _entry(
                    entry_id="entry-future",
                    event_type="future_resume_delta",
                    occurred_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
                )
            ]
        )

        assert projection.projector_coverage_complete is False
        assert projection.unsupported_replay_entries == (
            ("entry-future", "future_resume_delta", None),
        )

    def test_marks_projection_incomplete_for_non_composite_stage_completion(
        self,
    ) -> None:
        projection = project_run_ledger_replay(
            [
                _entry(
                    entry_id="entry-postrun",
                    event_type="stage_completed",
                    stage="postrun",
                    occurred_at=datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
                )
            ]
        )

        assert projection.projector_coverage_complete is False
        assert projection.unsupported_replay_entries == (
            ("entry-postrun", "stage_completed", "postrun"),
        )
