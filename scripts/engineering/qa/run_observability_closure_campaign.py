#!/usr/bin/env python3
"""Run a bounded, evidence-gated observability closure campaign.

The runner never edits a dotenv file. Pipeline processes receive explicit
isolated data and log paths through their process environment, while tracked
configuration is resolved from the checkout containing this script.
"""

from __future__ import annotations

import argparse
import csv
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
    "backend_profile",
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
    "backend_profile": {
        "http_root_match_count": 1,
        "loki_match_count": 1,
        "canonical_mismatch_count": 0,
    },
}

EVIDENCE_RAW_KIND_REQUIREMENTS: dict[str, dict[str, int]] = {
    "tracing_parity": {"attempt-result": 30},
    "metric_reconciliation": {
        "prometheus-response": 15,
        "ledger-snapshot": 15,
        "dq-anomaly-response": 1,
    },
    "workflow_correlation": {"workflow-result": 2, "child-result": 2},
    "metric_surface": {"inventory-report": 1},
    "dashboard_variables": {"dashboard-variable-report": 8},
    "zero_evidence": {"raw-zero-source": 4},
    "scrape_targets": {"target-capture": 213},
    "render_stability": {"render-manifest": 16, "screenshot": 16},
    "promtool": {"promtool-output": 3},
    "online_run": {"online-run-result": 1, "instrumentation-response": 1},
    "backend_profile": {
        "backend-http-response": 1,
        "loki-response": 1,
        "canonical-signature": 1,
    },
}

TERMINAL_EVENTS = frozenset({"run_finished", "run_failed"})
CANONICAL_EVIDENCE_ASSEMBLER = (
    "scripts.engineering.qa.assemble_observability_closure_evidence"
)


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
    checkpoint_disposition: str = ""
    checkpoint_interval: int | None = None
    output_artifacts: tuple[dict[str, str], ...] = ()
    semantic_output_records: int = 0
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
            and (
                bool(self.checkpoint_artifacts)
                or self.checkpoint_disposition == "not_applicable_below_interval"
            )
            and bool(self.output_artifacts)
            and self.semantic_output_records > 0
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
    expected_outcome: str = "success"

    @property
    def satisfies_closure(self) -> bool:
        exit_matches = (
            self.exit_code == 0
            if self.expected_outcome == "success"
            else self.exit_code != 0
        )
        return exit_matches and not self.timed_out


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
        timeout=900,
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


_OCCURRENCE_FIELDS = frozenset(
    {
        "_ingestion_ts",
        "ingestion_ts",
        "_run_id",
        "run_id",
        "manifest_id",
        "created_at",
        "updated_at",
    }
)


def _semantic_value(value: object) -> object:
    """Remove per-occurrence identity while retaining business data semantics."""
    if isinstance(value, dict):
        return {
            str(key): _semantic_value(item)
            for key, item in value.items()
            if str(key) not in _OCCURRENCE_FIELDS
        }
    if isinstance(value, (list, tuple)):
        return [_semantic_value(item) for item in value]
    return value


def _output_layer(path: Path) -> str:
    parts = path.parts
    try:
        return parts[parts.index("output") + 1]
    except (ValueError, IndexError):
        return "unknown"


def _semantic_rows_from_path(path: Path) -> list[object]:
    """Read business rows from a supported output artifact."""
    if "_delta_log" in path.parts:
        return []
    try:
        if path.suffix == ".parquet":
            import pyarrow.parquet as parquet

            return [
                _semantic_value(row) for row in parquet.read_table(path).to_pylist()
            ]
        if path.suffix == ".jsonl":
            return [
                _semantic_value(json.loads(line))
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        if path.suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload if isinstance(payload, list) else [payload]
            return [_semantic_value(row) for row in rows]
        if path.suffix == ".csv":
            with path.open(encoding="utf-8", newline="") as stream:
                return [_semantic_value(row) for row in csv.DictReader(stream)]
    except (
        ImportError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ):
        return []
    return []


def _semantic_output_payload(
    paths: Iterable[Path],
) -> tuple[list[dict[str, object]], int]:
    """Return path-independent rows suitable for tracing parity comparison."""
    materialized = tuple(paths)
    parquet_paths = tuple(path for path in materialized if path.suffix == ".parquet")
    selected = parquet_paths or materialized
    payload: list[dict[str, object]] = []
    row_count = 0
    for path in selected:
        rows = _semantic_rows_from_path(path)
        if not rows:
            continue
        row_count += len(rows)
        payload.append(
            {
                "layer": _output_layer(path),
                "rows": sorted(
                    rows,
                    key=lambda row: json.dumps(row, sort_keys=True, default=str),
                ),
            }
        )
    payload.sort(key=lambda item: json.dumps(item, sort_keys=True, default=str))
    return payload, row_count


def _checkpoint_policy(
    repo_root: Path, pipeline: str, limit: int
) -> tuple[str, int | None]:
    """Classify checkpoint evidence against the configured record interval."""
    config_root = repo_root / "configs" / "entities" / "chembl"
    for path in sorted(config_root.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        if not re.search(
            rf"^\s*pipeline_name:\s*{re.escape(pipeline)}\s*$", text, re.MULTILINE
        ):
            continue
        intervals = [
            int(value)
            for value in re.findall(
                r"^\s*checkpoint_interval:\s*(\d+)\s*$", text, re.MULTILINE
            )
        ]
        interval = min(intervals) if intervals else None
        if interval is not None and limit < interval:
            return "not_applicable_below_interval", interval
        return "required", interval
    return "required", None


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
    expected_outcome: str = "success",
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
        expected_outcome=expected_outcome,
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


def _workflow_failure_command(
    *, python: Path, limit: int, empty_bronze_root: Path
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
        str(empty_bronze_root),
        "--no-tracing",
        "--no-ensure-observability-backend",
    )


def _dq_hard_failure_test_command(*, python: Path) -> tuple[str, ...]:
    return (
        str(python),
        "-m",
        "pytest",
        "-q",
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
    semantic_output, semantic_output_records = _semantic_output_payload(output_paths)
    checkpoint_disposition, checkpoint_interval = _checkpoint_policy(
        repo_root, pipeline, limit
    )
    if checkpoint_paths:
        checkpoint_disposition = "retained"
    result_signature = (
        hashlib.sha256(
            json.dumps(
                {
                    "terminal_events": terminal_events,
                    "metrics_snapshot": metrics,
                    "details": _semantic_value(details),
                    "semantic_output": semantic_output,
                },
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest()
        if len(terminal_rows) == 1 and semantic_output_records > 0
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
        checkpoint_disposition=checkpoint_disposition,
        checkpoint_interval=checkpoint_interval,
        output_artifacts=output_artifacts,
        semantic_output_records=semantic_output_records,
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--finalize-report", type=Path)
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
    if isinstance(command, list) and (
        len(command) < 6
        or command[1:3] != ["-m", CANONICAL_EVIDENCE_ASSEMBLER]
        or "--category" not in command
        or key not in command
    ):
        errors.append(
            "producer.command must use the canonical typed evidence assembler"
        )
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


def _validate_tracing_raw(
    retained: list[dict[str, str]],
    expected_binding: dict[str, object] | None = None,
) -> list[str]:
    payloads, errors = _json_payloads_by_kind(retained, "attempt-result")
    if len(payloads) != 30:
        return [*errors, "tracing parity requires exactly 30 attempt results"]
    pipelines = {str(payload.get("pipeline") or "") for payload in payloads}
    statuses = {payload.get("status") for payload in payloads}
    if pipelines != set(CHEMBL_PIPELINES):
        errors.append("tracing attempts must cover all 15 canonical pipelines")
    if statuses != {"success"}:
        errors.append("tracing attempt statuses must all equal success")
    for pipeline in CHEMBL_PIPELINES:
        pair = [payload for payload in payloads if payload.get("pipeline") == pipeline]
        modes = {payload.get("tracing") for payload in pair}
        signatures = {str(payload.get("data_signature") or "") for payload in pair}
        if len(pair) != 2 or modes != {False, True}:
            errors.append(f"{pipeline} requires explicit OFF and ON results")
        if len(signatures) != 1 or "" in signatures:
            errors.append(
                f"{pipeline} tracing data signatures must be identical and non-empty"
            )
    if expected_binding is not None:
        expected_attempts = expected_binding.get("standalone_attempts")
        expected_occurrences = (
            {
                (
                    str(item.get("pipeline") or ""),
                    item.get("tracing"),
                    str((item.get("run_ids") or [""])[0]),
                    str(item.get("result_signature") or ""),
                )
                for item in expected_attempts
                if isinstance(item, dict)
                and isinstance(item.get("run_ids"), list)
                and len(item["run_ids"]) == 1
            }
            if isinstance(expected_attempts, list)
            else set()
        )
        actual_occurrences = {
            (
                str(payload.get("pipeline") or ""),
                payload.get("tracing"),
                str(payload.get("run_id") or ""),
                str(payload.get("data_signature") or ""),
            )
            for payload in payloads
        }
        if actual_occurrences != expected_occurrences:
            errors.append("tracing raw results do not match executed run occurrences")
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
    dq_rows, dq_errors = _json_payloads_by_kind(retained, "dq-anomaly-response")
    errors.extend(ledger_errors)
    errors.extend(dq_errors)
    if len(prometheus) != 15 or len(ledgers) != 15:
        errors.append("metric reconciliation requires 15 Prometheus and 15 ledger rows")
    prom_by_key: dict[tuple[str, str], dict[str, object]] = {}
    ledger_by_key: dict[tuple[str, str], dict[str, object]] = {}
    for payload in prometheus:
        key = (str(payload.get("pipeline") or ""), str(payload.get("run_id") or ""))
        if not all(key) or key in prom_by_key:
            errors.append("Prometheus rows require unique pipeline/run_id anchors")
        prom_by_key[key] = payload
        if payload.get("status") != "success":
            errors.append(
                "Prometheus reconciliation responses must report status=success"
            )
        if payload.get("pipeline_runs_total_delta") != 1:
            errors.append(
                "each terminal run must increment pipeline_runs_total exactly once"
            )
        if payload.get("health_probe_counter_delta") != 0:
            errors.append("pipeline completion must not change health-probe counters")
    for payload in ledgers:
        key = (str(payload.get("pipeline") or ""), str(payload.get("run_id") or ""))
        if not all(key) or key in ledger_by_key:
            errors.append("ledger rows require unique pipeline/run_id anchors")
        ledger_by_key[key] = payload
        events = payload.get("events")
        terminal = (
            [
                event
                for event in events
                if isinstance(event, dict)
                and event.get("event_type") in TERMINAL_EVENTS
            ]
            if isinstance(events, list)
            else []
        )
        if len(terminal) != 1:
            errors.append(
                "each ledger snapshot must contain exactly one terminal event"
            )
        if payload.get("terminal_run_result_count") != 1:
            errors.append("each ledger snapshot must reconcile one terminal RunResult")
    if set(prom_by_key) != set(ledger_by_key):
        errors.append("Prometheus and ledger pipeline/run anchors must match exactly")
    if {pipeline for pipeline, _run_id in prom_by_key} != set(CHEMBL_PIPELINES):
        errors.append("metric reconciliation must cover all 15 canonical pipelines")
    if len(dq_rows) != 1:
        errors.append("metric reconciliation requires one focused DQ anomaly row")
    else:
        dq_row = dq_rows[0]
        if (
            dq_row.get("source_present") is not True
            or dq_row.get("metric") != "bioetl_dq_anomaly_detected"
            or dq_row.get("delta") != 1
            or not str(dq_row.get("test_node_id") or "").strip()
        ):
            errors.append(
                "focused DQ failure must increment one present anomaly metric"
            )
    return errors


def _validate_workflow_raw(retained: list[dict[str, str]]) -> list[str]:
    parents, errors = _json_payloads_by_kind(retained, "workflow-result")
    children, child_errors = _json_payloads_by_kind(retained, "child-result")
    errors.extend(child_errors)
    parent_ids: set[str] = set()
    statuses = {payload.get("status") for payload in parents}
    child_by_anchor: dict[tuple[str, str], dict[str, object]] = {}
    for child in children:
        for field_name in (
            "workflow_run_id",
            "run_id",
            "manifest_id",
            "workflow_name",
            "workflow_step_id",
        ):
            if not str(child.get(field_name) or "").strip():
                errors.append(f"child {field_name} must be non-empty")
        if child.get("terminal_event") not in TERMINAL_EVENTS:
            errors.append("child terminal_event must be run_finished or run_failed")
        anchor = (
            str(child.get("run_id") or ""),
            str(child.get("manifest_id") or ""),
        )
        if all(anchor):
            if anchor in child_by_anchor:
                errors.append("child run/manifest anchors must be unique")
            child_by_anchor[anchor] = child

    repeated_steps: dict[tuple[str, str], list[dict[str, object]]] = {}
    for parent in parents:
        for field_name in (
            "workflow_run_id",
            "workflow_name",
            "workflow_step_id",
            "child_run_id",
            "child_manifest_id",
        ):
            if not str(parent.get(field_name) or "").strip():
                errors.append(f"parent {field_name} must be non-empty")
        workflow_run_id = str(parent.get("workflow_run_id") or "")
        if workflow_run_id:
            parent_ids.add(workflow_run_id)
        repeated_steps.setdefault(
            (
                str(parent.get("workflow_name") or ""),
                str(parent.get("workflow_step_id") or ""),
            ),
            [],
        ).append(parent)
        anchor = (
            str(parent.get("child_run_id") or ""),
            str(parent.get("child_manifest_id") or ""),
        )
        child = child_by_anchor.get(anchor)
        if child is None:
            errors.append("parent child run/manifest anchors must resolve to a child")
            continue
        for field_name in (
            "workflow_run_id",
            "workflow_name",
            "workflow_step_id",
        ):
            if str(child.get(field_name) or "") != str(parent.get(field_name) or ""):
                errors.append(
                    f"parent/child {field_name} must match for reciprocal anchors"
                )

    if len(parent_ids) < 2 or not {"success", "failed"}.issubset(statuses):
        errors.append(
            "workflow raw evidence requires distinct success and failure parents"
        )
    for child in children:
        if str(child.get("workflow_run_id") or "") not in parent_ids:
            errors.append("child workflow_run_id must resolve to a retained parent")
    has_repeated_success_and_failure = any(
        len(
            {
                str(parent.get("workflow_run_id") or "")
                for parent in occurrences
                if str(parent.get("workflow_run_id") or "")
            }
        )
        >= 2
        and {"success", "failed"}.issubset(
            {parent.get("status") for parent in occurrences}
        )
        for (workflow_name, workflow_step_id), occurrences in repeated_steps.items()
        if workflow_name and workflow_step_id
    )
    if not has_repeated_success_and_failure:
        errors.append(
            "workflow raw evidence requires repeated success/failure runs for one step"
        )
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
        "policy_aliases_without_catalog",
        "catalog_aliases_without_declaration",
        "policy_aliases_overlapping_outputs",
        "http_semantics_violations",
        "panel_contract_drift",
        "prometheus_run_id_selector_violations",
    ):
        if payload.get(field_name) != []:
            errors.append(f"inventory {field_name} must be empty")
    aliases = payload.get("policy_alias_metrics")
    if not isinstance(aliases, list) or len(set(map(str, aliases))) != 20:
        errors.append("inventory must retain exactly 20 governed policy aliases")
    counts = payload.get("typed_target_counts")
    if counts != {
        "promql": 171,
        "http": 30,
        "loki": 5,
        "tempo": 0,
        "unknown": 0,
    }:
        errors.append("inventory typed target counts do not match shipped dashboards")
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


def _validate_online_raw(
    retained: list[dict[str, str]],
    expected_binding: dict[str, object] | None = None,
) -> list[str]:
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
        if expected_binding is not None and run.get("run_id") != expected_binding.get(
            "online_run_id"
        ):
            errors.append("online raw result does not match the executed online run")
    required_deltas = {
        "bioetl_adapter_requests_total": 1,
        "bioetl_rate_limiter_wait_seconds_count": 1,
        "bioetl_circuit_breaker_success_total": 1,
        "bioetl_adapter_request_duration_seconds_count": 1,
    }
    metric_rows: dict[str, dict[str, object]] = {}
    for payload in instrumentation:
        metrics = payload.get("metrics")
        if (
            not isinstance(metrics, dict)
            or payload.get("raw_source_present") is not True
        ):
            errors.append("online instrumentation requires a present raw metric source")
            continue
        for name, row in metrics.items():
            if isinstance(row, dict):
                metric_rows[str(name)] = row
    for metric_name, minimum_delta in required_deltas.items():
        row = metric_rows.get(metric_name, {})
        if row.get("source_present") is not True:
            errors.append(f"online metric {metric_name} requires a present raw source")
        delta = row.get("delta")
        if (
            not isinstance(delta, (int, float))
            or isinstance(delta, bool)
            or delta < minimum_delta
        ):
            errors.append(
                f"online metric {metric_name} delta must be >= {minimum_delta}"
            )
    retry_row = metric_rows.get("bioetl_data_source_retries_total", {})
    if retry_row.get("source_present") is not True or retry_row.get("delta") != 1:
        errors.append(
            "controlled online retry probe must increment retry metric exactly once"
        )
    return errors


def _validate_backend_profile_raw(retained: list[dict[str, str]]) -> list[str]:
    http_rows, errors = _json_payloads_by_kind(retained, "backend-http-response")
    loki_rows, loki_errors = _json_payloads_by_kind(retained, "loki-response")
    signatures, signature_errors = _json_payloads_by_kind(
        retained, "canonical-signature"
    )
    errors.extend(loki_errors)
    errors.extend(signature_errors)
    if len(http_rows) != 1:
        errors.append("backend profile requires exactly one retained HTTP response")
    else:
        row = http_rows[0]
        if (
            row.get("state") != "populated"
            or row.get("read_only_mount") is not True
            or not str(row.get("data_root") or "").strip()
            or int(row.get("record_count", 0)) < 1
        ):
            errors.append(
                "backend HTTP response must prove the exact populated read-only root"
            )
    if len(loki_rows) != 1:
        errors.append("backend profile requires exactly one retained Loki response")
    else:
        row = loki_rows[0]
        if (
            row.get("job") != "bioetl-audit"
            or row.get("sentinel_match_count") != 1
            or row.get("read_only_mount") is not True
            or not str(row.get("log_root") or "").strip()
        ):
            errors.append("Loki response must prove one bounded bioetl-audit sentinel")
    if len(signatures) != 1:
        errors.append("backend profile requires one canonical before/after signature")
    else:
        row = signatures[0]
        if row.get("before") != row.get("after") or row.get("unchanged") is not True:
            errors.append("canonical data/log signatures must remain unchanged")
    return errors


def _validate_raw_content(
    key: str,
    retained: list[dict[str, str]],
    expected_binding: dict[str, object] | None = None,
) -> list[str]:
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
        "backend_profile": _validate_backend_profile_raw,
    }
    if key == "tracing_parity":
        return _validate_tracing_raw(retained, expected_binding)
    if key == "online_run":
        return _validate_online_raw(retained, expected_binding)
    return validators[key](retained)


def _evidence_gate(
    evidence: dict[str, str],
    *,
    audit_root: Path,
    source_revision: str,
    expected_binding: dict[str, object] | None = None,
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
            if (
                expected_binding is not None
                and payload.get("campaign_binding") != expected_binding
            ):
                key_errors.append(
                    "campaign_binding does not match the executed campaign"
                )
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
                key_errors.extend(
                    _validate_raw_content(key, retained, expected_binding)
                )
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
    if limitations:
        errors.append(
            "residual limitations must be resolved before campaign completion"
        )
    return {"satisfied": not errors, "errors": errors, "mappings": mappings}


def _stable_sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


def _campaign_binding(
    *,
    source_provenance: dict[str, object],
    attempts: list[AttemptEvidence],
    online_attempt: AttemptEvidence,
    phases: tuple[PhaseEvidence, ...],
) -> dict[str, object]:
    """Bind external observations to one immutable execution occurrence."""
    standalone = [
        {
            "pipeline": attempt.pipeline,
            "tracing": attempt.tracing,
            "run_ids": list(attempt.run_ids),
            "result_signature": attempt.result_signature,
        }
        for attempt in sorted(attempts, key=lambda item: (item.pipeline, item.tracing))
    ]
    phase_payload = [
        {
            "name": phase.name,
            "command": list(phase.command),
            "stdout_sha256": phase.stdout_sha256,
            "stderr_sha256": phase.stderr_sha256,
        }
        for phase in phases
    ]
    return {
        "source_revision": source_provenance["revision"],
        "source_tree": source_provenance["tree"],
        "standalone_attempts_sha256": _stable_sha256(standalone),
        "standalone_attempts": standalone,
        "online_run_id": online_attempt.run_ids[0]
        if len(online_attempt.run_ids) == 1
        else "",
        "phase_evidence_sha256": _stable_sha256(phase_payload),
    }


def _retained_artifacts_valid(report: dict[str, object]) -> tuple[bool, list[str]]:
    """Re-hash execution artifacts before accepting separately produced evidence."""
    errors: list[str] = []

    def validate_artifact(artifact: object, label: str) -> None:
        if not isinstance(artifact, dict):
            errors.append(f"{label} must be an object")
            return
        path = Path(str(artifact.get("path") or ""))
        expected = str(artifact.get("sha256") or "")
        if not path.is_file():
            errors.append(f"{label} is missing")
        elif _sha256_file(path) != expected:
            errors.append(f"{label} hash changed after execution")

    attempts = report.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        errors.append("attempts must be a non-empty array")
    else:
        for attempt_index, attempt in enumerate(attempts):
            if not isinstance(attempt, dict):
                errors.append(f"attempts[{attempt_index}] must be an object")
                continue
            for field_name in (
                "manifest_artifacts",
                "ledger_artifacts",
                "checkpoint_artifacts",
                "output_artifacts",
            ):
                artifacts = attempt.get(field_name)
                if not isinstance(artifacts, list):
                    errors.append(
                        f"attempts[{attempt_index}].{field_name} must be an array"
                    )
                    continue
                for artifact_index, artifact in enumerate(artifacts):
                    validate_artifact(
                        artifact,
                        f"attempts[{attempt_index}].{field_name}[{artifact_index}]",
                    )
    workflow_gate = report.get("workflow_phase_gate")
    phases = workflow_gate.get("phases") if isinstance(workflow_gate, dict) else None
    if not isinstance(phases, list) or not phases:
        errors.append("workflow phase evidence is missing")
    else:
        for phase_index, phase in enumerate(phases):
            if not isinstance(phase, dict):
                errors.append(f"workflow phase {phase_index} must be an object")
                continue
            for stream_name in ("stdout", "stderr"):
                validate_artifact(
                    {
                        "path": phase.get(f"{stream_name}_path"),
                        "sha256": phase.get(f"{stream_name}_sha256"),
                    },
                    f"workflow phase {phase_index} {stream_name}",
                )
    return not errors, errors


def _finalize_campaign(
    *,
    args: argparse.Namespace,
    audit_root: Path,
    source_provenance: dict[str, object],
    evidence: dict[str, str],
) -> int:
    report_path = args.finalize_report.expanduser().resolve()
    expected_report_path = (
        audit_root / "observability-closure-campaign.json"
    ).resolve()
    if report_path != expected_report_path or not report_path.is_file():
        raise ValueError(
            "--finalize-report must name AUDIT_ROOT/observability-closure-campaign.json"
        )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("campaign report must be a schema_version=1 object")
    if payload.get("status") != "awaiting_external_evidence":
        raise ValueError("campaign report is not awaiting external evidence")
    if payload.get("source_revision") != source_provenance["revision"]:
        raise ValueError("campaign report source revision no longer matches HEAD")
    report_provenance = payload.get("source_provenance")
    if not isinstance(report_provenance, dict) or report_provenance.get(
        "tree"
    ) != source_provenance.get("tree"):
        raise ValueError("campaign report source tree no longer matches HEAD")
    retained_ok, retained_errors = _retained_artifacts_valid(payload)
    binding = payload.get("campaign_binding")
    if not isinstance(binding, dict):
        raise ValueError("campaign report has no occurrence binding")
    external_gate = _evidence_gate(
        evidence,
        audit_root=audit_root,
        source_revision=str(source_provenance["revision"]),
        expected_binding=binding,
    )
    residual_gate = _residual_findings_gate(args.residual_limitation, args.finding_id)
    core_gates = (
        payload.get("pipeline_config_parity") is True
        and isinstance(payload.get("attempt_gate"), dict)
        and payload["attempt_gate"].get("satisfied") is True
        and isinstance(payload.get("online_attempt_gate"), dict)
        and payload["online_attempt_gate"].get("satisfied") is True
        and isinstance(payload.get("workflow_phase_gate"), dict)
        and payload["workflow_phase_gate"].get("satisfied") is True
        and isinstance(payload.get("canonical_signature_gate"), dict)
        and payload["canonical_signature_gate"].get("satisfied") is True
    )
    complete = bool(
        source_provenance["clean"]
        and retained_ok
        and core_gates
        and external_gate["satisfied"]
        and residual_gate["satisfied"]
    )
    payload.update(
        {
            "generated_at": _utc_now(),
            "status": "complete" if complete else "incomplete",
            "external_evidence_gate": external_gate,
            "scorecard": _scorecard(external_gate),
            "retained_artifact_gate": {
                "satisfied": retained_ok,
                "errors": retained_errors,
            },
            "residual_limitations": args.residual_limitation,
            "finding_ids": args.finding_id,
            "residual_finding_gate": residual_gate,
        }
    )
    report_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": payload["status"], "report": str(report_path)}))
    return 0 if complete else 1


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
        if (args.execute or args.finalize_report is not None) and not source_provenance[
            "clean"
        ]:
            raise ValueError(
                "execution and finalization require a clean tracked and untracked source tree"
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
    if args.finalize_report is not None:
        try:
            return _finalize_campaign(
                args=args,
                audit_root=audit_root,
                source_provenance=source_provenance,
                evidence=evidence,
            )
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True))
            return 2
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
    failure_phase_root = audit_root / "phases" / "chembl-baseline-failure"
    empty_bronze_root = failure_phase_root / "empty-bronze"
    empty_bronze_root.mkdir(parents=True, exist_ok=True)
    failure_phase = _run_phase_command(
        name="chembl_baseline_expected_failure",
        command=_workflow_failure_command(
            python=args.python.expanduser().absolute(),
            limit=args.limit,
            empty_bronze_root=empty_bronze_root,
        ),
        repo_root=repo_root,
        phase_root=failure_phase_root,
        data_root=failure_phase_root / "data",
        timeout_seconds=args.timeout_seconds,
        expected_outcome="failure",
    )
    dq_phase_root = audit_root / "phases" / "dq-hard-failure"
    dq_phase = _run_phase_command(
        name="dq_hard_failure_boundary",
        command=_dq_hard_failure_test_command(
            python=args.python.expanduser().absolute()
        ),
        repo_root=repo_root,
        phase_root=dq_phase_root,
        data_root=dq_phase_root / "data",
        timeout_seconds=args.timeout_seconds,
    )
    phases = (workflow_phase, failure_phase, dq_phase)
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
    core_complete = bool(
        parity_ok
        and canonical_unchanged
        and attempt_gate
        and online_attempt.satisfies_closure
        and all(phase.satisfies_closure for phase in phases)
    )
    binding = _campaign_binding(
        source_provenance=source_provenance,
        attempts=attempts,
        online_attempt=online_attempt,
        phases=phases,
    )
    report = {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "source_revision": source_revision,
        "source_provenance": source_provenance,
        "status": "awaiting_external_evidence" if core_complete else "incomplete",
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
        "campaign_binding": binding,
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
    return 0 if core_complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
