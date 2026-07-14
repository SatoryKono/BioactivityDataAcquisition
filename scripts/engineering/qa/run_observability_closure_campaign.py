#!/usr/bin/env python3
"""Run a bounded, evidence-gated observability closure campaign.

The runner never edits a dotenv file. Pipeline processes receive explicit
isolated data and log paths through their process environment, while tracked
configuration is resolved from the checkout containing this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess  # nosec B404 - command is assembled from fixed literals.
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

CHEMBL_PIPELINES = (
    "chembl_activity",
    "chembl_assay",
    "chembl_assay_parameters",
    "chembl_cell_line",
    "chembl_compound_record",
    "chembl_molecule",
    "chembl_protein_class",
    "chembl_publication",
    "chembl_publication_similarity",
    "chembl_publication_term",
    "chembl_subcellular_fraction",
    "chembl_target",
    "chembl_target_component",
    "chembl_target_protein_classification",
    "chembl_tissue",
)

REQUIRED_EXTERNAL_EVIDENCE = (
    "tracing_parity",
    "metric_reconciliation",
    "workflow_correlation",
    "metric_surface",
    "dashboard_variables",
    "zero_evidence",
    "scrape_targets",
    "render_stability",
    "promtool",
    "online_run",
)

EVIDENCE_SUMMARY_REQUIREMENTS: dict[str, dict[str, int]] = {
    "tracing_parity": {
        "pipelines_compared": 15,
        "mismatch_count": 0,
        "chembl_population_score_x100": 4321,
    },
    "metric_reconciliation": {"pipelines_reconciled": 15, "mismatch_count": 0},
    "workflow_correlation": {
        "success_cases": 1,
        "failure_cases": 1,
        "mismatch_count": 0,
    },
    "metric_surface": {
        "record_outputs": 103,
        "drift_count": 0,
        "metric_quality_score_x100": 4600,
    },
    "dashboard_variables": {
        "dashboard_count": 8,
        "pipeline_count": 15,
        "missing_count": 0,
    },
    "zero_evidence": {"case_count": 4, "mismatch_count": 0},
    "scrape_targets": {
        "executable_targets": 213,
        "recaptured": 213,
        "mismatch_count": 0,
    },
    "render_stability": {
        "dashboard_count": 8,
        "renders_per_dashboard": 2,
        "unstable_count": 0,
        "dashboard_quality_score_x100": 4232,
    },
    "promtool": {"rule_file_count": 2, "failure_count": 0},
    "online_run": {
        "attempt_count": 1,
        "terminal_event_count": 1,
        "failure_count": 0,
        "overall_observability_score_x100": 4600,
    },
}

EVIDENCE_RAW_KIND_REQUIREMENTS: dict[str, dict[str, int]] = {
    "tracing_parity": {"attempt-result": 2},
    "metric_reconciliation": {"prometheus-response": 1, "ledger-snapshot": 1},
    "workflow_correlation": {"workflow-result": 2, "child-result": 2},
    "metric_surface": {"inventory-report": 1},
    "dashboard_variables": {"dashboard-variable-report": 8},
    "zero_evidence": {"raw-zero-source": 4},
    "scrape_targets": {"target-capture": 213},
    "render_stability": {"render-manifest": 16, "screenshot": 16},
    "promtool": {"promtool-output": 3},
    "online_run": {"online-run-result": 1, "instrumentation-response": 1},
}

TERMINAL_EVENTS = frozenset({"run_finished", "run_failed"})


@dataclass(frozen=True, slots=True)
class AttemptEvidence:
    """Durable evidence for one pipeline/tracing-mode attempt."""

    pipeline: str
    tracing: bool
    started_at: str
    finished_at: str
    exit_code: int
    timed_out: bool
    command: tuple[str, ...]
    stdout_path: str
    stderr_path: str
    manifest_ids: tuple[str, ...]
    run_ids: tuple[str, ...]
    terminal_ledger_events: tuple[str, ...]
    manifest_artifacts: tuple[dict[str, str], ...] = ()
    ledger_artifacts: tuple[dict[str, str], ...] = ()
    checkpoint_artifacts: tuple[dict[str, str], ...] = ()
    output_artifacts: tuple[dict[str, str], ...] = ()
    terminal_metrics_snapshot: dict[str, int] = field(default_factory=dict)
    terminal_details: dict[str, object] = field(default_factory=dict)
    result_signature: str = ""
    run_mode: str = "standalone_cached"

    @property
    def has_one_terminal_event(self) -> bool:
        """Return whether the attempt produced exactly one terminal ledger row."""
        return len(self.terminal_ledger_events) == 1

    @property
    def satisfies_closure(self) -> bool:
        """Return whether this standalone run has unambiguous success evidence."""
        return bool(
            self.exit_code == 0
            and not self.timed_out
            and len(self.manifest_ids) == 1
            and len(self.run_ids) == 1
            and self.terminal_ledger_events == ("run_finished",)
            and len(self.manifest_artifacts) == 1
            and len(self.ledger_artifacts) == 1
            and bool(self.checkpoint_artifacts)
            and bool(self.output_artifacts)
            and bool(self.result_signature)
        )


@dataclass(frozen=True, slots=True)
class PhaseEvidence:
    """Retained command evidence for one non-standalone campaign phase."""

    name: str
    command: tuple[str, ...]
    started_at: str
    finished_at: str
    exit_code: int
    timed_out: bool
    stdout_path: str
    stdout_sha256: str
    stderr_path: str
    stderr_sha256: str

    @property
    def satisfies_closure(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _discover_chembl_pipelines(repo_root: Path) -> tuple[str, ...]:
    config_root = repo_root / "configs" / "entities" / "chembl"
    names: list[str] = []
    for path in sorted(config_root.glob("*.yaml")):
        matches = re.findall(
            r"^\s*pipeline_name:\s*([a-z0-9_]+)\s*$",
            path.read_text(encoding="utf-8"),
            flags=re.MULTILINE,
        )
        if len(matches) != 1:
            raise ValueError(f"expected one pipeline.pipeline_name in {path}")
        names.append(matches[0])
    return tuple(sorted(names))


def _registry_pipeline_command(
    repo_root: Path, *, python: Path
) -> tuple[tuple[str, ...], subprocess.CompletedProcess[str]]:
    """Discover pipeline names through the canonical public CLI command."""
    command = (str(python), "-m", "bioetl", "config", "list-pipelines")
    completed = subprocess.run(  # nosec B603
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    names = tuple(
        sorted(
            line.removeprefix("  - ").strip()
            for line in completed.stdout.splitlines()
            if line.startswith("  - chembl_")
        )
    )
    return names, completed


def _discover_registered_chembl_pipelines(repo_root: Path) -> tuple[str, ...]:
    names, _completed = _registry_pipeline_command(
        repo_root,
        python=Path(sys.executable),
    )
    return names


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_signature(root: Path) -> str:
    """Return a deterministic content signature for one canonical root."""
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing")
        return digest.hexdigest()
    if root.is_file():
        digest.update(root.name.encode())
        digest.update(_sha256_file(root).encode())
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(_sha256_file(path).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def _parse_evidence(items: Iterable[str]) -> dict[str, str]:
    evidence: dict[str, str] = {}
    for item in items:
        key, separator, value = item.partition("=")
        if not separator or not key.strip() or not value.strip():
            raise ValueError("--evidence values must use KEY=/absolute/path")
        path = Path(value).expanduser()
        if not path.is_absolute():
            raise ValueError(f"evidence path for {key!r} must be absolute")
        normalized_key = key.strip()
        if normalized_key in evidence:
            raise ValueError(f"duplicate evidence key: {normalized_key}")
        evidence[normalized_key] = str(path.resolve())
    return evidence


def _validate_roots(audit_root: Path, canonical_roots: tuple[Path, ...]) -> None:
    if not audit_root.is_absolute():
        raise ValueError("--audit-root must be absolute")
    resolved_audit = audit_root.resolve()
    for root in canonical_roots:
        resolved = root.expanduser().resolve()
        if not resolved.is_dir():
            raise ValueError(
                f"canonical root must be an existing directory: {resolved}"
            )
        if resolved == resolved_audit:
            raise ValueError("audit root must differ from every canonical root")
        if resolved in resolved_audit.parents or resolved_audit in resolved.parents:
            raise ValueError("audit and canonical roots must not contain each other")


def _validate_canonical_layout(data_root: Path, log_root: Path) -> None:
    resolved_data = data_root.expanduser().resolve()
    resolved_logs = log_root.expanduser().resolve()
    if resolved_data == resolved_logs:
        raise ValueError("canonical data and log roots must differ")
    if not (resolved_data / "output" / "bronze").is_dir():
        raise ValueError(
            "canonical data root must contain the immutable output/bronze cache"
        )


def _validate_fresh_audit_root(audit_root: Path) -> None:
    """Reject retained runtime state while allowing prebuilt evidence manifests."""
    if not audit_root.exists():
        return
    forbidden = ("data", "logs", "attempts", "observability-closure-campaign.json")
    present = [name for name in forbidden if (audit_root / name).exists()]
    if present:
        raise ValueError(
            "audit root contains retained runtime state: " + ", ".join(present)
        )


def _manifest_snapshot(data_root: Path) -> set[Path]:
    root = data_root / "output" / "control" / "run_manifest"
    return set(root.glob("*.json")) if root.is_dir() else set()


def _file_snapshot(root: Path) -> dict[Path, str]:
    if not root.is_dir():
        return {}
    return {
        path: _sha256_file(path)
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    }


def _changed_files(before: dict[Path, str], after: dict[Path, str]) -> set[Path]:
    return {
        path
        for path, digest in after.items()
        if path not in before or before[path] != digest
    }


def _file_artifacts(paths: Iterable[Path], *, root: Path) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "path": str(path),
            "relative_path": path.relative_to(root).as_posix(),
            "sha256": _sha256_file(path),
        }
        for path in sorted(paths)
        if path.is_file()
    )


def _read_new_manifest_identity(
    paths: Iterable[Path], *, expected_pipeline: str
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[Path, ...]]:
    manifest_ids: list[str] = []
    run_ids: list[str] = []
    retained_paths: list[Path] = []
    for path in sorted(paths):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(payload.get("pipeline_name") or "") != expected_pipeline:
            continue
        retained_paths.append(path)
        manifest_id = str(payload.get("manifest_id") or "").strip()
        run_id = str(payload.get("run_id") or "").strip()
        if manifest_id:
            manifest_ids.append(manifest_id)
        if run_id:
            run_ids.append(run_id)
    return tuple(manifest_ids), tuple(run_ids), tuple(retained_paths)


def _read_ledger_rows(data_root: Path) -> list[dict[str, object]]:
    root = data_root / "output" / "control" / "run_ledger"
    rows: list[dict[str, object]] = []
    if not root.is_dir():
        return rows
    for path in sorted(root.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _terminal_events_for_runs(
    rows: Iterable[dict[str, object]], run_ids: tuple[str, ...]
) -> tuple[str, ...]:
    selected: list[str] = []
    run_id_set = set(run_ids)
    for row in rows:
        if str(row.get("run_id") or "") not in run_id_set:
            continue
        event_type = str(row.get("event_type") or "")
        if event_type in TERMINAL_EVENTS:
            selected.append(event_type)
    return tuple(selected)


def _terminal_rows_for_runs(
    rows: Iterable[dict[str, object]], run_ids: tuple[str, ...]
) -> tuple[dict[str, object], ...]:
    run_id_set = set(run_ids)
    return tuple(
        row
        for row in rows
        if str(row.get("run_id") or "") in run_id_set
        and str(row.get("event_type") or "") in TERMINAL_EVENTS
    )


def _terminal_payload(
    rows: tuple[dict[str, object], ...],
) -> tuple[dict[str, int], dict[str, object], str]:
    if len(rows) != 1:
        return {}, {}, ""
    row = rows[0]
    raw_metrics = row.get("metrics_snapshot")
    metrics = (
        {
            str(key): value
            for key, value in raw_metrics.items()
            if isinstance(key, str) and type(value) is int
        }
        if isinstance(raw_metrics, dict)
        else {}
    )
    raw_details = row.get("details")
    details = (
        {str(key): value for key, value in raw_details.items()}
        if isinstance(raw_details, dict)
        else {}
    )
    semantic_payload = {
        "event_type": row.get("event_type"),
        "metrics_snapshot": metrics,
        "details": details,
    }
    signature = hashlib.sha256(
        json.dumps(semantic_payload, sort_keys=True, default=str).encode()
    ).hexdigest()
    return metrics, details, signature


def _timeout_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _run_phase_command(
    *,
    name: str,
    command: tuple[str, ...],
    repo_root: Path,
    phase_root: Path,
    data_root: Path,
    timeout_seconds: int,
) -> PhaseEvidence:
    phase_root.mkdir(parents=True, exist_ok=True)
    stdout_path = phase_root / "stdout.log"
    stderr_path = phase_root / "stderr.log"
    env = os.environ.copy()
    env["BIOETL_DATA_DIR"] = str(data_root)
    env["BIOETL_LOG_FILE"] = str(phase_root / "bioetl.log")
    started_at = _utc_now()
    timed_out = False
    try:
        completed = subprocess.run(  # nosec B603
            command,
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = 124
        stdout = _timeout_output(exc.stdout)
        stderr = _timeout_output(exc.stderr)
    except OSError as exc:
        exit_code = 126
        stdout = ""
        stderr = f"{type(exc).__name__}: {exc}"
    finished_at = _utc_now()
    stdout_path.write_text(str(stdout), encoding="utf-8")
    stderr_path.write_text(str(stderr), encoding="utf-8")
    return PhaseEvidence(
        name=name,
        command=command,
        started_at=started_at,
        finished_at=finished_at,
        exit_code=exit_code,
        timed_out=timed_out,
        stdout_path=str(stdout_path),
        stdout_sha256=_sha256_file(stdout_path),
        stderr_path=str(stderr_path),
        stderr_sha256=_sha256_file(stderr_path),
    )


def _workflow_baseline_command(
    *, python: Path, limit: int, cached_bronze_root: Path
) -> tuple[str, ...]:
    return (
        str(python),
        "-m",
        "bioetl",
        "workflow",
        "run",
        "chembl_baseline",
        "--run-type",
        "incremental",
        "--limit",
        str(limit),
        "--use-cached-bronze",
        "--cached-bronze-path",
        str(cached_bronze_root),
        "--no-tracing",
        "--no-ensure-observability-backend",
    )


def _workflow_failure_tests_command(*, python: Path) -> tuple[str, ...]:
    return (
        str(python),
        "-m",
        "pytest",
        "-q",
        (
            "tests/unit/application/services/test_workflow_runner_service.py::"
            "test_workflow_runner_marks_downstream_steps_skipped_after_failure"
        ),
        (
            "tests/unit/application/services/test_data_quality_service.py::"
            "TestDataQualityServiceThresholds::"
            "test_hard_threshold_exactly_at_limit_raises_error"
        ),
    )


def _attempt_command(
    *,
    python: Path,
    pipeline: str,
    limit: int,
    tracing: bool,
    cached_bronze_root: Path | None,
) -> tuple[str, ...]:
    command = [
        str(python),
        "-m",
        "bioetl",
        "run",
        "--pipeline",
        pipeline,
        "--run-type",
        "incremental",
        "--limit",
        str(limit),
        "--no-health-server",
        "--tracing" if tracing else "--no-tracing",
    ]
    if cached_bronze_root is None:
        command.append("--no-cached-bronze")
    else:
        command.extend(
            ("--use-cached-bronze", "--cached-bronze-path", str(cached_bronze_root))
        )
    return tuple(command)


def _run_attempt(
    *,
    repo_root: Path,
    audit_root: Path,
    python: Path,
    pipeline: str,
    limit: int,
    tracing: bool,
    timeout_seconds: int,
    cached_bronze_root: Path | None,
    run_mode: str = "standalone_cached",
) -> AttemptEvidence:
    attempt_name = f"{run_mode}--{pipeline}--tracing-{str(tracing).lower()}"
    attempt_root = audit_root / "attempts" / attempt_name
    data_root = attempt_root / "data"
    log_root = attempt_root / "logs"
    attempt_root.mkdir(parents=True, exist_ok=True)
    log_root.mkdir(parents=True, exist_ok=True)
    stdout_path = attempt_root / "stdout.log"
    stderr_path = attempt_root / "stderr.log"
    before_manifests = _manifest_snapshot(data_root)
    before_files = _file_snapshot(data_root)
    command = _attempt_command(
        python=python,
        pipeline=pipeline,
        limit=limit,
        tracing=tracing,
        cached_bronze_root=cached_bronze_root,
    )
    env = os.environ.copy()
    env["BIOETL_DATA_DIR"] = str(data_root)
    env["BIOETL_LOG_FILE"] = str(log_root / "bioetl-audit.log")
    started_at = _utc_now()
    timed_out = False
    try:
        completed = subprocess.run(  # nosec B603
            command,
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = 124
        stdout = _timeout_output(exc.stdout)
        stderr = _timeout_output(exc.stderr)
    except OSError as exc:
        timed_out = False
        exit_code = 126
        stdout = ""
        stderr = f"{type(exc).__name__}: {exc}"
    finished_at = _utc_now()
    stdout_path.write_text(str(stdout), encoding="utf-8")
    stderr_path.write_text(str(stderr), encoding="utf-8")
    new_manifests = _manifest_snapshot(data_root) - before_manifests
    manifest_ids, run_ids, manifest_paths = _read_new_manifest_identity(
        new_manifests,
        expected_pipeline=pipeline,
    )
    ledger_rows = _read_ledger_rows(data_root)
    terminal_events = _terminal_events_for_runs(ledger_rows, run_ids)
    terminal_rows = _terminal_rows_for_runs(ledger_rows, run_ids)
    metrics, details, _terminal_signature = _terminal_payload(terminal_rows)
    ledger_paths = tuple(
        data_root / "output" / "control" / "run_ledger" / f"{manifest_id}.jsonl"
        for manifest_id in manifest_ids
    )
    after_files = _file_snapshot(data_root)
    changed_files = _changed_files(before_files, after_files)
    checkpoint_paths = tuple(
        path for path in changed_files if "/output/checkpoints/" in path.as_posix()
    )
    output_paths = tuple(
        path
        for path in changed_files
        if "/output/control/" not in path.as_posix()
        and "/output/checkpoints/" not in path.as_posix()
    )
    output_artifacts = _file_artifacts(output_paths, root=data_root)
    result_signature = (
        hashlib.sha256(
            json.dumps(
                {
                    "terminal_events": terminal_events,
                    "metrics_snapshot": metrics,
                    "details": details,
                    "output_sha256": sorted(
                        artifact["sha256"] for artifact in output_artifacts
                    ),
                },
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest()
        if len(terminal_rows) == 1 and output_artifacts
        else ""
    )
    return AttemptEvidence(
        pipeline=pipeline,
        tracing=tracing,
        started_at=started_at,
        finished_at=finished_at,
        exit_code=exit_code,
        timed_out=timed_out,
        command=command,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        manifest_ids=manifest_ids,
        run_ids=run_ids,
        terminal_ledger_events=terminal_events,
        manifest_artifacts=_file_artifacts(manifest_paths, root=data_root),
        ledger_artifacts=_file_artifacts(ledger_paths, root=data_root),
        checkpoint_artifacts=_file_artifacts(checkpoint_paths, root=data_root),
        output_artifacts=output_artifacts,
        terminal_metrics_snapshot=metrics,
        terminal_details=details,
        result_signature=result_signature,
        run_mode=run_mode,
    )


def _tracing_values(mode: str) -> tuple[bool, ...]:
    if mode == "off":
        return (False,)
    if mode == "on":
        return (True,)
    return (False, True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--canonical-data-root", type=Path)
    parser.add_argument("--canonical-log-root", type=Path)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--tracing-mode", choices=("off", "on", "both"), default="both")
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--residual-limitation", action="append", default=[])
    parser.add_argument("--finding-id", action="append", default=[])
    parser.add_argument("--execute", action="store_true")
    return parser


def _planned_attempts(
    pipelines: tuple[str, ...], mode: str
) -> list[dict[str, str | bool]]:
    return [
        {"pipeline": pipeline, "tracing": tracing}
        for pipeline in pipelines
        for tracing in _tracing_values(mode)
    ]


def _source_provenance(repo_root: Path) -> dict[str, object]:
    revision = subprocess.run(  # nosec B603
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    tree = subprocess.run(  # nosec B603
        ["git", "rev-parse", "HEAD^{tree}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    status = subprocess.run(  # nosec B603
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    dirty_entries = tuple(line for line in status.stdout.splitlines() if line.strip())
    return {
        "revision": revision.stdout.strip(),
        "tree": tree.stdout.strip(),
        "clean": not dirty_entries,
        "dirty_entries": dirty_entries,
    }


def _source_revision(repo_root: Path) -> str:
    return str(_source_provenance(repo_root)["revision"])


def _parse_generated_at(value: object) -> bool:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _validate_summary(key: str, summary: object) -> list[str]:
    if not isinstance(summary, dict):
        return ["summary must be an object"]
    errors: list[str] = []
    for field_name, expected in EVIDENCE_SUMMARY_REQUIREMENTS[key].items():
        value = summary.get(field_name)
        if type(value) is not int:
            errors.append(f"summary.{field_name} must be an integer")
        elif (
            field_name.endswith(
                (
                    "count",
                    "mismatch_count",
                    "failure_count",
                    "unstable_count",
                    "drift_count",
                    "missing_count",
                )
            )
            and expected == 0
        ):
            if value != 0:
                errors.append(f"summary.{field_name} must equal 0")
        elif value < expected:
            errors.append(f"summary.{field_name} must be >= {expected}")
    return errors


def _validate_evidence_producer(key: str, producer: object) -> list[str]:
    if not isinstance(producer, dict):
        return ["producer must be an object"]
    errors: list[str] = []
    command = producer.get("command")
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(item, str) and item.strip() for item in command)
    ):
        errors.append("producer.command must be a non-empty string array")
    if producer.get("exit_code") != 0:
        errors.append("producer.exit_code must equal 0")
    if key == "promtool" and producer.get("tool_version") != "3.13.1":
        errors.append("producer.tool_version must equal pinned 3.13.1")
    return errors


def _validate_evidence_assertions(assertions: object) -> list[str]:
    if not isinstance(assertions, list) or not assertions:
        return ["assertions must be a non-empty array"]
    errors: list[str] = []
    for index, assertion in enumerate(assertions):
        if not isinstance(assertion, dict):
            errors.append(f"assertions[{index}] must be an object")
            continue
        if not str(assertion.get("name") or "").strip():
            errors.append(f"assertions[{index}].name must be non-empty")
        if assertion.get("status") != "pass":
            errors.append(f"assertions[{index}].status must equal pass")
        if assertion.get("actual") != assertion.get("expected"):
            errors.append(f"assertions[{index}] actual must equal expected")
    return errors


def _validate_raw_artifacts(
    key: str,
    raw_artifacts: object,
    *,
    raw_root: Path,
) -> tuple[list[str], list[dict[str, str]]]:
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        return ["raw_artifacts must be a non-empty array"], []
    errors: list[str] = []
    retained: list[dict[str, str]] = []
    kind_counts: dict[str, int] = {}
    seen_paths: set[Path] = set()
    for index, artifact in enumerate(raw_artifacts):
        if not isinstance(artifact, dict):
            errors.append(f"raw_artifacts[{index}] must be an object")
            continue
        path = Path(str(artifact.get("path") or "")).expanduser().resolve()
        kind = str(artifact.get("kind") or "").strip()
        expected_sha256 = str(artifact.get("sha256") or "").strip()
        if raw_root not in path.parents:
            errors.append(
                f"raw_artifacts[{index}] must be inside AUDIT_ROOT/evidence/raw"
            )
        if path in seen_paths:
            errors.append(f"raw_artifacts[{index}] duplicates another raw artifact")
        seen_paths.add(path)
        if not path.is_file():
            errors.append(f"raw_artifacts[{index}] is not a file")
            continue
        actual_sha256 = _sha256_file(path)
        if expected_sha256 != actual_sha256:
            errors.append(f"raw_artifacts[{index}].sha256 does not match content")
        if not kind:
            errors.append(f"raw_artifacts[{index}].kind must be non-empty")
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        retained.append({"path": str(path), "sha256": actual_sha256, "kind": kind})
    for kind, minimum in EVIDENCE_RAW_KIND_REQUIREMENTS[key].items():
        if kind_counts.get(kind, 0) < minimum:
            errors.append(f"raw artifact kind {kind!r} requires at least {minimum}")
    return errors, retained


def _json_payloads_by_kind(
    retained: list[dict[str, str]], kind: str
) -> tuple[list[dict[str, object]], list[str]]:
    payloads: list[dict[str, object]] = []
    errors: list[str] = []
    for artifact in retained:
        if artifact["kind"] != kind:
            continue
        path = Path(artifact["path"])
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"{kind} artifact must be valid JSON: {exc}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"{kind} artifact payload must be an object")
            continue
        payloads.append(payload)
    return payloads, errors


def _validate_tracing_raw(retained: list[dict[str, str]]) -> list[str]:
    payloads, errors = _json_payloads_by_kind(retained, "attempt-result")
    if len(payloads) != 2:
        return [*errors, "tracing parity requires exactly two attempt results"]
    pipelines = {str(payload.get("pipeline") or "") for payload in payloads}
    tracing_modes = {payload.get("tracing") for payload in payloads}
    statuses = {payload.get("status") for payload in payloads}
    signatures = {str(payload.get("data_signature") or "") for payload in payloads}
    if len(pipelines) != 1 or "" in pipelines:
        errors.append("tracing attempts must describe one non-empty pipeline")
    if tracing_modes != {False, True}:
        errors.append("tracing attempts must contain explicit OFF and ON results")
    if statuses != {"success"}:
        errors.append("tracing attempt statuses must both equal success")
    if len(signatures) != 1 or "" in signatures:
        errors.append("tracing attempt data signatures must be identical and non-empty")
    decision_traces = [payload.get("decision_trace") for payload in payloads]
    if not any(isinstance(trace, list) and trace for trace in decision_traces):
        errors.append(
            "at least one tracing attempt requires a non-empty decision trace"
        )
    return errors


def _validate_metric_reconciliation_raw(
    retained: list[dict[str, str]],
) -> list[str]:
    prometheus, errors = _json_payloads_by_kind(retained, "prometheus-response")
    ledgers, ledger_errors = _json_payloads_by_kind(retained, "ledger-snapshot")
    errors.extend(ledger_errors)
    if not prometheus or any(
        payload.get("status") != "success" for payload in prometheus
    ):
        errors.append("Prometheus reconciliation responses must report status=success")
    if not ledgers or any(
        not isinstance(payload.get("events"), list) for payload in ledgers
    ):
        errors.append("ledger reconciliation snapshots must contain events")
    for payload in (*prometheus, *ledgers):
        if payload.get("expected") != payload.get("actual"):
            errors.append("metric reconciliation raw expected/actual values must match")
    return errors


def _validate_workflow_raw(retained: list[dict[str, str]]) -> list[str]:
    parents, errors = _json_payloads_by_kind(retained, "workflow-result")
    children, child_errors = _json_payloads_by_kind(retained, "child-result")
    errors.extend(child_errors)
    parent_ids = {
        str(payload.get("workflow_run_id") or "")
        for payload in parents
        if str(payload.get("workflow_run_id") or "")
    }
    statuses = {payload.get("status") for payload in parents}
    if len(parent_ids) < 2 or not {"success", "failed"}.issubset(statuses):
        errors.append(
            "workflow raw evidence requires distinct success and failure parents"
        )
    for child in children:
        if str(child.get("workflow_run_id") or "") not in parent_ids:
            errors.append("child workflow_run_id must resolve to a retained parent")
        for field_name in (
            "run_id",
            "manifest_id",
            "workflow_name",
            "workflow_step_id",
        ):
            if not str(child.get(field_name) or "").strip():
                errors.append(f"child {field_name} must be non-empty")
        if child.get("terminal_event") not in TERMINAL_EVENTS:
            errors.append("child terminal_event must be run_finished or run_failed")
    return errors


def _validate_inventory_raw(retained: list[dict[str, str]]) -> list[str]:
    payloads, errors = _json_payloads_by_kind(retained, "inventory-report")
    if len(payloads) != 1:
        return [*errors, "metric surface requires exactly one inventory report"]
    payload = payloads[0]
    outputs = payload.get("recording_rule_outputs")
    if not isinstance(outputs, list) or len(set(map(str, outputs))) < 103:
        errors.append("inventory must retain at least 103 unique recording outputs")
    for field_name in (
        "recording_declarations_without_output",
        "recording_outputs_without_declaration",
        "prometheus_run_id_selector_violations",
    ):
        if payload.get(field_name) != []:
            errors.append(f"inventory {field_name} must be empty")
    return errors


def _validate_dashboard_raw(retained: list[dict[str, str]]) -> list[str]:
    payloads, errors = _json_payloads_by_kind(retained, "dashboard-variable-report")
    dashboard_ids: set[str] = set()
    for payload in payloads:
        uid = str(payload.get("dashboard_uid") or "")
        if not uid or uid in dashboard_ids:
            errors.append("dashboard variable reports require unique non-empty UIDs")
        dashboard_ids.add(uid)
        pipelines = payload.get("pipelines")
        exclusion = str(payload.get("eligibility_exclusion") or "").strip()
        if pipelines != list(CHEMBL_PIPELINES) and not exclusion:
            errors.append(
                "dashboard variables require 15 canonical IDs or an exclusion"
            )
    if len(dashboard_ids) < 8:
        errors.append("dashboard variable evidence requires eight dashboards")
    return errors


def _validate_zero_raw(retained: list[dict[str, str]]) -> list[str]:
    payloads, errors = _json_payloads_by_kind(retained, "raw-zero-source")
    for payload in payloads:
        value = payload.get("value")
        if (
            payload.get("source_present") is not True
            or payload.get("state") != "present"
        ):
            errors.append(
                "numeric zero requires a present raw source and present state"
            )
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value != 0:
            errors.append("raw zero evidence value must be finite numeric zero")
    return errors


def _validate_scrape_raw(retained: list[dict[str, str]]) -> list[str]:
    payloads, errors = _json_payloads_by_kind(retained, "target-capture")
    target_ids: set[str] = set()
    for payload in payloads:
        target_id = str(payload.get("target_id") or "")
        if not target_id or target_id in target_ids:
            errors.append("target captures require unique non-empty target_id values")
        target_ids.add(target_id)
        if payload.get("scrape_interval_elapsed") is not True:
            errors.append("target capture must follow a complete scrape interval")
        if not _parse_generated_at(payload.get("captured_at")):
            errors.append("target capture requires timezone-aware captured_at")
        if payload.get("raw_value") != payload.get("expected_value"):
            errors.append("target raw and independently expected values must match")
    if len(target_ids) < 213:
        errors.append("scrape evidence requires 213 unique executable targets")
    return errors


def _validate_render_raw(retained: list[dict[str, str]]) -> list[str]:
    manifests, errors = _json_payloads_by_kind(retained, "render-manifest")
    screenshots = [row for row in retained if row["kind"] == "screenshot"]
    screenshot_hashes: set[str] = set()
    for screenshot in screenshots:
        path = Path(screenshot["path"])
        if not path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            errors.append("retained screenshot must be a PNG artifact")
        screenshot_hashes.add(screenshot["sha256"])
    captures: set[tuple[str, int]] = set()
    stable_windows: set[str] = set()
    for payload in manifests:
        uid = str(payload.get("dashboard_uid") or "")
        render_index = payload.get("render_index")
        if not uid or type(render_index) is not int:
            errors.append(
                "render manifest requires dashboard_uid and integer render_index"
            )
            continue
        captures.add((uid, render_index))
        stable_windows.add(str(payload.get("stable_window_id") or ""))
        if payload.get("status") != "success":
            errors.append("render manifest status must equal success")
        if payload.get("screenshot_sha256") not in screenshot_hashes:
            errors.append(
                "render manifest screenshot hash must resolve to retained PNG"
            )
    dashboards = {uid for uid, _index in captures}
    if len(dashboards) < 8 or len(captures) < 16:
        errors.append("render evidence requires eight dashboards rendered twice")
    if len(stable_windows) != 1 or "" in stable_windows:
        errors.append("all renders must share one non-empty stable monitoring window")
    return errors


def _validate_promtool_raw(retained: list[dict[str, str]]) -> list[str]:
    payloads, errors = _json_payloads_by_kind(retained, "promtool-output")
    phases = {str(payload.get("phase") or "") for payload in payloads}
    expected_phases = {"check-observability", "check-control-plane", "test-fixtures"}
    if phases != expected_phases:
        errors.append(
            "promtool evidence requires both checks and the fixture test phase"
        )
    for payload in payloads:
        if (
            payload.get("tool_version") != "3.13.1"
            or payload.get("exit_code") != 0
            or "SUCCESS" not in str(payload.get("output") or "")
        ):
            errors.append("promtool raw output must prove pinned successful execution")
    return errors


def _validate_online_raw(retained: list[dict[str, str]]) -> list[str]:
    runs, errors = _json_payloads_by_kind(retained, "online-run-result")
    instrumentation, metric_errors = _json_payloads_by_kind(
        retained, "instrumentation-response"
    )
    errors.extend(metric_errors)
    if len(runs) != 1:
        errors.append("online evidence requires exactly one designated run")
    else:
        run = runs[0]
        if (
            run.get("status") != "success"
            or run.get("cached_mode") is not False
            or run.get("terminal_event") != "run_finished"
        ):
            errors.append("online run must be successful, uncached, and terminal")
        for field_name in ("run_id", "manifest_id"):
            if not str(run.get(field_name) or "").strip():
                errors.append(f"online run {field_name} must be non-empty")
    required_metrics = {
        "bioetl_adapter_requests_total",
        "bioetl_data_source_retries_total",
        "bioetl_rate_limiter_tokens_available",
        "bioetl_circuit_breaker_state",
        "bioetl_adapter_request_duration_seconds",
    }
    metric_names: set[str] = set()
    for payload in instrumentation:
        metrics = payload.get("metrics")
        if (
            not isinstance(metrics, dict)
            or payload.get("raw_source_present") is not True
        ):
            errors.append("online instrumentation requires a present raw metric source")
            continue
        metric_names.update(str(name) for name in metrics)
    if not required_metrics.issubset(metric_names):
        errors.append(
            "online instrumentation is missing API/retry/rate-limit/circuit metrics"
        )
    return errors


def _validate_raw_content(key: str, retained: list[dict[str, str]]) -> list[str]:
    validators = {
        "tracing_parity": _validate_tracing_raw,
        "metric_reconciliation": _validate_metric_reconciliation_raw,
        "workflow_correlation": _validate_workflow_raw,
        "metric_surface": _validate_inventory_raw,
        "dashboard_variables": _validate_dashboard_raw,
        "zero_evidence": _validate_zero_raw,
        "scrape_targets": _validate_scrape_raw,
        "render_stability": _validate_render_raw,
        "promtool": _validate_promtool_raw,
        "online_run": _validate_online_raw,
    }
    return validators[key](retained)


def _evidence_gate(
    evidence: dict[str, str],
    *,
    audit_root: Path,
    source_revision: str,
) -> dict[str, object]:
    errors: dict[str, list[str]] = {}
    evidence_root = (audit_root / "evidence").resolve()
    resolved_paths = [Path(value).resolve() for value in evidence.values()]
    if len(set(resolved_paths)) != len(resolved_paths):
        errors["_paths"] = ["each evidence type requires a unique artifact"]
    unexpected_keys = sorted(set(evidence) - set(REQUIRED_EXTERNAL_EVIDENCE))
    if unexpected_keys:
        errors["_keys"] = ["unexpected evidence types: " + ", ".join(unexpected_keys)]
    artifacts: dict[str, dict[str, str]] = {}
    raw_artifacts_retained: dict[str, list[dict[str, str]]] = {}
    summaries: dict[str, dict[str, int]] = {}
    raw_root = (evidence_root / "raw").resolve()
    for key in REQUIRED_EXTERNAL_EVIDENCE:
        key_errors: list[str] = []
        raw_path = evidence.get(key)
        if raw_path is None:
            errors[key] = ["missing evidence artifact"]
            continue
        path = Path(raw_path).resolve()
        if evidence_root not in path.parents:
            key_errors.append("artifact must be inside AUDIT_ROOT/evidence")
        if not path.is_file():
            key_errors.append("artifact is not a file")
            errors[key] = key_errors
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors[key] = [f"invalid JSON: {exc}"]
            continue
        if not isinstance(payload, dict):
            key_errors.append("payload must be an object")
        else:
            if payload.get("schema_version") != 1:
                key_errors.append("schema_version must equal 1")
            if payload.get("evidence_type") != key:
                key_errors.append(f"evidence_type must equal {key}")
            if payload.get("status") != "pass":
                key_errors.append("status must equal pass")
            if payload.get("source_revision") != source_revision:
                key_errors.append("source_revision does not match campaign revision")
            if not _parse_generated_at(payload.get("generated_at")):
                key_errors.append("generated_at must be timezone-aware ISO-8601")
            key_errors.extend(_validate_summary(key, payload.get("summary")))
            if isinstance(payload.get("summary"), dict):
                summaries[key] = {
                    str(field): value
                    for field, value in payload["summary"].items()
                    if isinstance(field, str) and type(value) is int
                }
            key_errors.extend(_validate_evidence_producer(key, payload.get("producer")))
            key_errors.extend(_validate_evidence_assertions(payload.get("assertions")))
            raw_errors, retained = _validate_raw_artifacts(
                key,
                payload.get("raw_artifacts"),
                raw_root=raw_root,
            )
            key_errors.extend(raw_errors)
            if not raw_errors:
                key_errors.extend(_validate_raw_content(key, retained))
            raw_artifacts_retained[key] = retained
        if key_errors:
            errors[key] = key_errors
        artifacts[key] = {"path": str(path), "sha256": _sha256_file(path)}
    return {
        "satisfied": not errors,
        "errors": errors,
        "artifacts": artifacts,
        "raw_artifacts": raw_artifacts_retained,
        "summaries": summaries,
    }


def _scorecard(external_gate: dict[str, object]) -> dict[str, dict[str, float]]:
    summaries = external_gate.get("summaries")
    typed = summaries if isinstance(summaries, dict) else {}
    score_fields = {
        "dashboard_quality": ("render_stability", "dashboard_quality_score_x100", 4232),
        "metric_quality": ("metric_surface", "metric_quality_score_x100", 4600),
        "chembl_population": (
            "tracing_parity",
            "chembl_population_score_x100",
            4321,
        ),
        "overall_observability": (
            "online_run",
            "overall_observability_score_x100",
            4600,
        ),
    }
    scorecard: dict[str, dict[str, float]] = {}
    for name, (category, field_name, baseline_x100) in score_fields.items():
        category_summary = typed.get(category)
        current_x100 = (
            category_summary.get(field_name)
            if isinstance(category_summary, dict)
            else None
        )
        current = float(current_x100) / 100 if type(current_x100) is int else 0.0
        baseline = baseline_x100 / 100
        scorecard[name] = {
            "baseline": baseline,
            "current": current,
            "delta": round(current - baseline, 2),
        }
    return scorecard


def _residual_findings_gate(
    limitations: list[str], finding_specs: list[str]
) -> dict[str, object]:
    errors: list[str] = []
    mappings: list[dict[str, str]] = []
    if len(limitations) != len(finding_specs):
        errors.append("each residual limitation requires exactly one finding issue")
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for index, limitation in enumerate(limitations):
        if not limitation.strip():
            errors.append(f"residual limitation {index} must be non-empty")
        if index >= len(finding_specs):
            continue
        finding_id, separator, issue_url = finding_specs[index].partition("=")
        if not separator or not re.fullmatch(r"[A-Z][A-Z0-9-]+-\d{3}", finding_id):
            errors.append(f"finding {index} must use FINDING-ID=https://.../issues/N")
            continue
        if not re.fullmatch(
            r"https://github\.com/SatoryKono/BioactivityDataAcquisition/issues/\d+",
            issue_url,
        ):
            errors.append(f"finding {index} must reference a BioETL GitHub issue URL")
            continue
        if finding_id in seen_ids or issue_url in seen_urls:
            errors.append("finding IDs and issue URLs must be unique")
        seen_ids.add(finding_id)
        seen_urls.add(issue_url)
        mappings.append(
            {
                "limitation": limitation,
                "finding_id": finding_id,
                "issue_url": issue_url,
            }
        )
    return {"satisfied": not errors, "errors": errors, "mappings": mappings}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = _repo_root()
    audit_root = args.audit_root.expanduser()
    canonical_roots = tuple(
        path
        for path in (args.canonical_data_root, args.canonical_log_root)
        if path is not None
    )
    try:
        evidence = _parse_evidence(args.evidence)
        if args.execute and len(canonical_roots) != 2:
            raise ValueError(
                "--execute requires --canonical-data-root and --canonical-log-root"
            )
        _validate_roots(audit_root, canonical_roots)
        if args.execute:
            assert args.canonical_data_root is not None
            assert args.canonical_log_root is not None
            _validate_canonical_layout(
                args.canonical_data_root,
                args.canonical_log_root,
            )
            _validate_fresh_audit_root(audit_root)
        source_provenance = _source_provenance(repo_root)
        if args.execute and not source_provenance["clean"]:
            raise ValueError(
                "--execute requires a clean tracked and untracked source tree"
            )
        registered_pipelines, registry_completed = _registry_pipeline_command(
            repo_root,
            python=args.python.expanduser().absolute(),
        )
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True))
        return 2
    pipelines = _discover_chembl_pipelines(repo_root)
    parity_ok = pipelines == registered_pipelines == CHEMBL_PIPELINES
    planned = _planned_attempts(pipelines, args.tracing_mode)
    source_revision = str(source_provenance["revision"])
    external_gate = _evidence_gate(
        evidence,
        audit_root=audit_root,
        source_revision=source_revision,
    )
    scorecard = _scorecard(external_gate)
    residual_finding_gate = _residual_findings_gate(
        args.residual_limitation,
        args.finding_id,
    )
    if not args.execute:
        payload = {
            "status": "planned",
            "pipeline_config_parity": parity_ok,
            "pipelines": list(pipelines),
            "registered_pipelines": list(registered_pipelines),
            "attempts": planned,
            "source_revision": source_revision,
            "source_provenance": source_provenance,
            "registry_command": list(registry_completed.args),
            "registry_stdout": registry_completed.stdout,
            "external_evidence_gate": external_gate,
            "scorecard": scorecard,
            "residual_limitations": args.residual_limitation,
            "finding_ids": args.finding_id,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if parity_ok else 1
    audit_root.mkdir(parents=True, exist_ok=True)
    registry_evidence_root = audit_root / "evidence" / "raw"
    registry_evidence_root.mkdir(parents=True, exist_ok=True)
    registry_stdout_path = registry_evidence_root / "registry-command.stdout"
    registry_stdout_path.write_text(registry_completed.stdout, encoding="utf-8")
    before = {str(path.resolve()): _tree_signature(path) for path in canonical_roots}
    assert args.canonical_data_root is not None
    cached_bronze_root = args.canonical_data_root.resolve() / "output" / "bronze"
    attempts: list[AttemptEvidence] = []
    for item in planned:
        attempts.append(
            _run_attempt(
                repo_root=repo_root,
                audit_root=audit_root,
                python=args.python.expanduser().absolute(),
                pipeline=str(item["pipeline"]),
                limit=args.limit,
                tracing=bool(item["tracing"]),
                timeout_seconds=args.timeout_seconds,
                cached_bronze_root=cached_bronze_root,
            )
        )
    online_attempt = _run_attempt(
        repo_root=repo_root,
        audit_root=audit_root,
        python=args.python.expanduser().absolute(),
        pipeline="chembl_activity",
        limit=args.limit,
        tracing=False,
        timeout_seconds=args.timeout_seconds,
        cached_bronze_root=None,
        run_mode="online",
    )
    workflow_phase_root = audit_root / "phases" / "chembl-baseline"
    workflow_phase = _run_phase_command(
        name="chembl_baseline",
        command=_workflow_baseline_command(
            python=args.python.expanduser().absolute(),
            limit=args.limit,
            cached_bronze_root=cached_bronze_root,
        ),
        repo_root=repo_root,
        phase_root=workflow_phase_root,
        data_root=workflow_phase_root / "data",
        timeout_seconds=args.timeout_seconds,
    )
    failure_phase_root = audit_root / "phases" / "workflow-failure-cases"
    failure_phase = _run_phase_command(
        name="workflow_failure_and_dq_hard_failure",
        command=_workflow_failure_tests_command(
            python=args.python.expanduser().absolute()
        ),
        repo_root=repo_root,
        phase_root=failure_phase_root,
        data_root=failure_phase_root / "data",
        timeout_seconds=args.timeout_seconds,
    )
    phases = (workflow_phase, failure_phase)
    after = {str(path.resolve()): _tree_signature(path) for path in canonical_roots}
    canonical_unchanged = before == after
    expected_attempt_keys = {
        (pipeline, tracing)
        for pipeline in CHEMBL_PIPELINES
        for tracing in (False, True)
    }
    actual_attempt_keys = {(attempt.pipeline, attempt.tracing) for attempt in attempts}
    tracing_pairs = {
        pipeline: {
            attempt.tracing: attempt.result_signature
            for attempt in attempts
            if attempt.pipeline == pipeline
        }
        for pipeline in CHEMBL_PIPELINES
    }
    tracing_pair_gate = all(
        set(pair) == {False, True} and bool(pair[False]) and pair[False] == pair[True]
        for pair in tracing_pairs.values()
    )
    attempt_gate = bool(
        args.tracing_mode == "both"
        and actual_attempt_keys == expected_attempt_keys
        and len(attempts) == len(expected_attempt_keys)
        and all(attempt.satisfies_closure for attempt in attempts)
        and tracing_pair_gate
    )
    complete = bool(
        parity_ok
        and canonical_unchanged
        and attempt_gate
        and online_attempt.satisfies_closure
        and all(phase.satisfies_closure for phase in phases)
        and external_gate["satisfied"]
        and residual_finding_gate["satisfied"]
    )
    report = {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "source_revision": source_revision,
        "source_provenance": source_provenance,
        "status": "complete" if complete else "incomplete",
        "pipeline_config_parity": parity_ok,
        "pipelines": list(pipelines),
        "registered_pipelines": list(registered_pipelines),
        "registry_command_evidence": {
            "command": list(registry_completed.args),
            "stdout_path": str(registry_stdout_path),
            "stdout_sha256": _sha256_file(registry_stdout_path),
        },
        "attempt_gate": {
            "satisfied": attempt_gate,
            "attempt_count": len(attempts),
            "required_tracing_mode": "both",
            "actual_tracing_mode": args.tracing_mode,
            "tracing_result_parity": tracing_pair_gate,
            "tracing_result_signatures": tracing_pairs,
        },
        "attempts": [asdict(item) for item in attempts],
        "online_attempt_gate": {
            "satisfied": online_attempt.satisfies_closure,
            "attempt": asdict(online_attempt),
        },
        "workflow_phase_gate": {
            "satisfied": all(phase.satisfies_closure for phase in phases),
            "phases": [asdict(phase) for phase in phases],
        },
        "canonical_signature_gate": {
            "satisfied": canonical_unchanged,
            "before": before,
            "after": after,
        },
        "external_evidence_gate": external_gate,
        "scorecard": scorecard,
        "residual_limitations": args.residual_limitation,
        "finding_ids": args.finding_id,
        "residual_finding_gate": residual_finding_gate,
    }
    output_path = audit_root / "observability-closure-campaign.json"
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"status": report["status"], "report": str(output_path)}, sort_keys=True
        )
    )
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
