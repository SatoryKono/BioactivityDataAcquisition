from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from scripts.engineering.qa import report_provider_contract_drift as report


pytestmark = pytest.mark.unit


def test_build_provider_contract_drift_report_records_lfs_pointer_skips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay_module = ModuleType("tests.contract._provider_contract_replay")
    replay_module.PROVIDER_CONTRACT_REPLAY_PROBES = [
        SimpleNamespace(
            provider="chembl",
            probe="activity",
            cassette_rel_path="tests/contract/cassettes/chembl.yaml",
            interaction_index=0,
        )
    ]

    def _raise_skip(_case: object) -> dict[str, object]:
        raise pytest.skip.Exception("Git LFS pointer detected in cassette")

    replay_module.build_provider_contract_replay_report = _raise_skip
    monkeypatch.setitem(sys.modules, replay_module.__name__, replay_module)

    payload = report.build_provider_contract_drift_report()

    assert payload["source_posture"] == "vcr_replay_with_lfs_pointer_skips"
    assert payload["totals"]["skipped_probe_count"] == 1
    assert payload["totals"]["max_severity"] == "benign"
    row = payload["reports"][0]
    assert row["result"] == "skipped_due_to_lfs_pointer"
    assert "Git LFS pointer detected" in row["skip_reason"]
