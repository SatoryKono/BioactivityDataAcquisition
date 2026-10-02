"""Strict, isolated live acceptance of every configured pipeline and workflow.

Run the pytest entrypoint with BIOETL_GREEN_ACCEPTANCE=1. No missing evidence,
unsupported replay family or unsuccessful child is accepted as a green run.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import yaml


@dataclass(frozen=True)
class Case:
    kind: str
    name: str
    steps: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return f"{self.kind}-{self.name}"


def pipeline_prerequisites(name: str, root: Path) -> tuple[str, ...]:
    """Prepare upstream tables from the canonical companion workflow DAG."""
    path = root / "configs/workflows" / f"{name}.yaml"
    if not path.is_file():
        return ()
    rows = yaml.safe_load(path.read_text(encoding="utf-8"))["workflow"]["steps"]
    by_id = {row["step_id"]: row for row in rows}
    targets = [row for row in rows if row.get("pipeline_name") == name]
    if len(targets) != 1:
        return ()
    ordered: list[str] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(step_id: str) -> None:
        if step_id in visited:
            return
        if step_id in visiting:
            raise ValueError(f"Cyclic prerequisite workflow: {name}")
        visiting.add(step_id)
        row = by_id[step_id]
        for parent in row.get("depends_on", []):
            visit(parent)
        visiting.remove(step_id)
        visited.add(step_id)
        if row is not targets[0]:
            if row["kind"] != "pipeline":
                raise ValueError(f"Unsupported prerequisite kind: {row['kind']}")
            ordered.append(row["pipeline_name"])

    visit(targets[0]["step_id"])
    return tuple(ordered)


def discover(root: Path) -> tuple[Case, ...]:
    """Discover coverage from canonical configs, including composite entities."""
    cases = []
    for path in sorted((root / "configs/entities").glob("*/*.yaml")):
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        kind = "composite" if config["provider"] == "composite" else "pipeline"
        name = config["pipeline"]["pipeline_name"]
        cases.append(Case(kind, name, prerequisites=pipeline_prerequisites(name, root)))
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
        "--required-persistence-profile",
        "degraded_observable",
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
    assert folder.resolve().is_relative_to(root.resolve()), (
        "Output must stay inside the isolated worktree"
    )
    folder.mkdir(parents=True, exist_ok=False)
    data, reports = folder / "data", folder / "reports"
    shutil.copytree(root / "data/input", data / "input")
    shutil.copytree(root / "configs", folder / "configs")
    shutil.copy2(root / "uv.lock", folder / "uv.lock")
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
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        NUMEXPR_NUM_THREADS="1",
        POLARS_MAX_THREADS="2",
        TOKIO_WORKER_THREADS="2",
    )
    if sys.platform == "win32":
        environment[
            "BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__PLAIN_WRITE_PROCESS_ISOLATION"
        ] = "true"
    args = command(case)
    failures = []
    launches = [command(Case("pipeline", name)) for name in case.prerequisites]
    launches.append(args)
    with (folder / "launch.log").open("w", encoding="utf-8") as log:
        for launch in launches:
            failures.extend(run_launch(launch, folder, environment, log))
            if failures:
                break
    failures.extend(logged_errors((folder / "launch.log").read_text(encoding="utf-8")))
    paths = sorted(reports.glob("pipeline/*/*/pipeline-run-report.json"))
    if not paths:
        failures.append("pipeline_reports_missing")
    for path in paths:
        try:
            failures.extend(inspect_pipeline(path, reports, data))
        except Exception as exc:
            failures.append(f"{path.name}: {type(exc).__name__}: {exc}")
    expected_names = sorted([case.name, *case.prerequisites])
    if (
        case.kind == "pipeline"
        and sorted(p.parent.parent.name for p in paths) != expected_names
    ):
        failures.append("pipeline_report_coverage_mismatch")
    if case.kind == "workflow":
        failures.extend(inspect_workflow(case, reports, paths))
    failures.extend(inspect_composite_parents(case, data, paths))
    (folder / "result.json").write_text(
        json.dumps(
            {
                "case": case.id,
                "command": args,
                "launches": launches,
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


def run_launch(
    args: list[str], folder: Path, environment: dict[str, str], log: TextIO
) -> list[str]:
    """Run one bounded launch and terminate its complete Windows process tree."""
    failures = []
    try:
        process = subprocess.Popen(
            args,
            cwd=folder,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        returncode = process.wait(timeout=1800)
        if returncode:
            failures.append(f"exit_code={returncode}")
    except subprocess.TimeoutExpired:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=30,
            )
        else:
            process.kill()
        process.wait(timeout=30)
        failures.append("launch_timeout=1800s")
    return failures


def inspect_workflow(case: Case, reports: Path, paths: list[Path]) -> list[str]:
    """Require the complete successful workflow and every bound child report."""
    failures = []
    parents = list(reports.glob(f"workflow/{case.name}/*/workflow-run-report.json"))
    if len(parents) != 1:
        failures.append("workflow_report_missing_or_ambiguous")
        return failures
    parent = json.loads(parents[0].read_text(encoding="utf-8"))
    if parent.get("schema_version") != "workflow_run_report_v1":
        failures.append("workflow_report_schema_mismatch")
    if (
        parent.get("identity", {}).get("workflow_name") != case.name
        or parent.get("identity", {}).get("workflow_run_id") != parents[0].parent.name
    ):
        failures.append("workflow_report_identity_mismatch")
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
    return failures


def inspect_composite_parents(case: Case, data: Path, paths: list[Path]) -> list[str]:
    """Do not infer parent evidence or replay readiness from successful children."""
    manifests = []
    for path in (data / "output/control/run_manifest").glob("*.json"):
        if path.name.endswith(".contract-evidence.json"):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("provider") == "composite":
            manifests.append(payload)
    failures = []
    if case.kind == "composite" and not any(
        manifest.get("pipeline_name") == case.name for manifest in manifests
    ):
        failures.append("composite_parent_manifest_missing")
    for manifest in manifests:
        if not any(
            path.parent.parent.name == manifest.get("pipeline_name")
            and path.parent.name == manifest.get("run_id")
            for path in paths
        ):
            failures.append(
                f"composite_parent_report_missing:{manifest.get('pipeline_name')}"
            )
    return failures
