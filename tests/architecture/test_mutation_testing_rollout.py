"""Architecture tests for mutation-testing rollout policy."""

from __future__ import annotations

import pytest

from tests.architecture._test_matrix_policy_support import WORKFLOWS_DIR, load_matrix


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
        assert mutation["targets"]["application"]["min_score"] == 60
        assert mutation["targets"]["application"]["enforced"] is False

        assert "mutmut run --paths-to-mutate=src/bioetl/domain/" in workflow
        assert "THRESHOLD = 70.0" in workflow
        assert "--paths-to-mutate=src/bioetl/application/" not in workflow
        assert mutation.get("ci_gate_mode") == "partial"
