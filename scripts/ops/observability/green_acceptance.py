"""Strict, isolated live acceptance of every configured pipeline and workflow.

Run the pytest entrypoint with BIOETL_GREEN_ACCEPTANCE=1. No missing evidence,
unsupported replay family or unsuccessful child is accepted as a green run.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Case:
    kind: str
    name: str
    steps: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return f"{self.kind}-{self.name}"


def discover(root: Path) -> tuple[Case, ...]:
    """Discover coverage from canonical configs, including composite entities."""
    cases = []
    for path in sorted((root / "configs/entities").glob("*/*.yaml")):
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        kind = "composite" if config["provider"] == "composite" else "pipeline"
        cases.append(Case(kind, config["pipeline"]["pipeline_name"]))
    for path in sorted((root / "configs/workflows").glob("*.yaml")):
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))["workflow"]
        cases.append(
            Case(
                "workflow",
                workflow["name"],
                tuple(step["step_id"] for step in workflow["steps"]),
            )
        )
    assert cases and len({case.id for case in cases}) == len(cases)
    return tuple(cases)


def command(case: Case) -> list[str]:
    """Every actual launch carries the user-required record limit."""
    if case.kind == "workflow":
        args = ["workflow", "run", case.name]
    elif case.kind == "composite":
        args = ["run-composite", "--composite", case.name.removeprefix("composite_")]
    else:
        args = ["run", "--pipeline", case.name, "--no-health-server"]
    return [
        sys.executable,
        "-m",
        "bioetl",
        *args,
        "--limit",
        "1000",
    ]


def green_failures(status: str, presentation: dict, assessment: dict) -> list[str]:
    """Only explicit green values pass; absent and unsupported values fail."""
    expected = {
        "overview": (status, "success"),
        "saved_evidence": (presentation.get("saved_evidence_status"), "OK"),
        "replay_readiness": (presentation.get("replay_readiness_status"), "OK"),
        "overall_verdict": (assessment.get("verdict"), "OK"),
        "evidence_completeness": (assessment.get("evidence_completeness"), "COMPLETE"),
    }
    return [
        f"{key}={actual!r}, expected {wanted}"
        for key, (actual, wanted) in expected.items()
        if actual != wanted
    ]


def logged_errors(text: str) -> list[str]:
    """Reject structured error records even when the CLI eventually exits zero."""
    errors = []
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict) and record.get("level") in {
            "error",
            "critical",
            "fatal",
        }:
            errors.append(f"error_log:{record.get('event', 'unknown')}")
    return errors


def inspect_pipeline(path: Path, reports: Path, data: Path) -> list[str]:
    """Use the same file verification and projections as the shipped dashboard."""
    from bioetl.infrastructure.control_plane import FileRunManifestStore
    from bioetl.infrastructure.control_plane.replay_object_verifier import (
        ReplayObjectVerifier,
    )
    from bioetl.interfaces.http._recent_run_presentation import recent_run_presentation
    from bioetl.interfaces.http.selected_run_status import load_selected_run_status

    payload = json.loads(path.read_text(encoding="utf-8"))
    identity = payload["identity"]
    pipeline, run_id = path.parent.parent.name, path.parent.name
    assert identity["pipeline_name"] == pipeline and identity["run_id"] == run_id
    control = data / "output/control"
    port = FileRunManifestStore(
        base_path=control / "run_manifest",
        replay_object_verifier=ReplayObjectVerifier(
            config_root=control / "effective_config",
            lock_root=control / "dependency_locks",
            bronze_root=data / "output/bronze",
        ),
    )
    assessment = load_selected_run_status(
        pipeline=pipeline, run_id=run_id, root=reports, manifest_port=port
    )
    presentation = recent_run_presentation(
        {"pipeline": pipeline, "run_id": run_id},
        root=reports,
        manifest_port=port,
    )
    (path.parent / "green-acceptance.json").write_text(
        json.dumps(
            {"assessment": assessment, "presentation": presentation},
            indent=2,
        ),
        encoding="utf-8",
    )
    return [
        f"{pipeline}/{run_id}: {reason}"
        for reason in green_failures(
            identity.get("status", "UNKNOWN"),
            presentation,
            assessment,
        )
    ]


def execute(case: Case, root: Path, output: Path, env_file: Path) -> list[str]:
    """Run once into a fresh case directory; persist failures even on process exit."""
    from dotenv import dotenv_values

    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=root, text=True
    ).strip()
    assert branch.startswith("codex/pipeline-green-gates"), f"Unsafe branch: {branch}"
    assert not subprocess.check_output(
        ["git", "status", "--porcelain", "-uno"], cwd=root, text=True
    ).strip(), "Commit candidate before replay-ready launches"
    folder = output / case.id
    folder.mkdir(parents=True, exist_ok=False)
    data, reports = folder / "data", folder / "reports"
    environment = {
        **os.environ,
        **{
            key: value
            for key, value in dotenv_values(env_file).items()
            if value is not None
        },
    }
    environment.update(
        BIOETL_DATA_DIR=str(data),
        BIOETL_REPORT_ROOT=str(reports),
        BIOETL_CONFIGS_ROOT=str(root / "configs"),
        PYTHONPATH=os.pathsep.join([str(root / "src"), str(root)]),
        BIOETL_METRICS_ENABLED="false",
        BIOETL_PUSHGATEWAY_URL="",
        PYTHONDONTWRITEBYTECODE="1",
    )
    args = command(case)
    failures = []
    with (folder / "launch.log").open("w", encoding="utf-8") as log:
        try:
            result = subprocess.run(
                args,
                cwd=root,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=1800,
                check=False,
            )
            if result.returncode:
                failures.append(f"exit_code={result.returncode}")
        except subprocess.TimeoutExpired:
            failures.append("launch_timeout=1800s")
    failures.extend(logged_errors((folder / "launch.log").read_text(encoding="utf-8")))
    paths = sorted(reports.glob("pipeline/*/*/pipeline-run-report.json"))
    if not paths:
        failures.append("pipeline_reports_missing")
    for path in paths:
        try:
            failures.extend(inspect_pipeline(path, reports, data))
        except Exception as exc:
            failures.append(f"{path.name}: {type(exc).__name__}: {exc}")
    if case.kind == "pipeline" and (
        len(paths) != 1 or paths[0].parent.parent.name != case.name
    ):
        failures.append("pipeline_report_coverage_mismatch")
    if case.kind == "workflow":
        parents = list(reports.glob(f"workflow/{case.name}/*/workflow-run-report.json"))
        if len(parents) != 1:
            failures.append("workflow_report_missing_or_ambiguous")
        else:
            parent = json.loads(parents[0].read_text(encoding="utf-8"))
            rows = parent.get("execution", [])
            if parent["identity"].get("status") != "success":
                failures.append("workflow_status_not_success")
            if sorted(row["step_id"] for row in rows) != sorted(case.steps):
                failures.append("workflow_step_coverage_mismatch")
            for row in rows:
                if (
                    row.get("status") != "success"
                    or row.get("error_type")
                    or row.get("error_message")
                ):
                    failures.append(f"workflow_step_failed:{row['step_id']}")
                if row.get("kind") == "pipeline" and not any(
                    p.parent.name == row.get("pipeline_run_id")
                    and p.parent.parent.name == row.get("pipeline_name")
                    for p in paths
                ):
                    failures.append(f"workflow_child_report_missing:{row['step_id']}")
    (folder / "result.json").write_text(
        json.dumps(
            {
                "case": case.id,
                "command": args,
                "limit": 1000,
                "source_commit": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=root, text=True
                ).strip(),
                "failures": failures,
                "passed": not failures,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return failures
