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
# Documentation gates for deterministic identity governance.

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
ADR_014 = ROOT / "docs/02-architecture/decisions/ADR-014-deterministic-writes.md"
TESTING_GUIDE = ROOT / "docs/03-guides/testing.md"


def test_deterministic_identity_governance_docs_name_enforced_contracts() -> None:
    text = ADR_014.read_text(encoding="utf-8")
    required = {
        "tests/fixtures/golden/domain/deterministic_identity_v1.json",
        "configs/quality/runtime_uuid_seams.yaml",
        "test_runtime_uuid4_generation_seams_are_classified",
        "test_deterministic_identity_golden_contract_is_stable",
        "test_replay_critical_checkpoint_surfaces_do_not_call_wall_clock_directly",
        "ClockPort",
    }
    missing = sorted(token for token in required if token not in text)

    assert missing == []


def test_testing_guide_documents_wsl_governance_timeout_mitigation() -> None:
    text = TESTING_GUIDE.read_text(encoding="utf-8")
    required = {
        "mixed Windows + WSL mounted",
        "git-index-backed governance helpers",
        "environment-limited validation",
    }
    missing = sorted(token for token in required if token not in text)

    assert missing == []
