"""Workflow contract checks for SonarCloud CI gating."""

from pathlib import Path


def test_sonarcloud_workflow_avoids_secret_based_job_if() -> None:
    workflow = Path(".github/workflows/sonarcloud.yml").read_text(encoding="utf-8")

    assert "if: ${{ secrets.SONAR_TOKEN != '' }}" not in workflow
    assert "id: sonar-token" in workflow
    assert "steps.sonar-token.outputs.available == 'true'" in workflow
    assert "SONAR_TOKEN is not configured; skipping SonarCloud scan." in workflow
