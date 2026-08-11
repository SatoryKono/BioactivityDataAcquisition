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
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from scripts.engineering.qa import report_provider_contract_drift as report


pytestmark = pytest.mark.unit


def test_main_accepts_dispatcher_argv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "provider-contract-drift.json"
    payload = {
        "totals": {"max_severity": "benign"},
        "reports": [],
    }
    monkeypatch.setattr(report, "build_provider_contract_drift_report", lambda: payload)

    result = report.main(["--output", str(output), "--fail-on", "never"])

    assert result == 0
    assert json.loads(output.read_text(encoding="utf-8")) == payload


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
