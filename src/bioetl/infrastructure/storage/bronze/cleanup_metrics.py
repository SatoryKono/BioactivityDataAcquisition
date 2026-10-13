"""Bounded Prometheus outcome emission for Bronze cleanup results."""

from __future__ import annotations

from bioetl.domain.ports import MetricsPort


def emit_cleanup_outcome_metrics(metrics: MetricsPort, result: dict[str, int]) -> None:
    """Emit retained artifact counts via registered metric families."""
    labels = {"operation": "cleanup"}
    if result["files_skipped"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_files_skipped_total",
            result["files_skipped"],
            labels,
        )
    if result["bytes_skipped"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_bytes_skipped_total",
            result["bytes_skipped"],
            labels,
        )
    if result["files_conflicted"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_files_conflicted_total",
            result["files_conflicted"],
            labels,
        )
    if result["bytes_conflicted"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_bytes_conflicted_total",
            result["bytes_conflicted"],
            labels,
        )
    if result["files_failed"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_files_failed_total",
            result["files_failed"],
            labels,
        )
    if result["bytes_failed"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_bytes_failed_total",
            result["bytes_failed"],
            labels,
        )
    if result["directories_skipped"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_directories_skipped_total",
            result["directories_skipped"],
            labels,
        )
    if result["directories_conflicted"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_directories_conflicted_total",
            result["directories_conflicted"],
            labels,
        )
    if result["directories_failed"]:
        metrics.increment_counter(
            "bioetl_bronze_cleanup_directories_failed_total",
            result["directories_failed"],
            labels,
        )
