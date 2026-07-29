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
"""Unit tests for full-universe historical replay claim policy."""

from __future__ import annotations

import pytest

from bioetl.application.services.control_plane.replay.historical_universe_policy import (
    build_authoritative_truth_surface,
    build_durable_coverage_claim,
    build_governed_full_corpus_gate,
    build_universal_claim,
)
from bioetl.application.services.control_plane.replay.historical_universe_service import (
    HistoricalReplayUniverseInventorySnapshot,
    HistoricalReplayUniverseRecord,
)


pytestmark = pytest.mark.unit


def _record(*, durable_evidence_coverage: bool) -> HistoricalReplayUniverseRecord:
    return HistoricalReplayUniverseRecord(
        manifest_id="archived-manifest",
        run_id="archived-run",
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        execution_context="isolated",
        certification_status="already_certified",
        replay_occurrence_kind="historical_source_replay_certified_parent",
        blocking_reasons=(),
        universe_origin="external_archived",
        evidence_residency="authoritative_archive",
        durable_evidence_coverage=durable_evidence_coverage,
        source_pack_ref="archive-pack",
    )


def test_governed_full_corpus_gate_blocks_universal_claim_without_durable_evidence() -> (
    None
):
    inventory = HistoricalReplayUniverseInventorySnapshot(
        records=(_record(durable_evidence_coverage=False),)
    )

    universal_claim = build_universal_claim(inventory)
    durable_claim = build_durable_coverage_claim(inventory)
    gate = build_governed_full_corpus_gate(
        authoritative_truth_surface=build_authoritative_truth_surface(),
        universal_claim=universal_claim,
        durable_claim=durable_claim,
    )

    assert universal_claim["claimed"] is True
    assert durable_claim["claimed"] is False
    assert gate["required_claims"] == {
        "universal_claim": True,
        "durable_evidence_coverage_claim": False,
    }
    assert gate["satisfied"] is False
    assert gate["verdict"] == "gate_blocked"
