"""Architecture ratchet for deterministic test identity helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TARGETS = (
    "tests/helpers/metadata_fixtures.py",
    "tests/unit/application/core/test_batch_transformer.py",
    "tests/unit/application/services/run_manifest_test_support.py",
    "tests/unit/application/services/test_run_ledger_service.py",
    "tests/unit/application/services/test_run_manifest_inspection_service.py",
    "tests/unit/application/services/test_metadata_assemblers.py",
    "tests/unit/application/services/test_metadata_assemblers_helpers.py",
    "tests/unit/application/services/control_plane/test_historical_replay_certification_service.py",
    "tests/unit/application/services/control_plane/test_historical_replay_closure_service.py",
    "tests/unit/application/services/control_plane/test_historical_replay_corpus_service.py",
    "tests/unit/application/services/control_plane/test_historical_replay_universe_service.py",
    "tests/unit/domain/test_pipeline_context.py",
    "tests/unit/interfaces/http/test_health_server_control_plane_identity.py",
    "tests/testing_support/bronze_writer.py",
    "tests/performance/test_batching_performance.py",
    "tests/integration/ci/test_reproducibility_contract_suite.py",
    "tests/integration/test_pubchem_pipeline.py",
    "tests/integration/test_uniprot_pipeline.py",
    "tests/integration/workflow/test_workflow_runner_service.py",
    "tests/e2e/test_advanced_scenarios_e2e.py",
    "tests/e2e/test_advanced_scenarios_harness_contracts.py",
    "tests/e2e/test_pipeline_with_schema_drift_e2e.py",
    "tests/e2e/test_resilience_scenarios_e2e.py",
)

ADVANCED_HARNESS_CONTEXT_TARGETS = (
    "tests/e2e/test_advanced_scenarios_e2e.py",
    "tests/e2e/test_advanced_scenarios_harness_contracts.py",
)


@pytest.mark.architecture
def test_high_signal_test_surfaces_use_deterministic_identity_helpers() -> None:
    for relative_path in TARGETS:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "tests.helpers.deterministic_ids" in text, (
            f"{relative_path} must import tests.helpers.deterministic_ids"
        )
        assert "uuid4(" not in text, (
            f"{relative_path} must avoid incidental uuid4() identities in replay- or "
            "golden-sensitive test scaffolding"
        )


@pytest.mark.architecture
def test_advanced_harness_e2e_uses_replay_stable_contexts() -> None:
    for relative_path in ADVANCED_HARNESS_CONTEXT_TARGETS:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "create_test_context(" not in text, (
            f"{relative_path} must not call occurrence-safe create_test_context() "
            "for harness-mode replay-sensitive runs"
        )
        assert "create_test_context," not in text, (
            f"{relative_path} must not import occurrence-safe create_test_context() "
            "for harness-mode replay-sensitive runs"
        )

    advanced_text = (ROOT / "tests/e2e/test_advanced_scenarios_e2e.py").read_text(
        encoding="utf-8"
    )
    assert "build_e2e_run_context" in advanced_text
    assert "deterministic_uuid_from_callsite" in advanced_text
    assert "create_deterministic_test_context" not in advanced_text


@pytest.mark.architecture
def test_deterministic_id_helper_module_exposes_typed_and_callsite_wrappers() -> None:
    text = (ROOT / "tests/helpers/deterministic_ids.py").read_text(encoding="utf-8")

    for token in (
        "def deterministic_uuid_string(",
        "def deterministic_uuid_string_from_callsite(",
        "def deterministic_run_uuid(",
        "def deterministic_run_uuid_from_callsite(",
        "def deterministic_batch_uuid(",
        "def deterministic_batch_uuid_from_callsite(",
    ):
        assert token in text, f"deterministic helper surface missing {token}"
