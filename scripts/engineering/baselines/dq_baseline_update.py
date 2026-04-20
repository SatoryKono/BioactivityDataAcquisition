#!/usr/bin/env python3
"""
dq_baseline_update.py - Update Data Quality baseline metrics.

Recalculates baseline metrics for Data Quality validation by analyzing
historical pipeline run data. The baseline is used for anomaly detection
and threshold comparison.

Baseline metrics include:
- Average error rate
- Standard deviation
- Record count statistics
- Processing time benchmarks

Usage:
    # Update baseline for all pipelines
    python src/tools/dq_baseline_update.py

    # Update baseline for specific pipeline
    python src/tools/dq_baseline_update.py --pipeline chembl_activity

    # Custom analysis window
    python src/tools/dq_baseline_update.py --window-days 60

    # Dry-run to preview changes
    python src/tools/dq_baseline_update.py --dry-run

References:
    - RULES.md §3.4.1: Data Quality baseline
    - DQConfig in src/bioetl/domain/config.py
    - Anomaly detection in src/bioetl/infrastructure/observability/anomaly/

Aligned with RULES.md v5.24 (2026-01-06)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, stdev

# Configure logging for CLI output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Default data and reports directories
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"

# Default baseline output location
DEFAULT_BASELINE_FILE = DEFAULT_REPORTS_DIR / "dq_baselines.json"

# Default analysis window
DEFAULT_WINDOW_DAYS = 30


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class RunMetrics:
    """Metrics from a single pipeline run."""

    run_id: str
    pipeline: str
    timestamp: datetime
    records_processed: int
    records_failed: int
    error_rate: float
    duration_ms: int


@dataclass
class BaselineMetrics:
    """Computed baseline metrics for a pipeline."""

    pipeline: str
    updated_at: datetime
    window_days: int
    runs_analyzed: int
    avg_error_rate: float
    stdev_error_rate: float
    avg_records: float
    avg_duration_ms: float
    min_error_rate: float
    max_error_rate: float


@dataclass
class BaselineUpdateResult:
    """Result of baseline update operation."""

    pipeline: str
    success: bool
    baseline: BaselineMetrics | None = None
    error: str | None = None


@dataclass
class UpdateReport:
    """Report of all baseline updates."""

    results: list[BaselineUpdateResult] = field(default_factory=list)
    dry_run: bool = False

    @property
    def successful(self) -> int:
        """Number of successful updates."""
        return sum(1 for r in self.results if r.success)

    @property
    def failed(self) -> int:
        """Number of failed updates."""
        return sum(1 for r in self.results if not r.success)


# =============================================================================
# Metrics Collection Functions
# =============================================================================


def _load_run_metrics(
    data_dir: Path, pipeline: str | None, window: timedelta
) -> list[RunMetrics]:
    """Load run metrics from completed pipeline runs.

    This looks for metrics in the standard BioETL locations:
    - data/metrics/{pipeline}/runs/*.json
    - data/audit/{pipeline}/*.json

    Args:
        data_dir: Base data directory.
        pipeline: Specific pipeline or None for all.
        window: Time window for analysis.

    Returns:
        List of RunMetrics from historical runs.
    """
    metrics = []
    cutoff = datetime.now() - window

    metrics.extend(
        _load_metrics_from_glob(
            base_dir=data_dir / "audit",
            pattern=f"{pipeline}/*.json" if pipeline else "*/*.json",
            cutoff=cutoff,
            parser=_parse_audit_file,
        )
    )
    metrics.extend(
        _load_metrics_from_glob(
            base_dir=data_dir / "metrics",
            pattern=f"{pipeline}/runs/*.json" if pipeline else "*/runs/*.json",
            cutoff=cutoff,
            parser=_parse_metrics_file,
        )
    )

    return metrics


def _load_metrics_from_glob(
    *,
    base_dir: Path,
    pattern: str,
    cutoff: datetime,
    parser: callable,
) -> list[RunMetrics]:
    metrics: list[RunMetrics] = []
    if not base_dir.exists():
        return metrics

    for metrics_file in base_dir.glob(pattern):
        try:
            run_metric = parser(metrics_file, cutoff)
            if run_metric:
                metrics.append(run_metric)
        except Exception as e:
            logger.debug("Failed to parse %s: %s", metrics_file, e)
    return metrics


def _parse_audit_file(file_path: Path, cutoff: datetime) -> RunMetrics | None:
    """Parse a single audit file for run metrics.

    Args:
        file_path: Path to the audit JSON file.
        cutoff: Minimum timestamp for inclusion.

    Returns:
        RunMetrics if valid and within window, None otherwise.
    """
    with open(file_path) as f:
        data = json.load(f)

    # Parse timestamp
    ts_str = data.get("completed_at") or data.get("timestamp")
    if not ts_str:
        return None

    try:
        timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except ValueError:
        return None

    if timestamp.replace(tzinfo=None) < cutoff:
        return None

    # Extract metrics
    records_processed = data.get("records_processed", 0)
    records_failed = data.get("records_failed", 0)
    duration_ms = data.get("duration_ms", 0)

    if records_processed == 0:
        return None

    error_rate = records_failed / records_processed

    pipeline = data.get("pipeline") or file_path.parent.name

    return RunMetrics(
        run_id=data.get("run_id", file_path.stem),
        pipeline=pipeline,
        timestamp=timestamp.replace(tzinfo=None),
        records_processed=records_processed,
        records_failed=records_failed,
        error_rate=error_rate,
        duration_ms=duration_ms,
    )


def _parse_metrics_file(file_path: Path, cutoff: datetime) -> RunMetrics | None:
    """Parse a single metrics file for run data.

    Args:
        file_path: Path to the metrics JSON file.
        cutoff: Minimum timestamp for inclusion.

    Returns:
        RunMetrics if valid and within window, None otherwise.
    """
    with open(file_path) as f:
        data = json.load(f)

    # Parse timestamp
    ts_str = data.get("timestamp") or data.get("completed_at")
    if not ts_str:
        return None

    try:
        timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except ValueError:
        return None

    if timestamp.replace(tzinfo=None) < cutoff:
        return None

    # Extract metrics
    records_processed = data.get("total_records", 0) or data.get("records_processed", 0)
    records_failed = data.get("failed_records", 0) or data.get("records_failed", 0)
    duration_ms = data.get("duration_ms", 0)

    if records_processed == 0:
        return None

    error_rate = records_failed / records_processed

    # Get pipeline name from directory structure
    pipeline = file_path.parent.parent.name

    return RunMetrics(
        run_id=data.get("run_id", file_path.stem),
        pipeline=pipeline,
        timestamp=timestamp.replace(tzinfo=None),
        records_processed=records_processed,
        records_failed=records_failed,
        error_rate=error_rate,
        duration_ms=duration_ms,
    )


# =============================================================================
# Baseline Calculation Functions
# =============================================================================


def compute_baseline(
    pipeline: str,
    metrics: list[RunMetrics],
    window_days: int,
) -> BaselineMetrics:
    """Compute baseline metrics from historical runs.

    Args:
        pipeline: Pipeline name.
        metrics: List of historical run metrics.
        window_days: Analysis window in days.

    Returns:
        BaselineMetrics with computed statistics.

    Raises:
        ValueError: If insufficient data for computation.
    """
    if not metrics:
        raise ValueError(f"No metrics available for pipeline '{pipeline}'")

    if len(metrics) < 2:
        raise ValueError(
            f"Insufficient runs for pipeline '{pipeline}' (need at least 2, got {len(metrics)})"
        )

    error_rates = [m.error_rate for m in metrics]
    records = [m.records_processed for m in metrics]
    durations = [m.duration_ms for m in metrics if m.duration_ms > 0]

    return BaselineMetrics(
        pipeline=pipeline,
        updated_at=datetime.now(),
        window_days=window_days,
        runs_analyzed=len(metrics),
        avg_error_rate=mean(error_rates),
        stdev_error_rate=stdev(error_rates) if len(error_rates) > 1 else 0.0,
        avg_records=mean(records),
        avg_duration_ms=mean(durations) if durations else 0.0,
        min_error_rate=min(error_rates),
        max_error_rate=max(error_rates),
    )


def update_baseline(
    pipeline: str,
    data_dir: Path,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> BaselineUpdateResult:
    """Update baseline for a single pipeline.

    Args:
        pipeline: Pipeline name.
        data_dir: Base data directory.
        window_days: Analysis window in days.

    Returns:
        BaselineUpdateResult with computed baseline or error.
    """
    try:
        window = timedelta(days=window_days)
        metrics = _load_run_metrics(data_dir, pipeline, window)

        # Filter to this pipeline
        pipeline_metrics = [m for m in metrics if m.pipeline == pipeline]

        baseline = compute_baseline(pipeline, pipeline_metrics, window_days)

        return BaselineUpdateResult(
            pipeline=pipeline,
            success=True,
            baseline=baseline,
        )

    except Exception as e:
        return BaselineUpdateResult(
            pipeline=pipeline,
            success=False,
            error=str(e),
        )


def get_known_pipelines(data_dir: Path) -> list[str]:
    """Get list of known pipelines from data directories.

    Args:
        data_dir: Base data directory.

    Returns:
        List of pipeline names found in data.
    """
    pipelines = set()

    # Collect pipelines from different sources
    _add_pipelines_from_directory(pipelines, data_dir / "audit")
    _add_pipelines_from_directory(pipelines, data_dir / "metrics")
    _add_pipelines_from_silver_tables(pipelines, data_dir / "silver")

    return sorted(pipelines)


def _add_pipelines_from_directory(pipelines: set[str], directory: Path) -> None:
    """Add pipeline names from directory structure.

    Args:
        pipelines: Set to add pipeline names to
        directory: Directory to scan for pipelines
    """
    if directory.exists():
        for item in directory.iterdir():
            if item.is_dir():
                pipelines.add(item.name)


def _add_pipelines_from_silver_tables(pipelines: set[str], silver_dir: Path) -> None:
    """Add pipeline names from silver table structure.

    Args:
        pipelines: Set to add pipeline names to
        silver_dir: Silver data directory to scan
    """
    if not silver_dir.exists():
        return
    for provider_dir in _provider_directories(silver_dir):
        for entity_dir in _silver_entity_directories(provider_dir):
            pipelines.add(f"{provider_dir.name}_{entity_dir.name}")


def _provider_directories(silver_dir: Path) -> list[Path]:
    return [provider_dir for provider_dir in silver_dir.iterdir() if provider_dir.is_dir()]


def _silver_entity_directories(provider_dir: Path) -> list[Path]:
    return [
        entity_dir
        for entity_dir in provider_dir.iterdir()
        if entity_dir.is_dir() and (entity_dir / "_delta_log").exists()
    ]


# =============================================================================
# Persistence Functions
# =============================================================================


def save_baselines(
    results: list[BaselineUpdateResult],
    output_file: Path,
) -> None:
    """Save computed baselines to JSON file.

    Args:
        results: List of successful baseline results.
        output_file: Path to output JSON file.
    """
    baselines = {}

    for result in results:
        if result.success and result.baseline:
            b = result.baseline
            baselines[result.pipeline] = {
                "updated_at": b.updated_at.isoformat(),
                "window_days": b.window_days,
                "runs_analyzed": b.runs_analyzed,
                "avg_error_rate": round(b.avg_error_rate, 6),
                "stdev_error_rate": round(b.stdev_error_rate, 6),
                "avg_records": round(b.avg_records, 2),
                "avg_duration_ms": round(b.avg_duration_ms, 2),
                "min_error_rate": round(b.min_error_rate, 6),
                "max_error_rate": round(b.max_error_rate, 6),
            }

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(baselines, f, indent=2)


# =============================================================================
# CLI Interface
# =============================================================================


def log_report(report: UpdateReport, output_file: Path | None) -> None:
    """Log baseline update report."""
    _log_report_header()
    _log_report_mode(report.dry_run)

    # Successful updates
    successful = [r for r in report.results if r.success]
    if successful:
        _log_successful_updates(successful)

    # Failed updates
    failed = [r for r in report.results if not r.success]
    if failed:
        _log_failed_updates(failed)

    _log_report_footer(report, output_file)


def _log_report_header() -> None:
    """Log report header."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("DQ Baseline Update Report")
    logger.info("=" * 70)
    logger.info("")


def _log_report_mode(dry_run: bool) -> None:
    """Log report mode."""
    if dry_run:
        logger.info("MODE: Dry-run (no changes saved)")
    else:
        logger.info("MODE: Apply")
    logger.info("")


def _log_successful_updates(successful: list[UpdateResult]) -> None:
    """Log successful updates."""
    logger.info("## SUCCESSFUL (%d pipelines)", len(successful))
    logger.info("")
    for result in successful:
        b = result.baseline
        if b:
            logger.info("  Pipeline: %s", b.pipeline)
            logger.info("    Runs analyzed:    %d", b.runs_analyzed)
            logger.info(
                "    Avg error rate:   %.4f (%.2f%%)",
                b.avg_error_rate,
                b.avg_error_rate * 100,
            )
            logger.info("    Stdev error rate: %.4f", b.stdev_error_rate)
            logger.info(
                "    Error range:      %.4f - %.4f",
                b.min_error_rate,
                b.max_error_rate,
            )
            logger.info("    Avg records:      %.0f", b.avg_records)
            logger.info("    Avg duration:     %.0f ms", b.avg_duration_ms)
            logger.info("")


def _log_failed_updates(failed: list[UpdateResult]) -> None:
    """Log failed updates."""
    logger.info("## FAILED (%d pipelines)", len(failed))
    for result in failed:
        logger.info("  %s: %s", result.pipeline, result.error)
    logger.info("")


def _log_report_footer(report: UpdateReport, output_file: Path | None) -> None:
    """Log report footer."""
    logger.info("=" * 70)
    logger.info("Summary: %d successful, %d failed", report.successful, report.failed)
    if output_file and not report.dry_run:
        logger.info("Baselines saved to: %s", output_file)
    logger.info("=" * 70)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="BioETL DQ Baseline Update Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--pipeline",
        type=str,
        help="Specific pipeline name (default: all pipelines)",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=DEFAULT_WINDOW_DAYS,
        help=f"Analysis window in days (default: {DEFAULT_WINDOW_DAYS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without saving",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Data directory (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_BASELINE_FILE,
        help=f"Output file for baselines (default: {DEFAULT_BASELINE_FILE})",
    )
    return parser.parse_args()


def main() -> int:
    """Entry point."""
    args = parse_args()

    logger.info("DQ Baseline Update Tool")
    logger.info("")
    logger.info("Analysis window: %d days", args.window_days)
    logger.info("Data directory:  %s", args.data_dir)
    logger.info("")

    report = UpdateReport(dry_run=args.dry_run)

    if args.pipeline:
        # Update single pipeline
        pipelines = [args.pipeline]
    else:
        # Discover pipelines
        pipelines = get_known_pipelines(args.data_dir)
        if not pipelines:
            logger.warning("No pipelines found in data directory.")
            logger.info("Try running some pipelines first, or check --data-dir path.")
            return 0

    logger.info("Pipelines to update: %s", ", ".join(pipelines))
    logger.info("")

    for pipeline in pipelines:
        result = update_baseline(
            pipeline=pipeline,
            data_dir=args.data_dir,
            window_days=args.window_days,
        )
        report.results.append(result)

    # Save baselines if not dry-run
    if not args.dry_run and report.successful > 0:
        successful_results = [r for r in report.results if r.success]
        save_baselines(successful_results, args.output)

    log_report(report, args.output if not args.dry_run else None)

    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
