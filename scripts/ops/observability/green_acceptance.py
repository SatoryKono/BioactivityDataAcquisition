"""Strict, isolated live acceptance of every configured pipeline and workflow.

Run the pytest entrypoint with BIOETL_GREEN_ACCEPTANCE=1. No missing evidence,
unsupported replay family or unsuccessful child is accepted as a green run.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

import yaml

LOCK_FILENAME = "uv.lock"
RESULT_FILENAME = "result.json"
CAMPAIGN_FILENAME = "campaign.json"


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


def command(case: Case, limit: int = 1000) -> list[str]:
    """Every actual launch carries the user-required record limit."""
    validate_limit(limit)
    if case.kind == "workflow":
        args = ["workflow", "run", case.name]
    elif case.kind == "composite":
        args = [
            "run-composite",
            "--composite",
            case.name.removeprefix("composite_"),
            "--no-health-server",
        ]
    else:
        args = ["run", "--pipeline", case.name, "--no-health-server"]
    return [
        sys.executable,
        "-m",
        "bioetl",
        *args,
        "--limit",
        str(limit),
        "--required-persistence-profile",
        "degraded_observable",
    ]


def launch_timeout(case: Case, root: Path) -> int:
    """Allow every configured stage its budget before the process-tree deadline."""
    if case.kind == "pipeline":
        return 1800
    if case.kind == "composite":
        name = case.name.removeprefix("composite_")
        config = yaml.safe_load(
            (root / "configs/composites" / f"{name}.yaml").read_text(encoding="utf-8")
        )["composite"]
        stages = [*config.get("dependencies", []), *config.get("enrichers", [])]
        return (
            1800 + 600 + sum(int(stage.get("timeout_seconds", 600)) for stage in stages)
        )
    config = yaml.safe_load(
        (root / "configs/workflows" / f"{case.name}.yaml").read_text(encoding="utf-8")
    )["workflow"]
    return 300 + sum(
        1800 if step["kind"] == "pipeline" else 300 for step in config["steps"]
    )


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


def validate_limit(limit: int) -> None:
    """Reject accidental booleans, unlimited runs and malformed record limits."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")


def source_commit(root: Path) -> str:
    """Require a committed candidate on an isolated acceptance branch."""
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=root, text=True
    ).strip()
    if not branch.startswith("codex/pipeline-green-gates"):
        raise ValueError(f"Unsafe branch: {branch}")
    if subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip():
        raise ValueError("Commit candidate before replay-ready launches")
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()


def write_receipt(path: Path, payload: dict) -> None:
    """Replace only a receipt owned by this new attempt, atomically."""
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(path)


def input_fingerprints(root: Path) -> dict[str, str]:
    """Bind all copied inputs by relative name and bytes, without exposing content."""
    fingerprints = {}
    for name in ("configs", "data/input", LOCK_FILENAME):
        path = root / name
        if not path.exists():
            raise FileNotFoundError(name)
        files = sorted(path.rglob("*")) if path.is_dir() else [path]
        entries = {}
        for item in files:
            if item.is_symlink():
                raise ValueError(
                    f"Snapshot symlink is unsupported: {item.relative_to(root)}"
                )
            if item.is_file():
                with item.open("rb") as stream:
                    entries[item.relative_to(root).as_posix()] = hashlib.file_digest(
                        stream, "sha256"
                    ).hexdigest()
        fingerprints[name] = hashlib.sha256(
            json.dumps(entries, sort_keys=True).encode()
        ).hexdigest()
    return fingerprints


def composite_report_coverage(
    case: Case, config_root: Path, paths: list[Path]
) -> list[str]:
    """Require every child unless immutable inputs prove an optional empty stage."""
    config = yaml.safe_load(
        (
            config_root / "composites" / f"{case.name.removeprefix('composite_')}.yaml"
        ).read_text(encoding="utf-8")
    )["composite"]
    expected = [
        config["seed"]["pipeline"],
        *[row["pipeline"] for row in config.get("dependencies", [])],
        *[row["pipeline"] for row in config.get("enrichers", [])],
    ]
    actual = [path.parent.parent.name for path in paths]
    failures = []
    parents = [path for path in paths if path.parent.parent.name == case.name]
    if len(parents) != 1:
        return failures + ["composite_parent_report_missing_or_ambiguous"]
    parent = json.loads(parents[0].read_text(encoding="utf-8"))
    missing = set(expected) - set(actual)
    if missing:
        from scripts.ops.observability.green_optional_inputs import (
            verified_empty_optional_stages,
        )

        try:
            skipped = verified_empty_optional_stages(config, parent, parents[0])
            expected = [name for name in expected if name not in missing & skipped]
        except (ValueError, OSError, KeyError, TypeError) as exc:
            failures.append(f"composite_optional_skip_unverified:{type(exc).__name__}")
    if sorted(actual) != sorted([case.name, *expected]):
        failures.append("composite_report_coverage_mismatch")
    children = parent.get("io", {}).get("child_runs", [])
    bound = sorted(
        (row.get("pipeline_name", ""), row.get("run_id", "")) for row in children
    )
    observed = sorted(
        (path.parent.parent.name, path.parent.name)
        for path in paths
        if path not in parents
    )
    if bound != observed or any(row.get("status") != "success" for row in children):
        failures.append("composite_child_identity_or_status_mismatch")
    return failures


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


def execute(
    case: Case,
    root: Path,
    output: Path,
    env_file: Path,
    *,
    limit: int = 1000,
    expected_source: str | None = None,
) -> list[str]:
    """Run once; retain a terminal receipt for setup errors and cancellation."""
    validate_limit(limit)
    source = source_commit(root)
    if expected_source is not None and source != expected_source:
        raise ValueError("source_commit_changed")
    folder = output / case.id
    if not folder.resolve().is_relative_to(root.resolve()):
        raise ValueError("Output must stay inside the isolated worktree")
    folder.mkdir(parents=True, exist_ok=False)
    failures: list[str] = []
    receipt = {
        "case": case.id,
        "command": command(case, limit),
        "limit": limit,
        "source_commit": source,
        "started_at": timestamp(),
        "status": "running",
        "passed": False,
        "failures": failures,
        "processes": [],
    }
    write_receipt(folder / RESULT_FILENAME, receipt)
    try:
        failures.extend(_execute_case(case, root, folder, env_file, limit, receipt))
    except BaseException as exc:
        failures.append(f"execution_error:{type(exc).__name__}")
        receipt["status"] = (
            "interrupted" if not isinstance(exc, Exception) else "failed"
        )
        raise
    finally:
        try:
            receipt["source_commit_after"] = source_commit(root)
            if receipt["source_commit_after"] != source:
                failures.append("source_commit_changed")
        except Exception as exc:
            failures.append(f"source_verification_error:{type(exc).__name__}")
        if receipt["status"] == "running":
            receipt["status"] = "failed" if failures else "success"
        receipt.update(finished_at=timestamp(), passed=not failures)
        write_receipt(folder / RESULT_FILENAME, receipt)
    return failures


def _execute_case(
    case: Case,
    root: Path,
    folder: Path,
    env_file: Path,
    limit: int,
    receipt: dict,
) -> list[str]:
    data, reports = folder / "data", folder / "reports"
    inputs_before = input_fingerprints(root)
    shutil.copytree(root / "data/input", data / "input")
    shutil.copytree(root / "configs", folder / "configs")
    shutil.copy2(root / LOCK_FILENAME, folder / LOCK_FILENAME)
    receipt["input_fingerprints"] = input_fingerprints(folder)
    if (
        receipt["input_fingerprints"] != inputs_before
        or input_fingerprints(root) != inputs_before
    ):
        raise ValueError("input_snapshot_changed_during_copy")
    write_receipt(folder / RESULT_FILENAME, receipt)
    environment = _case_environment(root, folder, env_file)
    failures = []
    launch_cases = [Case("pipeline", name) for name in case.prerequisites] + [case]
    launches = [command(launch_case, limit) for launch_case in launch_cases]
    timeouts = [launch_timeout(launch_case, root) for launch_case in launch_cases]
    receipt.update(launches=launches, launch_timeout_seconds=timeouts)
    with (folder / "launch.log").open("w", encoding="utf-8") as log:
        for launch, timeout in zip(launches, timeouts, strict=True):
            process_receipt: dict = {}
            receipt["processes"].append(process_receipt)
            failures.extend(
                run_launch(
                    launch,
                    folder,
                    environment,
                    log,
                    timeout_seconds=timeout,
                    receipt=process_receipt,
                )
            )
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
    if case.kind == "composite":
        failures.extend(composite_report_coverage(case, folder / "configs", paths))
    if (
        input_fingerprints(folder) != inputs_before
        or input_fingerprints(root) != inputs_before
    ):
        failures.append("input_snapshot_changed_during_execution")
    return failures


def _case_environment(root: Path, folder: Path, env_file: Path) -> dict[str, str]:
    """Bind runtime to captured roots and the unchanged provider/thread budgets."""
    from dotenv import dotenv_values

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
        BIOETL_CONFIGS_ROOT=str(folder / "configs"),
        PYTHONPATH=os.pathsep.join([str(root / "src"), str(root)]),
        BIOETL_METRICS_ENABLED="false",
        BIOETL_OBSERVABILITY__METRICS_ENABLED="false",
        BIOETL_OBSERVABILITY__METRICS_SERVER_ENABLED="false",
        BIOETL_PUSHGATEWAY_URL="",
        BIOETL_SEMANTICSCHOLAR_API_KEY="",
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
    return environment


def _stop_launch_process(process: subprocess.Popen, log: TextIO) -> None:
    """Stop and reap an owned launch without masking a process-exit race."""
    if process.poll() is None:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=30,
            )
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(timeout=30)


def run_launch(
    args: list[str],
    folder: Path,
    environment: dict[str, str],
    log: TextIO,
    *,
    timeout_seconds: int = 1800,
    receipt: dict | None = None,
) -> list[str]:
    """Bound a launch, recording its exit and cleaning up its own process tree."""
    receipt = receipt if receipt is not None else {}
    receipt.update(command=args, started_at=timestamp(), status="starting")
    process = None
    try:
        process = subprocess.Popen(
            args,
            cwd=folder,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=sys.platform != "win32",
        )
        receipt.update(pid=process.pid, status="running")
        returncode = process.wait(timeout=timeout_seconds)
        receipt.update(
            exit_code=returncode, status="failed" if returncode else "success"
        )
        return [f"exit_code={returncode}"] if returncode else []
    except subprocess.TimeoutExpired:
        receipt["status"] = "timeout"
        return [f"launch_timeout={timeout_seconds}s"]
    except BaseException as exc:
        receipt["status"] = "failed" if isinstance(exc, Exception) else "interrupted"
        receipt["error_type"] = type(exc).__name__
        raise
    finally:
        try:
            if process is not None and receipt["status"] in {
                "timeout",
                "interrupted",
                "failed",
            }:
                _stop_launch_process(process, log)
                receipt["exit_code"] = process.returncode
        finally:
            receipt["finished_at"] = timestamp()


COMPOSITE_ORDER = ("activity", "assay", "molecule", "target")


def _validate_campaign_output(root: Path, output: Path, limit: int) -> None:
    """Reject invalid limits, parallel workers and outputs outside this worktree."""
    validate_limit(limit)
    if os.environ.get("PYTEST_XDIST_WORKER"):
        raise ValueError("Campaign requires sequential pytest without xdist")
    if not output.resolve().is_relative_to((root / "reports").resolve()):
        raise ValueError("Campaign output must stay inside worktree reports")


def execute_campaign(
    root: Path, output: Path, env_file: Path, *, limit: int = 10
) -> list[str]:
    """Run the four RF-022 cases sequentially under one exclusive worktree lease.

    Local checks are preparation evidence. HTTP and offline replay acceptance
    remain separate obligations even if every local check passes.
    """
    _validate_campaign_output(root, output, limit)
    source = source_commit(root)
    inputs = input_fingerprints(root)
    available = {case.name: case for case in discover(root) if case.kind == "composite"}
    cases = [available[f"composite_{name}"] for name in COMPOSITE_ORDER]
    lock = root / "reports/quality/green-acceptance.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("x", encoding="utf-8") as stream:
        json.dump(
            {"pid": os.getpid(), "source_commit": source, "output": str(output)}, stream
        )
    rows = [
        {"case": case.id, "status": "not_started", "failures": []} for case in cases
    ]
    manifest = {
        "source_commit": source,
        "scope": {
            "issue": 11906,
            "composites": [case.name for case in cases],
            "excluded": {"composite_publication": "Tracked separately in #11947"},
        },
        "limit": limit,
        "started_at": timestamp(),
        "status": "running",
        "local_checks_passed": False,
        "acceptance_status": "PENDING_HTTP_AND_OFFLINE_REPLAY",
        "input_fingerprints": inputs,
        "cases": rows,
    }
    created = False
    failures: list[str] = []
    try:
        output.mkdir(parents=True, exist_ok=False)
        created = True
        write_receipt(output / CAMPAIGN_FILENAME, manifest)
        for case, row in zip(cases, rows, strict=True):
            row["status"] = "running"
            write_receipt(output / CAMPAIGN_FILENAME, manifest)
            try:
                if input_fingerprints(root) != inputs:
                    raise ValueError("campaign_inputs_changed")
                errors = execute(
                    case, root, output, env_file, limit=limit, expected_source=source
                )
            except BaseException as exc:
                row.update(
                    status="interrupted"
                    if not isinstance(exc, Exception)
                    else "failed",
                    error_type=type(exc).__name__,
                )
                manifest["status"] = row["status"]
                raise
            row.update(status="failed" if errors else "success", failures=errors)
            failures.extend(f"{case.id}:{error}" for error in errors)
            write_receipt(output / CAMPAIGN_FILENAME, manifest)
        if input_fingerprints(root) != inputs:
            failures.append("campaign_inputs_changed")
        manifest["status"] = "failed" if failures else "success"
        manifest["local_checks_passed"] = not failures
    finally:
        try:
            if created:
                if manifest["status"] == "running":
                    manifest["status"] = "interrupted"
                manifest["finished_at"] = timestamp()
                write_receipt(output / CAMPAIGN_FILENAME, manifest)
        finally:
            lock.unlink()
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
