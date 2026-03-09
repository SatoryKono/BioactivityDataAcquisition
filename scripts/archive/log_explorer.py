"""BioETL Log Explorer.

High-performance log analysis tool using Polars to query JSONL logs.
Supports filtering by level, pipeline, run_id, and error analysis.
"""

import json
from pathlib import Path
from typing import Optional

import click
import polars as pl


class LogExplorer:
    def __init__(self, log_path: str = "logs/bioetl.log"):
        self.log_path = Path(log_path)
        if not self.log_path.exists():
            raise FileNotFoundError(f"Log file not found at {log_path}")

    def _load_logs(self) -> pl.LazyFrame:
        """Load JSONL logs into a Polars LazyFrame."""
        # We use scan_ndjson for high performance on large files
        return pl.scan_ndjson(self.log_path)

    def get_summary(self, last_n: int = 1000):
        """Get a summary of logs (counts by level and pipeline)."""
        lf = self._load_logs().tail(last_n)

        summary = (
            lf.group_by(["level", "event"]).agg(pl.count().alias("count")).collect()
        )
        return summary

    def find_errors(self, pipeline: str | None = None, limit: int = 10):
        """Find recent errors, optionally filtered by pipeline."""
        lf = self._load_logs().filter(pl.col("level") == "error")

        if pipeline:
            lf = lf.filter(pl.col("pipeline") == pipeline)

        errors = lf.sort("timestamp", descending=True).limit(limit).collect()
        return errors

    def analyze_performance(self, pipeline: str):
        """Analyze pipeline stage durations if logged."""
        # Assuming we log events like 'stage_completed' with 'duration' field
        lf = self._load_logs().filter(
            (pl.col("pipeline") == pipeline) & (pl.col("event") == "stage_completed")
        )

        perf = (
            lf.group_by("stage")
            .agg(
                [
                    pl.col("duration").mean().alias("avg_duration"),
                    pl.col("duration").max().alias("max_duration"),
                    pl.count().alias("call_count"),
                ]
            )
            .collect()
        )
        return perf


@click.group()
def cli():
    """BioETL Log Explorer CLI."""
    pass


@cli.command()
@click.option("--path", default="logs/bioetl.log", help="Path to log file")
@click.option("--limit", default=1000, help="Analyze last N lines")
def summary(path, limit):
    """Show log summary."""
    explorer = LogExplorer(path)
    print(explorer.get_summary(limit))


@cli.command()
@click.option("--path", default="logs/bioetl.log", help="Path to log file")
@click.option("--pipeline", default=None, help="Filter by pipeline")
@click.option("--limit", default=5, help="Number of errors to show")
def errors(path, pipeline, limit):
    """Show recent errors."""
    explorer = LogExplorer(path)
    errs = explorer.find_errors(pipeline, limit)
    if errs.is_empty():
        print("No errors found.")
    else:
        print(errs)


if __name__ == "__main__":
    cli()
