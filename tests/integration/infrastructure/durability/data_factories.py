"""Closed construction catalog for the S1 durability smoke.

``STORE_NAMES`` is the full set of concrete stores this scaffold assembles
for the groups named in issue #12106.
"""

from __future__ import annotations

STORE_NAMES: tuple[str, ...] = (
    "g1_bronze",
    "g1_silver",
    "g1_gold",
    "g2_quarantine",
    "g2_checkpoint",
    "g3_run_manifest",
    "g3_run_ledger",
    "g3_lineage",
    "g4_workflow_execution_state",
    "g4_workflow_manifest",
    "g4_workflow_ledger",
    "g4_workflow_transform_artifact",
    "g5_effective_config",
    "g5_contract_registry",
    "g5_historical_replay_universe",
    "g5_historical_replay_closure",
    "g5_archive",
    "g5_artifact_lifecycle",
    "g5_contract_evidence",
    "g5_provider_health",
    "g5_run_report",
)

RUN_REPORT_MARKER = "durability-s1-smoke"
CHILD_FAILURE_CODE = 7
