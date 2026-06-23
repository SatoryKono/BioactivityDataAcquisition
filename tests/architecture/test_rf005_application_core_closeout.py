"""Closeout ratchets for RF-005 application/core duplication reduction."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

BATCH_EXECUTION_SHARED_CONTRACT_USERS: dict[str, set[str]] = {
    "src/bioetl/application/core/batch_executor_helpers.py": {
        "bioetl.application.core.batch_execution.contracts",
    },
    "src/bioetl/application/core/batch_executor_protocols.py": {
        "bioetl.application.core.batch_execution.contracts",
    },
    "src/bioetl/application/core/batch_execution/lifecycle.py": {
        "bioetl.application.core.batch_execution.contracts",
    },
    "src/bioetl/application/core/batch_execution/run_service.py": {
        "bioetl.application.core.batch_execution.contracts",
    },
    "src/bioetl/application/core/batch_execution/state_service.py": {
        "bioetl.application.core.batch_execution.contracts",
    },
}

APPLICATION_CORE_SHARED_FAILURE_POLICY_USERS: dict[str, set[str]] = {
    "src/bioetl/application/core/batch_executor.py": {
        "bioetl.application.core.batch_runtime_failure_policy",
    },
    "src/bioetl/application/core/batch_execution/run_service.py": {
        "bioetl.application.core.batch_runtime_failure_policy",
    },
    "src/bioetl/application/core/batch_processing_support.py": {
        "bioetl.application.core.batch_runtime_failure_policy",
    },
}

BATCH_PROCESSING_SUPPORT_USERS: dict[str, set[str]] = {
    "src/bioetl/application/core/batch_processing_service.py": {
        "bioetl.application.core.batch_processing_support",
    },
}

POSTRUN_SHARED_POLICY_USERS: dict[str, set[str]] = {
    "src/bioetl/application/core/postrun/dq_report_orchestrator.py": {
        "bioetl.application.core.postrun._failure_policy",
    },
    "src/bioetl/application/core/postrun/metadata_version_resolver.py": {
        "bioetl.application.core.postrun._failure_policy",
    },
}


def _imported_modules(relative_path: str) -> set[str]:
    path = ROOT / relative_path
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("relative_path", "required_modules"),
    list(BATCH_EXECUTION_SHARED_CONTRACT_USERS.items()),
)
def test_batch_execution_family_stays_routed_through_shared_contracts(
    relative_path: str,
    required_modules: set[str],
) -> None:
    """RF-005 should keep shared execution contracts in one narrow module."""
    imported_modules = _imported_modules(relative_path)
    missing_modules = required_modules - imported_modules
    assert not missing_modules, (
        f"{relative_path} no longer imports shared batch_execution contracts:\n"
        + "\n".join(sorted(missing_modules))
    )


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("relative_path", "required_modules"),
    list(POSTRUN_SHARED_POLICY_USERS.items()),
)
def test_postrun_family_stays_routed_through_shared_failure_policy(
    relative_path: str,
    required_modules: set[str],
) -> None:
    """RF-005 second family should keep strict/warning policy centralized."""
    imported_modules = _imported_modules(relative_path)
    missing_modules = required_modules - imported_modules
    assert not missing_modules, (
        f"{relative_path} no longer imports shared postrun failure policy:\n"
        + "\n".join(sorted(missing_modules))
    )


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("relative_path", "required_modules"),
    list(APPLICATION_CORE_SHARED_FAILURE_POLICY_USERS.items()),
)
def test_application_core_slice_stays_routed_through_shared_failure_policy(
    relative_path: str,
    required_modules: set[str],
) -> None:
    """RF-005 bounded slice should keep runtime failure tuples centralized."""
    imported_modules = _imported_modules(relative_path)
    missing_modules = required_modules - imported_modules
    assert not missing_modules, (
        f"{relative_path} no longer imports shared application/core failure policy:\n"
        + "\n".join(sorted(missing_modules))
    )


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("relative_path", "required_modules"),
    list(BATCH_PROCESSING_SUPPORT_USERS.items()),
)
def test_batch_processing_family_stays_routed_through_support_service(
    relative_path: str,
    required_modules: set[str],
) -> None:
    """RF-005 bounded slice should keep processing choreography centralized."""
    imported_modules = _imported_modules(relative_path)
    missing_modules = required_modules - imported_modules
    assert not missing_modules, (
        f"{relative_path} no longer imports shared batch-processing support module:\n"
        + "\n".join(sorted(missing_modules))
    )
