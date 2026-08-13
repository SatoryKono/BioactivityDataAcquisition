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
import io
import json
import os
import re
import subprocess  # nosec B404 - command is assembled from fixed literals.
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
import zstandard

from bioetl.domain.mapping.organism_classification import classify_organism
from bioetl.domain.types import CellularityType
from bioetl.infrastructure.storage.support.atomic_ops import (
    atomic_write_bytes,
    atomic_write_text,
)

JSONL_ZST_SUFFIX = ".jsonl.zst"
OBSERVABILITY_CLOSURE_CAMPAIGN_REPORT = "observability-closure-campaign.json"
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

_RECORDED_SPECIAL_FIXTURES = frozenset(
    {
        "chembl_assay_parameters",
        "chembl_protein_class",
        "chembl_publication_similarity",
        "chembl_publication_term",
        "chembl_subcellular_fraction",
        "chembl_tissue",
    }
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

    @property
    def retains_attempt_evidence(self) -> bool:
        """Return whether an attempted run is fully attributable, success or failure."""
        return bool(
            self.command
            and self.started_at
            and self.finished_at
            and not self.timed_out
            and len(self.manifest_ids) == 1
            and len(self.run_ids) == 1
            and self.has_one_terminal_event
            and len(self.manifest_artifacts) == 1
            and len(self.ledger_artifacts) == 1
            and (
                bool(self.checkpoint_artifacts)
                or self.checkpoint_disposition == "not_applicable_below_interval"
            )
            and bool(self.output_artifacts)
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
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        (str((repo_root / "src").resolve()), str(repo_root.resolve()))
    )
    completed = subprocess.run(  # nosec B603
        command,
        cwd=repo_root,
        env=env,
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
    """Return a deterministic metadata-manifest signature for one canonical root.

    The canonical lake can contain large Parquet payloads.  Re-reading every byte
    before and after a bounded audit makes the safety gate dominate (and sometimes
    prevent) the campaign itself.  A manifest over every entry's relative path,
    mode, size, and nanosecond timestamps detects additions, removals, and
    ordinary mutations without streaming the complete lake twice.
    """
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing")
        return digest.hexdigest()
    paths = (root,) if root.is_file() else (root, *sorted(root.rglob("*")))
    for path in paths:
        relative = "." if path == root else path.relative_to(root).as_posix()
        try:
            stat_result = path.lstat()
        except FileNotFoundError:
            # A concurrently managed canonical lake may remove an entry between
            # directory enumeration and lstat().  Retain that observation in the
            # signature so the safety gate reports drift instead of losing the
            # complete campaign to an unhandled traceback.
            digest.update(relative.encode())
            digest.update(b"\0vanished-during-scan\n")
            continue
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(
            f"{stat_result.st_mode}:{stat_result.st_size}:"
            f"{stat_result.st_mtime_ns}:{stat_result.st_ctime_ns}".encode()
        )
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
    forbidden = ("data", "logs", "attempts", OBSERVABILITY_CLOSURE_CAMPAIGN_REPORT)
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
        "_source_batch_id",
        "_valid_from",
        "batch_id",
        "bronze_batch_id",
        "ingestion_ts",
        "_run_id",
        "run_id",
        "manifest_id",
        "effective_config_artifact_id",
        "effective_config_hash",
        "resolved_config_hash",
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
    business_paths = tuple(path for path in materialized if "control" not in path.parts)
    parquet_paths = tuple(path for path in business_paths if path.suffix == ".parquet")
    jsonl_paths = tuple(path for path in business_paths if path.suffix == ".jsonl")
    csv_paths = tuple(path for path in business_paths if path.suffix == ".csv")
    selected = parquet_paths or jsonl_paths or csv_paths
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


def _has_non_empty_decision_trace(attempt: AttemptEvidence) -> bool:
    adaptive = attempt.terminal_details.get("adaptive_memory")
    return bool(isinstance(adaptive, dict) and adaptive.get("decision_trace"))


def _timeout_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _isolated_subprocess_env(
    *, repo_root: Path, data_root: Path, log_path: Path
) -> dict[str, str]:
    """Build an environment whose code and writable roots are explicit."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        (str((repo_root / "src").resolve()), str(repo_root.resolve()))
    )
    env["BIOETL_DATA_DIR"] = str(data_root.resolve())
    env["BIOETL_LOG_FILE"] = str(log_path.resolve())
    return env


def _is_directory_link(path: Path) -> bool:
    """Return whether *path* is a symlink or Windows directory junction."""
    return path.is_symlink() or path.is_junction()


def _create_windows_directory_junction(*, link: Path, target: Path) -> None:
    """Create a directory junction without requiring symlink privileges."""
    command = (
        os.environ.get("COMSPEC", "cmd.exe"),
        "/d",
        "/c",
        "mklink",
        "/j",
        str(link),
        str(target),
    )
    subprocess.run(  # nosec B603 - fixed mklink command and validated paths.
        command,
        capture_output=True,
        text=True,
        check=True,
    )


def _ensure_tracked_runtime_links(*, work_root: Path, repo_root: Path) -> None:
    """Expose tracked read-only configuration to a non-repository CWD."""
    configs_link = work_root / "configs"
    expected = (repo_root / "configs").resolve()
    if _is_directory_link(configs_link):
        if configs_link.resolve() != expected:
            raise ValueError(f"unexpected configs link target: {configs_link}")
        return
    if configs_link.exists():
        raise ValueError(f"audit work root already contains configs: {configs_link}")
    try:
        configs_link.symlink_to(expected, target_is_directory=True)
    except OSError as exc:
        if sys.platform != "win32" or getattr(exc, "winerror", None) != 1314:
            raise
        _create_windows_directory_junction(link=configs_link, target=expected)


def _run_phase_command(
    *,
    name: str,
    command: tuple[str, ...],
    repo_root: Path,
    phase_root: Path,
    data_root: Path,
    timeout_seconds: int,
    expected_outcome: str = "success",
    isolated_workdir: bool = True,
) -> PhaseEvidence:
    phase_root.mkdir(parents=True, exist_ok=True)
    if isolated_workdir:
        _ensure_tracked_runtime_links(work_root=phase_root, repo_root=repo_root)
    stdout_path = phase_root / "stdout.log"
    stderr_path = phase_root / "stderr.log"
    env = _isolated_subprocess_env(
        repo_root=repo_root,
        data_root=data_root,
        log_path=phase_root / "bioetl.log",
    )
    started_at = _utc_now()
    timed_out = False
    try:
        from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

        completed = (
            subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv  # nosec B603
                ensure_safe_cli_argv([str(token) for token in command]),
                cwd=phase_root if isolated_workdir else repo_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
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
    atomic_write_text(stdout_path, str(stdout))
    atomic_write_text(stderr_path, str(stderr))
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


def _find_bronze_record(
    entity_root: Path,
    *,
    predicate: Callable[[dict[str, object]], bool],
) -> tuple[dict[str, object], Path]:
    """Return the first deterministic JSONL record satisfying ``predicate``."""
    paths = sorted(
        (*entity_root.rglob("*.jsonl"), *entity_root.rglob(f"*{JSONL_ZST_SUFFIX}")),
        key=lambda path: path.as_posix(),
    )
    for path in paths:
        try:
            if path.name.endswith(JSONL_ZST_SUFFIX):
                compressed = path.open("rb")
                reader = zstandard.ZstdDecompressor().stream_reader(compressed)
                stream_context = io.TextIOWrapper(reader, encoding="utf-8")
            else:
                stream_context = path.open(encoding="utf-8")
            with stream_context as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    payload = json.loads(line)
                    if isinstance(payload, dict) and predicate(payload):
                        return payload, path
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise ValueError(f"no compatible cached Bronze record under {entity_root}")


def _record_from_decoded_response(
    decoded: dict[str, object],
) -> dict[str, object] | None:
    """Pick first list-of-dict entity row from a decoded VCR response body."""
    if "status" in decoded:
        return None
    for value in decoded.values():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return dict(value[0])
    return None


def _record_from_vcr_interaction(
    interaction: object,
) -> dict[str, object] | None:
    if not isinstance(interaction, dict):
        return None
    response = interaction.get("response")
    body = response.get("body") if isinstance(response, dict) else None
    raw = body.get("string") if isinstance(body, dict) else None
    if not isinstance(raw, str):
        return None
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    return _record_from_decoded_response(decoded)


def _first_recorded_response(path: Path) -> dict[str, object]:
    """Return the first non-status record from one governed VCR cassette."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    interactions = payload.get("interactions") if isinstance(payload, dict) else None
    if not isinstance(interactions, list):
        raise ValueError(f"invalid recorded fixture: {path}")
    for interaction in interactions:
        record = _record_from_vcr_interaction(interaction)
        if record is not None:
            return record
    raise ValueError(f"no bounded response record found in {path}")


def _load_bronze_fixture_mapping(repo_root: Path) -> tuple[Path, dict[str, object]]:
    """Return the tracked bronze fixture mapping used for standalone staging."""
    manifest_path = repo_root / "configs" / "base" / "bronze_fixture_manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    fixtures = manifest.get("fixtures") if isinstance(manifest, dict) else None
    if not isinstance(fixtures, dict):
        raise ValueError("Bronze fixture manifest has no fixtures mapping")
    return manifest_path, fixtures


def _standalone_pipeline_source(
    *,
    repo_root: Path,
    pipeline: str,
    fixture: dict[str, object],
) -> tuple[Path, bytes, str]:
    """Resolve one pipeline's staged source bytes and provenance kind."""
    if pipeline in _RECORDED_SPECIAL_FIXTURES:
        source_path = (
            repo_root
            / "tests"
            / "fixtures"
            / "vcr"
            / "chembl"
            / f"test_pipeline_matrix__{pipeline}.yaml"
        )
        record = _first_recorded_response(source_path)
        rendered = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
        return source_path, rendered.encode(), "recorded_provider_response"
    source_path = repo_root / str(fixture.get("fixture_path") or "")
    return source_path, source_path.read_bytes(), "tracked_bronze_fixture"


def _validate_standalone_fixture_source(
    *, repo_root: Path, source_path: Path, raw: bytes
) -> None:
    """Reject staged fixture sources that escape the checkout or are empty."""
    if repo_root.resolve() not in source_path.resolve().parents:
        raise ValueError(f"fixture escapes checkout: {source_path}")
    if not raw.strip():
        raise ValueError(f"fixture is empty: {source_path}")


def _write_standalone_fixture_files(
    *,
    cache_root: Path,
    entity: str,
    raw: bytes,
    compressor: zstandard.ZstdCompressor,
) -> tuple[Path, Path]:
    """Materialize one standalone fixture and its compressed twin."""
    destination = (
        cache_root
        / "chembl"
        / entity
        / "2026-07-14"
        / f"batch_2026-07-14_bounded_{entity}.jsonl"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(destination, raw)
    compressed = destination.with_suffix(JSONL_ZST_SUFFIX)
    atomic_write_bytes(compressed, compressor.compress(raw))
    return destination, compressed


def _standalone_fixture_evidence_record(
    *,
    pipeline: str,
    source_kind: str,
    source_path: Path,
    destination: Path,
    compressed: Path,
    raw: bytes,
    fixture: dict[str, object],
) -> dict[str, object]:
    """Build one standalone fixture evidence row."""
    return {
        "pipeline": pipeline,
        "source_kind": source_kind,
        "source_path": str(source_path),
        "source_sha256": _sha256_file(source_path),
        "fixture_path": str(destination),
        "fixture_sha256": _sha256_file(destination),
        "compressed_fixture_path": str(compressed),
        "compressed_fixture_sha256": _sha256_file(compressed),
        "record_count": sum(bool(line.strip()) for line in raw.splitlines()),
        "provenance": str(fixture.get("provenance") or ""),
        "validation_status": fixture.get("validation_status"),
    }


def _stage_one_standalone_fixture(
    *,
    repo_root: Path,
    cache_root: Path,
    pipeline: str,
    fixtures: dict[str, object],
    compressor: zstandard.ZstdCompressor,
) -> dict[str, object]:
    """Stage one ChEMBL pipeline fixture into the standalone cache root."""
    entity = pipeline.removeprefix("chembl_")
    fixture = fixtures.get(f"chembl/{entity}")
    if not isinstance(fixture, dict) or fixture.get("validation_status") != "valid":
        raise ValueError(f"missing valid tracked fixture for {pipeline}")
    source_path, raw, source_kind = _standalone_pipeline_source(
        repo_root=repo_root,
        pipeline=pipeline,
        fixture=fixture,
    )
    _validate_standalone_fixture_source(
        repo_root=repo_root, source_path=source_path, raw=raw
    )
    destination, compressed = _write_standalone_fixture_files(
        cache_root=cache_root,
        entity=entity,
        raw=raw,
        compressor=compressor,
    )
    return _standalone_fixture_evidence_record(
        pipeline=pipeline,
        source_kind=source_kind,
        source_path=source_path,
        destination=destination,
        compressed=compressed,
        raw=raw,
        fixture=fixture,
    )


def _stage_standalone_fixture_cache(
    *, repo_root: Path, audit_root: Path
) -> tuple[Path, dict[str, object]]:
    """Stage source-bound compatible cached input for every ChEMBL pipeline."""
    manifest_path, fixtures = _load_bronze_fixture_mapping(repo_root)
    cache_root = audit_root / "fixtures" / "standalone-cache"
    compressor = zstandard.ZstdCompressor(level=3)
    evidence = [
        _stage_one_standalone_fixture(
            repo_root=repo_root,
            cache_root=cache_root,
            pipeline=pipeline,
            fixtures=fixtures,
            compressor=compressor,
        )
        for pipeline in CHEMBL_PIPELINES
    ]
    return cache_root, {
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256_file(manifest_path),
        "records": evidence,
    }


def _resolve_workflow_join_records(
    chembl_root: Path,
) -> tuple[
    dict[str, object],
    Path,
    dict[str, object],
    dict[str, object],
    Path,
    dict[str, object],
    Path,
    str,
    str,
    str,
]:
    """Select assay/target/publication records that can form a baseline join."""
    assay, assay_source = _find_bronze_record(
        chembl_root / "assay",
        predicate=lambda row: (
            bool(row.get("target_chembl_id")) and bool(row.get("document_chembl_id"))
        ),
    )
    source_assay = dict(assay)
    try:
        target_id = str(assay["target_chembl_id"])
        publication_id = str(assay["document_chembl_id"])
        target, target_source = _find_bronze_record(
            chembl_root / "target",
            predicate=lambda row: (
                str(row.get("target_chembl_id") or "") == target_id
                and _workflow_target_is_gold_eligible(row)
            ),
        )
        publication, publication_source = _find_bronze_record(
            chembl_root / "publication",
            predicate=lambda row: (
                str(row.get("document_chembl_id") or "") == publication_id
            ),
        )
        return (
            assay,
            assay_source,
            source_assay,
            target,
            target_source,
            publication,
            publication_source,
            target_id,
            publication_id,
            "lossless_join_compatible_source_record",
        )
    except ValueError:
        target, target_source = _find_bronze_record(
            chembl_root / "target",
            predicate=lambda row: (
                bool(row.get("target_chembl_id"))
                and _workflow_target_is_gold_eligible(row)
            ),
        )
        publication, publication_source = _find_bronze_record(
            chembl_root / "publication",
            predicate=lambda row: bool(row.get("document_chembl_id")),
        )
        target_id = str(target["target_chembl_id"])
        publication_id = str(publication["document_chembl_id"])
        projected_assay = {
            **assay,
            "target_chembl_id": target_id,
            "document_chembl_id": publication_id,
        }
        return (
            projected_assay,
            assay_source,
            source_assay,
            target,
            target_source,
            publication,
            publication_source,
            target_id,
            publication_id,
            "deterministic_workflow_join_projection",
        )


def _write_workflow_fixture_entity(
    *,
    fixture_root: Path,
    entity: str,
    record: dict[str, object],
    source: Path,
    source_record: dict[str, object],
    derivation: str,
) -> dict[str, object]:
    """Write one workflow fixture entity and return its evidence row."""
    destination = (
        fixture_root
        / "chembl"
        / entity
        / "2026-07-14"
        / f"batch_2026-07-14_bounded_{entity}.jsonl"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    atomic_write_text(destination, rendered)
    compressed_destination = destination.with_suffix(JSONL_ZST_SUFFIX)
    atomic_write_bytes(
        compressed_destination,
        zstandard.ZstdCompressor(level=3).compress(rendered.encode("utf-8")),
    )
    return {
        "entity": entity,
        "source_path": str(source),
        "source_sha256": _sha256_file(source),
        "source_record_sha256": hashlib.sha256(
            (
                json.dumps(
                    source_record,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode()
        ).hexdigest(),
        "derivation": derivation,
        "record_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
        "fixture_path": str(destination),
        "fixture_sha256": _sha256_file(destination),
        "compressed_fixture_path": str(compressed_destination),
        "compressed_fixture_sha256": _sha256_file(compressed_destination),
    }


def _stage_workflow_fixture(
    *, canonical_bronze_root: Path, audit_root: Path
) -> tuple[Path, dict[str, object]]:
    """Stage a traceable three-record fixture for ``chembl_baseline`` joins."""
    (
        assay,
        assay_source,
        source_assay,
        target,
        target_source,
        publication,
        publication_source,
        target_id,
        publication_id,
        assay_derivation,
    ) = _resolve_workflow_join_records(canonical_bronze_root / "chembl")
    fixture_root = audit_root / "fixtures" / "chembl-baseline"
    entity_specs = (
        ("assay", assay, assay_source, source_assay, assay_derivation),
        ("target", target, target_source, target, "lossless_source_record"),
        (
            "publication",
            publication,
            publication_source,
            publication,
            "lossless_source_record",
        ),
    )
    evidence_records = [
        _write_workflow_fixture_entity(
            fixture_root=fixture_root,
            entity=entity,
            record=record,
            source=source,
            source_record=source_record,
            derivation=derivation,
        )
        for entity, record, source, source_record, derivation in entity_specs
    ]
    return fixture_root, {
        "target_id": target_id,
        "publication_id": publication_id,
        "records": evidence_records,
    }


def _workflow_target_is_gold_eligible(row: dict[str, object]) -> bool:
    """Match the target fields needed by the governed Gold join surface."""
    components = row.get("target_components")
    if not isinstance(components, list) or len(components) != 1:
        return False
    component = components[0]
    if not isinstance(component, dict):
        return False
    if component.get("component_type") != "PROTEIN":
        return False
    if not component.get("accession") or not component.get("component_id"):
        return False
    organism_raw = row.get("organism")
    tax_id_raw = row.get("tax_id")
    organism = organism_raw if isinstance(organism_raw, str) else None
    tax_id = tax_id_raw if isinstance(tax_id_raw, (int, str)) else None
    classification = classify_organism(organism, tax_id)
    return (
        row.get("target_type") == "SINGLE PROTEIN"
        and bool(row.get("pref_name"))
        and bool(row.get("organism"))
        and classification.organism_class == CellularityType.MULTICELLULAR
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
        "--noconftest",
        "-o",
        "addopts=",
        "-o",
        "timeout=0",
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
        "--no-ensure-observability-backend",
        "--tracing" if tracing else "--no-tracing",
    ]
    if cached_bronze_root is None:
        command.extend(
            (
                "--no-cached-bronze",
                "--required-persistence-profile",
                "degraded_observable",
            )
        )
    else:
        command.extend(
            ("--use-cached-bronze", "--cached-bronze-path", str(cached_bronze_root))
        )
    return tuple(command)


def _execute_attempt_subprocess(
    *,
    command: tuple[str, ...],
    attempt_root: Path,
    env: dict[str, str],
    timeout_seconds: int,
) -> tuple[int, bool, str, str]:
    """Run one attempt subprocess and normalize timeout/OSError outcomes."""
    try:
        from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

        completed = (
            subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv  # nosec B603
                ensure_safe_cli_argv([str(token) for token in command]),
                cwd=attempt_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        )
        return completed.returncode, False, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        return 124, True, _timeout_output(exc.stdout), _timeout_output(exc.stderr)
    except OSError as exc:
        return 126, False, "", f"{type(exc).__name__}: {exc}"


def _attempt_output_partitions(
    *,
    data_root: Path,
    before_files: dict[Path, str],
) -> tuple[tuple[Path, ...], tuple[Path, ...]]:
    """Partition changed files into checkpoint and semantic output paths."""
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
    return checkpoint_paths, output_paths


def _attempt_result_signature(
    *,
    terminal_events: tuple[str, ...],
    metrics: dict[str, int],
    semantic_output: object,
    terminal_rows: Sequence[dict[str, object]],
    semantic_output_records: int,
) -> str:
    """Hash the deterministic success signature when one terminal row exists."""
    if len(terminal_rows) != 1 or semantic_output_records <= 0:
        return ""
    return hashlib.sha256(
        json.dumps(
            {
                "terminal_events": terminal_events,
                "metrics_snapshot": metrics,
                "semantic_output": semantic_output,
            },
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class _AttemptEvidenceInputs:
    """Packed inputs for attempt evidence assembly (python:S107)."""

    repo_root: Path
    pipeline: str
    tracing: bool
    limit: int
    run_mode: str
    command: tuple[str, ...]
    data_root: Path
    stdout_path: Path
    stderr_path: Path
    started_at: str
    finished_at: str
    exit_code: int
    timed_out: bool
    before_manifests: set[Path]
    before_files: dict[Path, str]


def _collect_attempt_evidence(inputs: _AttemptEvidenceInputs) -> AttemptEvidence:
    """Assemble durable attempt evidence from isolated run artifacts."""
    new_manifests = _manifest_snapshot(inputs.data_root) - inputs.before_manifests
    manifest_ids, run_ids, manifest_paths = _read_new_manifest_identity(
        new_manifests,
        expected_pipeline=inputs.pipeline,
    )
    ledger_rows = _read_ledger_rows(inputs.data_root)
    terminal_events = _terminal_events_for_runs(ledger_rows, run_ids)
    terminal_rows = _terminal_rows_for_runs(ledger_rows, run_ids)
    metrics, details, _terminal_signature = _terminal_payload(terminal_rows)
    ledger_paths = tuple(
        inputs.data_root / "output" / "control" / "run_ledger" / f"{manifest_id}.jsonl"
        for manifest_id in manifest_ids
    )
    checkpoint_paths, output_paths = _attempt_output_partitions(
        data_root=inputs.data_root,
        before_files=inputs.before_files,
    )
    output_artifacts = _file_artifacts(output_paths, root=inputs.data_root)
    semantic_output, semantic_output_records = _semantic_output_payload(output_paths)
    checkpoint_disposition, checkpoint_interval = _checkpoint_policy(
        inputs.repo_root, inputs.pipeline, inputs.limit
    )
    if checkpoint_paths:
        checkpoint_disposition = "retained"
    result_signature = _attempt_result_signature(
        terminal_events=terminal_events,
        metrics=metrics,
        semantic_output=semantic_output,
        terminal_rows=terminal_rows,
        semantic_output_records=semantic_output_records,
    )
    return AttemptEvidence(
        pipeline=inputs.pipeline,
        tracing=inputs.tracing,
        started_at=inputs.started_at,
        finished_at=inputs.finished_at,
        exit_code=inputs.exit_code,
        timed_out=inputs.timed_out,
        command=inputs.command,
        stdout_path=str(inputs.stdout_path),
        stderr_path=str(inputs.stderr_path),
        manifest_ids=manifest_ids,
        run_ids=run_ids,
        terminal_ledger_events=terminal_events,
        manifest_artifacts=_file_artifacts(manifest_paths, root=inputs.data_root),
        ledger_artifacts=_file_artifacts(ledger_paths, root=inputs.data_root),
        checkpoint_artifacts=_file_artifacts(checkpoint_paths, root=inputs.data_root),
        checkpoint_disposition=checkpoint_disposition,
        checkpoint_interval=checkpoint_interval,
        output_artifacts=output_artifacts,
        semantic_output_records=semantic_output_records,
        terminal_metrics_snapshot=metrics,
        terminal_details=details,
        result_signature=result_signature,
        run_mode=inputs.run_mode,
    )


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
    _ensure_tracked_runtime_links(work_root=attempt_root, repo_root=repo_root)
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
    env = _isolated_subprocess_env(
        repo_root=repo_root,
        data_root=data_root,
        log_path=log_root / "bioetl-audit.log",
    )
    started_at = _utc_now()
    exit_code, timed_out, stdout, stderr = _execute_attempt_subprocess(
        command=command,
        attempt_root=attempt_root,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    finished_at = _utc_now()
    atomic_write_text(stdout_path, str(stdout))
    atomic_write_text(stderr_path, str(stderr))
    return _collect_attempt_evidence(
        _AttemptEvidenceInputs(
            repo_root=repo_root,
            pipeline=pipeline,
            tracing=tracing,
            limit=limit,
            run_mode=run_mode,
            command=command,
            data_root=data_root,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            started_at=started_at,
            finished_at=finished_at,
            exit_code=exit_code,
            timed_out=timed_out,
            before_manifests=before_manifests,
            before_files=before_files,
        )
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


def _run_git(
    args: list[str],
    *,
    repo_root: Path,
    timeout_seconds: float,
) -> subprocess.CompletedProcess[str]:
    """Run a bounded git command; re-raise timeouts as SubprocessError."""
    try:
        return subprocess.run(  # nosec B603
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise subprocess.SubprocessError(
            f"git {' '.join(args)} timed out after {timeout_seconds:.0f}s "
            f"(repo={repo_root})"
        ) from exc


def _source_provenance(repo_root: Path) -> dict[str, object]:
    """Return revision/tree/cleanliness for campaign gates.

    Cleanliness uses ``git status --porcelain --untracked-files=normal`` so
    untracked *paths* still fail the gate without expanding every file inside
    untracked directories. ``--untracked-files=all`` is pathologically slow on
    large/cloud-synced worktrees and has hung unit/plan mode on Windows GDrive.
    """
    revision = _run_git(
        ["rev-parse", "HEAD"],
        repo_root=repo_root,
        timeout_seconds=15,
    )
    tree = _run_git(
        ["rev-parse", "HEAD^{tree}"],
        repo_root=repo_root,
        timeout_seconds=15,
    )
    # ``-uno`` would ignore untracked entirely and weaken the execute gate.
    # ``normal`` lists untracked files and directories without deep expansion.
    status = _run_git(
        ["status", "--porcelain", "--untracked-files=normal"],
        repo_root=repo_root,
        timeout_seconds=20,
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



# Evidence validation is isolated from runtime execution and orchestration.
from scripts.engineering.qa.observability_closure_campaign_validation import (
    _parse_generated_at,
    _validate_summary,
    _validate_evidence_producer,
    _validate_evidence_assertions,
    _validate_one_raw_artifact,
    _validate_prometheus_reconciliation_rows,
    _validate_ledger_reconciliation_rows,
    _validate_dq_reconciliation_row,
    _require_nonempty_fields,
    _validate_one_workflow_child,
    _validate_workflow_child_rows,
    _parent_child_field_mismatches,
    _validate_one_workflow_parent,
    _validate_workflow_parent_rows,
    _has_repeated_success_and_failure,
    _validate_evidence_object_fields,
    _validate_sha256_artifact,
    _validate_attempt_artifact_field,
    _validate_attempt_artifacts,
    _validate_workflow_phase_stream_artifacts,
    _validate_raw_artifacts,
    _json_payloads_by_kind,
    _tracing_pair_errors,
    _expected_tracing_occurrences,
    _actual_tracing_occurrences,
    _tracing_coverage_errors,
    _validate_tracing_raw,
    _validate_metric_reconciliation_raw,
    _validate_workflow_raw,
    _inventory_report_errors,
    _validate_inventory_raw,
    _dashboard_variable_payload_errors,
    _validate_dashboard_raw,
    _validate_zero_raw,
    _validate_scrape_raw,
    _collect_screenshot_hashes,
    _validate_one_render_manifest,
    _validate_render_raw,
    _validate_promtool_raw,
    _validate_online_run_payload,
    _collect_online_metric_rows,
    _validate_online_metric_deltas,
    _validate_online_raw,
    _backend_http_profile_errors,
    _backend_loki_profile_errors,
    _backend_signature_errors,
    _validate_backend_profile_raw,
    _validate_raw_content,
    _evidence_path_uniqueness_errors,
    _gate_one_evidence_key,
    _evidence_gate,
    _scorecard,
    _residual_findings_gate,
    _stable_sha256,
    _campaign_binding,
    _retained_artifacts_valid,
    _load_finalize_report,
    _core_campaign_gates_satisfied,
)

def _finalize_campaign(
    *,
    args: argparse.Namespace,
    audit_root: Path,
    source_provenance: dict[str, object],
    evidence: dict[str, str],
) -> int:
    report_path = args.finalize_report.expanduser().resolve()
    payload = _load_finalize_report(
        report_path=report_path,
        audit_root=audit_root,
        source_provenance=source_provenance,
    )
    retained_ok, retained_errors = _retained_artifacts_valid(payload)
    binding = payload["campaign_binding"]
    assert isinstance(binding, dict)
    external_gate = _evidence_gate(
        evidence,
        audit_root=audit_root,
        source_revision=str(source_provenance["revision"]),
        expected_binding=binding,
    )
    residual_gate = _residual_findings_gate(args.residual_limitation, args.finding_id)
    complete = bool(
        source_provenance["clean"]
        and retained_ok
        and _core_campaign_gates_satisfied(payload)
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
    atomic_write_text(
        report_path,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )
    print(json.dumps({"status": payload["status"], "report": str(report_path)}))
    return 0 if complete else 1


def _bootstrap_campaign_context(
    args: argparse.Namespace,
    *,
    repo_root: Path,
    audit_root: Path,
    canonical_roots: tuple[Path, ...],
) -> tuple[
    dict[str, str],
    dict[str, object],
    tuple[str, ...],
    subprocess.CompletedProcess[str],
]:
    """Validate CLI setup and collect provenance + registry pipeline inventory."""
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
    return evidence, source_provenance, registered_pipelines, registry_completed



from scripts.engineering.qa import observability_closure_campaign_cli as _campaign_cli
from scripts.engineering.qa.observability_closure_campaign_cli import (
    _planned_payload,
    _run_standalone_attempts,
    _run_campaign_phases,
    _tracing_result_parity,
    _attempt_gate_satisfied,
    _ExecuteReportInputs,
    _build_execute_report,
)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI while preserving the historical module patch surface."""
    for name in ["_run_attempt","_run_phase_command","_stage_standalone_fixture_cache","_stage_workflow_fixture","_workflow_baseline_command","_workflow_failure_command","_dq_hard_failure_test_command","_source_revision","_registry_pipeline_command","_discover_chembl_pipelines"]:
        setattr(_campaign_cli, name, globals()[name])
    return _campaign_cli.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
