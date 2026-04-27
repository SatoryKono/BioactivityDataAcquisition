"""Workflow contract checks for SonarCloud CI gating."""

from pathlib import Path


def test_sonarcloud_workflow_avoids_secret_based_job_if() -> None:
    workflow = Path(".github/workflows/sonarcloud.yml").read_text(encoding="utf-8")

    assert "if: ${{ secrets.SONAR_TOKEN != '' }}" not in workflow
    assert "id: sonar-token" in workflow
    assert "steps.sonar-token.outputs.available == 'true'" in workflow
    assert "SONAR_TOKEN is not configured; skipping SonarCloud scan." in workflow


def test_sonarcloud_workflow_passes_canonical_scan_scope() -> None:
    workflow = Path(".github/workflows/sonarcloud.yml").read_text(encoding="utf-8")

    assert "sonar.sources=src/bioetl" in workflow
    assert "sonar.inclusions=src/bioetl/**/*.py" in workflow
    assert "-Dsonar.sources=src/bioetl" in workflow
    assert "-Dsonar.inclusions=src/bioetl/**/*.py" in workflow


def test_sonarcloud_config_declares_scope_contract() -> None:
    content = Path("sonar-project.properties").read_text(encoding="utf-8")

    assert "sonar.sources=src/bioetl" in content
    assert "sonar.inclusions=src/bioetl/**/*.py" in content
