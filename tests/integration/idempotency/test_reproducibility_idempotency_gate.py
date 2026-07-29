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
"""Campaign idempotency gate for tracked fixture replay."""

from __future__ import annotations

import json
import platform
from pathlib import Path

import pytest

from tests.integration._consolidation_suite_support import (
    run_tracked_fixture_replay_pair,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.no_api,
    pytest.mark.skipif(
        "microsoft" in platform.release().lower(),
        reason="Skipped on WSL due to asyncio teardown on cloud-mounted storage",
    ),
]


async def test_consolidation_idempotency_contract_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        first_manifest,
        second_manifest,
        first_effective,
        second_effective,
        _,
        _,
    ) = await run_tracked_fixture_replay_pair(
        tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert first_manifest["run_id"] != second_manifest["run_id"]
    assert first_manifest["run_type"] == second_manifest["run_type"] == "incremental"
    assert first_manifest["provider"] == second_manifest["provider"] == "chembl"
    assert first_manifest["entity"] == second_manifest["entity"] == "activity"
    assert first_manifest["launch_context"]["exact_replay"] is True
    assert second_manifest["launch_context"]["exact_replay"] is True

    source_refs_first = first_manifest.get("source_refs")
    source_refs_second = second_manifest.get("source_refs")
    assert isinstance(source_refs_first, list) and source_refs_first
    assert isinstance(source_refs_second, list) and source_refs_second
    assert len(source_refs_first) == len(source_refs_second) == 1
    assert (
        source_refs_first[0].get("provider")
        == source_refs_second[0].get("provider")
        == "chembl"
    )
    assert (
        source_refs_first[0].get("entity")
        == source_refs_second[0].get("entity")
        == "activity"
    )
    assert (
        source_refs_first[0].get("pipeline_name")
        == source_refs_second[0].get("pipeline_name")
        == "chembl_activity"
    )
    assert (
        source_refs_first[0]["input_snapshots"]
        == source_refs_second[0]["input_snapshots"]
    )

    first_snapshot = source_refs_first[0]["input_snapshots"][0]
    second_snapshot = source_refs_second[0]["input_snapshots"][0]
    assert first_snapshot["snapshot_id"] == second_snapshot["snapshot_id"]
    assert first_snapshot["content_hash"] == second_snapshot["content_hash"]
    assert first_snapshot["query_fingerprint"] == second_snapshot["query_fingerprint"]

    assert (
        first_manifest["code_provenance"]["effective_config_artifact_id"]
        == second_manifest["code_provenance"]["effective_config_artifact_id"]
    )
    assert (
        first_effective["artifact_id"]
        == second_effective["artifact_id"]
        == first_manifest["code_provenance"]["effective_config_artifact_id"]
    )

    contract_path = (
        tmp_path / "reports" / "reproducibility" / "tracked_fixture_idempotency.json"
    )
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(
        json.dumps(
            {
                "mode": "idempotent_rerun",
                "source_snapshot_id": first_snapshot["snapshot_id"],
                "run_ids": [
                    first_manifest["run_id"],
                    second_manifest["run_id"],
                ],
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
