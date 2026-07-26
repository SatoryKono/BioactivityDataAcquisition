"""Architecture tests for mutation-testing rollout policy."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.architecture._test_matrix_policy_support import (
    ROOT,
    WORKFLOWS_DIR,
    load_matrix,
)


@pytest.mark.architecture
class TestMutationTestingRollout:
    """Validate mutation-testing matrix stays aligned with workflow reality."""

    def test_mutation_matrix_matches_current_workflow_contract(self) -> None:
        matrix = load_matrix()
        mutation = matrix.get("mutation_testing", {})
        workflow = (WORKFLOWS_DIR / "mutation-testing.yml").read_text(encoding="utf-8")

        assert mutation.get("enabled") is True
        assert mutation.get("workflow_present") is True
        assert mutation.get("ci_gate_mode") in {"partial", "full"}
        assert mutation["targets"]["domain"]["min_score"] == 70
        assert mutation["targets"]["domain"]["enforced"] is True
        assert mutation["targets"]["application_control_plane"]["min_score"] == 60
        assert mutation["targets"]["application_control_plane"]["enforced"] is True
        assert mutation["targets"]["application_export_manifests"]["min_score"] == 60
        assert mutation["targets"]["application_export_manifests"]["enforced"] is True
        assert mutation["targets"]["application_workflow_runner"]["min_score"] == 60
        assert mutation["targets"]["application_workflow_runner"]["enforced"] is True
        assert mutation["targets"]["application"]["min_score"] == 60
        assert mutation["targets"]["application"]["enforced"] is False

        assert "paths_to_mutate: src/bioetl/domain/" in workflow
        assert "src/bioetl/application/services/control_plane/" in workflow
        assert "tests/unit/application/services/control_plane/" in workflow
        assert "src/bioetl/application/services/export_manifests.py" in workflow
        assert "src/bioetl/application/services/workflow_runner_service.py" in workflow
        assert "tests/unit/application/services/" in workflow
        assert "MUTATION_SCORE_THRESHOLD" in workflow
        assert 'config["source_paths"]' in workflow
        assert 'config["pytest_add_cli_args_test_selection"]' in workflow
        assert "          mutmut run\n" in workflow
        assert "--paths-to-mutate=" not in workflow
        assert "--tests-dir=" not in workflow
        assert (
            "mutmut run --paths-to-mutate=src/bioetl/domain/ --tests-dir=tests/ || true"
            not in workflow
        )
        assert (
            "Mutation workflow produced zero mutants; treating this as a broken gate."
            in workflow
        )
        assert "mutmut export-cicd-stats" in workflow
        assert "mutmut-cicd-stats.json" in workflow
        assert "Invalid mutmut CI/CD stats" in workflow
        assert "--paths-to-mutate=src/bioetl/application/" not in workflow
        assert mutation.get("ci_gate_mode") == "partial"

    def test_mutation_rollout_ledger_tracks_partial_application_target(self) -> None:
        matrix = load_matrix()
        mutation = matrix.get("mutation_testing", {})
        ledger_path = ROOT / mutation["governance_ledger_location"]
        ledger = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))

        assert ledger["policy_scope"] == "mutation_testing_rollout"
        assert (
            ledger["source_of_truth"]["matrix_path"]
            == "configs/quality/test_matrix.yaml"
        )
        assert ledger["backlog_reference"].endswith("/issues/3410")

        entries = {entry["target"]: entry for entry in ledger["entries"]}
        assert set(entries) == set(mutation["targets"])

        for target, target_policy in mutation["targets"].items():
            entry = entries[target]
            expected_status = "enforced" if target_policy["enforced"] else "staged"
            assert entry["status"] == expected_status
            assert entry["min_score"] == target_policy["min_score"]
            assert entry["owner"]
            if target_policy["enforced"]:
                assert entry["paths_to_mutate"] == target_policy["paths_to_mutate"]
                assert entry["tests_dir"] == target_policy["tests_dir"]
            assert entry["current_evidence_paths"]
            assert entry["artifact_paths"]
            for relative_path in (
                entry["current_evidence_paths"] + entry["artifact_paths"]
            ):
                assert (ROOT / Path(relative_path)).exists(), (
                    f"mutation rollout ledger path is missing for {target}: "
                    f"{relative_path}"
                )

            if entry["status"] == "staged":
                assert entry["blocking_classification"]
                assert entry["issue"].startswith("#")
                assert entry["last_reviewed"].startswith("2026-")
                assert entry["target_resolution_date"].startswith("2026-")
                assert entry["next_step"]
                assert entry["promotion_criteria"]
