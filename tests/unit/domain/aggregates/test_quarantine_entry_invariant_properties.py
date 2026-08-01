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
"""Property-based invariant tests for the QuarantineEntry aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bioetl.domain.aggregates.quarantine_entry import (
    QuarantineEntry,
    QuarantineStatus,
)
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.types import BatchID, RunID
from tests.helpers.deterministic_ids import deterministic_uuid_value

pytestmark = [pytest.mark.hypothesis]

_TEXT = st.text(
    min_size=1,
    max_size=16,
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters="-_:",
    ),
)
_SCALAR = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-10_000, max_value=10_000),
    _TEXT,
)
_PAYLOAD = st.dictionaries(keys=_TEXT, values=_SCALAR, min_size=1, max_size=5)
_METADATA = st.dictionaries(keys=_TEXT, values=_SCALAR, min_size=0, max_size=4)


def _ts(offset_seconds: int = 0) -> datetime:
    return datetime(2026, 4, 24, tzinfo=UTC) + timedelta(seconds=offset_seconds)


def _run_id() -> RunID:
    return RunID(deterministic_uuid_value("hypothesis.quarantine_entry.run_id"))


def _batch_id() -> BatchID:
    return BatchID(deterministic_uuid_value("hypothesis.quarantine_entry.batch_id"))


def _create_entry(
    payload: dict[str, object],
    metadata: dict[str, object] | None = None,
) -> QuarantineEntry:
    return QuarantineEntry.create(
        pipeline_name="chembl_activity",
        error_code="SCHEMA_VIOLATION",
        payload=payload,
        run_id=_run_id(),
        batch_id=_batch_id(),
        created_at=_ts(0),
        metadata=metadata,
    )


class TestQuarantineEntryInvariantProperties:
    """Invariant-focused properties for QuarantineEntry value semantics."""

    @pytest.mark.hypothesis
    @settings(
        deadline=None,
        max_examples=30,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.differing_executors],
    )
    @given(payload=_PAYLOAD, metadata_a=_METADATA, metadata_b=_METADATA)
    def test_payload_hash_depends_only_on_payload(
        self,
        payload: dict[str, object],
        metadata_a: dict[str, object],
        metadata_b: dict[str, object],
    ) -> None:
        """Metadata must not perturb payload hashing."""
        first = _create_entry(payload, metadata_a)
        second = _create_entry(payload, metadata_b)

        assert first.payload_hash == second.payload_hash
        if metadata_a == metadata_b:
            assert first.entry_id == second.entry_id
        else:
            assert first.entry_id != second.entry_id
        assert first.status == QuarantineStatus.NEW
        assert second.status == QuarantineStatus.NEW

    @pytest.mark.hypothesis
    @settings(
        deadline=None,
        max_examples=30,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.differing_executors],
    )
    @given(
        payload=_PAYLOAD,
        metadata=_METADATA,
        start_review_first=st.booleans(),
        resolution=st.sampled_from(["ignored", "reprocessed", "expired"]),
    )
    def test_resolution_paths_are_terminal_and_consistent(
        self,
        payload: dict[str, object],
        metadata: dict[str, object],
        start_review_first: bool,
        resolution: str,
    ) -> None:
        """All supported resolution paths must end in a terminal, resolved state."""
        entry = _create_entry(payload, metadata)
        if start_review_first:
            entry.start_review()

        if resolution == "ignored":
            entry.mark_ignored(reason="known source defect", resolved_at=_ts(10))
            expected_status = QuarantineStatus.IGNORED
        elif resolution == "reprocessed":
            entry.mark_reprocessed(
                new_record_id="silver:replacement",
                resolved_at=_ts(10),
            )
            expected_status = QuarantineStatus.REPROCESSED
        else:
            entry.mark_expired(expired_at=_ts(10))
            expected_status = QuarantineStatus.EXPIRED

        assert entry.status == expected_status
        assert entry.is_resolved
        assert entry.resolution_info is not None
        assert entry.resolution_info.resolution_type == resolution
        assert entry.age_seconds == pytest.approx(10.0)

    @pytest.mark.hypothesis
    @settings(
        deadline=None,
        max_examples=30,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.differing_executors],
    )
    @given(payload=_PAYLOAD, metadata=_METADATA)
    def test_payload_and_metadata_accessors_are_defensive(
        self,
        payload: dict[str, object],
        metadata: dict[str, object],
    ) -> None:
        """Accessors must return detached top-level mappings."""
        entry = _create_entry(payload, metadata)

        payload_view = entry.payload
        metadata_view = entry.metadata
        payload_view["mutated"] = "outside"
        metadata_view["triage"] = "changed"

        assert "mutated" not in entry.payload
        assert "triage" not in entry.metadata

    def test_regression_terminal_entry_rejects_metadata_mutation(self) -> None:
        """Terminal entries must reject post-resolution metadata changes."""
        entry = _create_entry({"id": "bad-record"})
        entry.mark_ignored(reason="expected bad data", resolved_at=_ts(10))

        with pytest.raises(InvalidStateError, match="Cannot modify metadata"):
            entry.add_metadata("operator_note", "retry later")
