# pyright: reportArgumentType=false
"""Bind 26 concrete untraced REQ-* IDs to existing tests (#9805).

REQ-DATA-007 REQ-DATA-008 REQ-DELTA-001 REQ-DEP-001 REQ-DEP-002 REQ-DX-004
REQ-ENV-003 REQ-GOV-001 REQ-GOV-002 REQ-GOV-003 REQ-GOV-004 REQ-GOV-008
REQ-GOV-009 REQ-GOV-010 REQ-GOV-012 REQ-LOAD-001 REQ-LOAD-002
REQ-PYTHON-001 REQ-PYTHON-002 REQ-PYTHON-003 REQ-STACK-001 REQ-STACK-002
REQ-STACK-003 REQ-STACK-004 REQ-TEST-003 REQ-TEST-004
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]

_SURFACES = (
    ROOT / "tests/unit/infrastructure/test_storage_factory.py",  # REQ-DATA-007
    ROOT / "tests/architecture/test_write_mode_types.py",  # REQ-DATA-008, REQ-GOV-009
    ROOT / "tests/architecture/test_layer_dependencies.py",  # REQ-DELTA-001
    ROOT / "tests/unit/repo_backed/scripts/ai/agent_tools/test_install_contracts.py",  # REQ-DEP-001
    ROOT / "tests/architecture/test_github_actions_runtime_policy.py",  # REQ-DEP-002
    ROOT / "tests/architecture/test_docker_runtime_contracts.py",  # REQ-DX-004
    ROOT / "tests/architecture/test_gitignore_secret_and_agents_policy.py",  # REQ-ENV-003
    ROOT / "tests/architecture/test_regression_metrics.py",  # REQ-GOV-001, REQ-PYTHON-001
    ROOT / "tests/architecture/test_config_golden_master.py",  # REQ-GOV-002
    ROOT / "tests/integration/idempotency/test_reproducibility_idempotency_gate.py",  # REQ-GOV-003
    ROOT / "tests/architecture/test_integration_vcr_policy.py",  # REQ-GOV-004
    ROOT / "tests/architecture/test_import_linter_workflow.py",  # REQ-GOV-008
    ROOT / "tests/security/test_structured_logging_redaction.py",  # REQ-GOV-010
    ROOT / "tests/architecture/test_quality_debt_scorecard.py",  # REQ-GOV-012
    ROOT / "tests/unit/application/core/test_checkpoint_manager.py",  # REQ-LOAD-001
    ROOT / "tests/architecture/test_force_full_scan_publication.py",  # REQ-LOAD-002
    ROOT / "tests/architecture/test_non_chembl_json_field_typing_policy.py",  # REQ-PYTHON-002/003
    ROOT / "tests/architecture/test_di_compliance.py",  # REQ-STACK-001
    ROOT / "tests/unit/infrastructure/adapters/test_sync_base.py",  # REQ-STACK-002
    ROOT / "tests/unit/domain/test_public_api_facade.py",  # REQ-STACK-003
    ROOT / "tests/architecture/test_code_formatting.py",  # REQ-STACK-004, REQ-PYTHON-001
    ROOT / "tests/architecture/test_vcr_cassette_freshness_policy.py",  # REQ-TEST-003
    ROOT / "tests/helpers/vcr_config.py",  # REQ-TEST-004
)


def test_concrete_untraced_req_surfaces_exist() -> None:
    missing = [path.as_posix() for path in _SURFACES if not path.is_file()]
    assert not missing, f"REQ binding surfaces missing: {missing}"
