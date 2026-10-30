"""Executable root, path and error contracts for all five QM-07 seams."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest
import yaml

from scripts.engineering.quality import architecture_debt_reduction as reduction
from scripts.engineering.quality import architecture_debt_task_generation as tasks
from scripts.engineering.quality import architecture_quality_scorecard as quality
from scripts.engineering.quality import debt_scorecard as debt
from scripts.engineering.quality import exemptions_registry_paths as paths
from scripts.engineering.quality.exemptions_registry_access import (
    load_exemptions_registry,
)

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[3]
STAMP = datetime(2026, 10, 21, 12, 0)


def test_defaults_resolve_repository_from_external_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert reduction._project_root() == ROOT
    assert tasks._project_root() == ROOT
    assert quality.PROJECT_ROOT == ROOT
    assert debt._project_root() == ROOT
    assert paths.project_root() == ROOT
    assert reduction._default_plan_output_path(
        project_root=ROOT, generated_at=STAMP
    ) == (
        ROOT / "reports/quality/architecture_debt_execution_plan_2026-10-21-12-00.json"
    )
    assert tasks._default_output_path(project_root=ROOT, generated_at=STAMP) == (
        ROOT
        / "reports/quality/tasks_architecture_metric_exemptions_2026-10-21-12-00.json"
    )
    assert (
        quality.DEFAULT_OUTPUT
        == ROOT / "reports/quality/architecture-quality-scorecard.json"
    )
    assert (
        debt._resolve_scorecard_path() == ROOT / "configs/quality/debt_scorecard.yaml"
    )
    assert (
        paths.resolve_registry_path()
        == ROOT / "configs/quality/architecture_metric_exemptions.yaml"
    )


def test_custom_roots_and_explicit_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom = tmp_path / "custom"
    external = tmp_path / "external"
    custom.mkdir()
    external.mkdir()
    monkeypatch.chdir(external)
    monkeypatch.setattr(reduction, "_project_root", lambda: custom)
    monkeypatch.setattr(tasks, "_project_root", lambda: custom)
    monkeypatch.setattr(debt, "_project_root", lambda: custom)
    monkeypatch.setattr(paths, "project_root", lambda: custom)
    assert reduction.find_latest_architecture_debt_tasks_file() is None
    reports = custom / "reports/quality"
    reports.mkdir(parents=True)
    latest = reports / "tasks_architecture_metric_exemptions_2026-10-21.json"
    latest.write_text("{}", encoding="utf-8")
    assert (
        reduction.find_latest_architecture_debt_tasks_file(project_root=custom)
        == latest
    )
    assert reduction.find_latest_architecture_debt_tasks_file() == latest
    assert (
        tasks._default_output_path(project_root=custom, generated_at=STAMP).parent
        == reports
    )
    assert debt._resolve_scorecard_path("relative.yaml") == custom / "relative.yaml"
    assert paths.resolve_registry_path("relative.yaml") == custom / "relative.yaml"
    for name in ("score.yaml", "registry.yaml"):
        (external / name).write_text("registries: {}\n", encoding="utf-8")
    assert debt.load_debt_scorecard(external / "score.yaml") == {"registries": {}}
    assert load_exemptions_registry(external / "registry.yaml") == {"registries": {}}
    assert (
        paths.resolve_registry_path(external / "registry.yaml")
        == external / "registry.yaml"
    )
    (custom / "relative.yaml").write_text("registries: {}\n", encoding="utf-8")
    assert debt.load_debt_scorecard("relative.yaml") == {"registries": {}}
    assert load_exemptions_registry("relative.yaml") == {"registries": {}}
    (external / "data.json").write_text('{"tasks": []}', encoding="utf-8")
    assert reduction.load_architecture_debt_tasks("data.json") == {"tasks": []}
    assert reduction.load_architecture_debt_tasks(external / "data.json") == {
        "tasks": []
    }
    assert quality._load_json(custom, str(external / "data.json")) == {"tasks": []}
    assert quality._load_yaml(custom, str(external / "score.yaml")) == {
        "registries": {}
    }
    assert quality._load_yaml(custom, "relative.yaml") == {"registries": {}}
    (custom / "data.json").write_text("{}", encoding="utf-8")
    assert quality._load_json(custom, "data.json") == {}
    payload = tasks.generate_architecture_debt_tasks_payload(
        registry_path=external / "registry.yaml",
        project_root=custom,
        generated_at=STAMP,
    )
    assert payload["schema_version"] == tasks.TASK_SCHEMA_VERSION


@pytest.mark.parametrize(
    "seam", ["reduction", "tasks", "quality_json", "quality_yaml", "debt", "registry"]
)
def test_missing_invalid_and_permission_errors(
    seam: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / (
        "input.json" if seam in {"reduction", "quality_json"} else "input.yaml"
    )

    def load() -> object:
        if seam == "reduction":
            return reduction.load_architecture_debt_tasks(path)
        if seam == "tasks":
            return tasks.generate_architecture_debt_tasks_payload(
                registry_path=path,
                project_root=tmp_path,
                generated_at=STAMP,
            )
        if seam == "quality_json":
            return quality._load_json(tmp_path, path.name)
        if seam == "quality_yaml":
            return quality._load_yaml(tmp_path, path.name)
        if seam == "debt":
            return debt.load_debt_scorecard(path)
        return load_exemptions_registry(path)

    with pytest.raises(FileNotFoundError):
        load()
    path.write_text("{invalid: [", encoding="utf-8")
    with pytest.raises((ValueError, yaml.YAMLError)):
        load()
    path.write_text("{}", encoding="utf-8")
    original = Path.read_text

    def denied(candidate: Path, *args: object, **kwargs: object) -> str:
        if candidate.resolve() == path:
            raise PermissionError("QM-07 denied fixture")
        return original(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", denied)
    with pytest.raises(PermissionError, match="QM-07 denied fixture"):
        load()


def test_gate_evaluators_execute_business_functions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.engineering.qa import debt_governance_gate_evaluators as evaluators

    monkeypatch.chdir(tmp_path)
    score = evaluators.load_debt_scorecard(ROOT / "configs/quality/debt_scorecard.yaml")
    assert isinstance(score, dict) and score
    errors, result = evaluators.evaluate_debt_scorecard(
        registry_path=ROOT / "configs/quality/architecture_metric_exemptions.yaml",
        scorecard_path=ROOT / "configs/quality/debt_scorecard.yaml",
        today=date(2026, 10, 21),
    )
    assert isinstance(errors, list)
    assert result is not None or errors
    payload = evaluators.build_architecture_quality_scorecard(repo_root=ROOT)
    assert payload["schema_version"] == 2
    assert payload["weights_sum"] == 1.0
    assert payload["categories"]
