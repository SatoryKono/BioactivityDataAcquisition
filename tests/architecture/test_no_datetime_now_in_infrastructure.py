"""Architecture test: datetime.now()/utcnow() only in application/composition layers.

REQ-ARCH-031: Single source of truth for timestamps.
Timestamps should be created in application layer and passed down.
See docs/02-architecture/decisions/ADR-014-deterministic-writes.md

Note: datetime.utcnow() is deprecated in Python 3.12+ (PEP 692).
Use datetime.now(UTC) instead for timezone-aware UTC timestamps.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Path relative to project root
INFRASTRUCTURE_DIR = Path("src/bioetl/infrastructure")

# Files allowed to use datetime.now() - with justification.
# Full documentation in ADR-014: docs/02-architecture/decisions/ADR-014-deterministic-writes.md
#
# Criteria for exceptions:
# 1. Timestamp does not affect determinism of batch operations
# 2. Timestamp is required for real-time monitoring/operations
# 3. Timestamp is not used in Bronze/Silver/Gold data
#
# REFACTORED (no longer need datetime.now()):
# - operations.py: Now accepts `now: datetime` parameter from caller
# - gold_writer.py: Now accepts `ingestion_ts: datetime` parameter for SCD2
ALLOWED_FILES: set[str] = {
    # infrastructure/observability/lineage.py
    # Uses datetime.now(UTC) for provenance tracking in record_run_start(),
    # record_run_end(), and for filtering lineage records by date range.
    "lineage.py",
    # infrastructure/observability/anomaly/detector.py
    # Uses datetime.now(UTC) for timestamp in AnomalyResult when critical anomalies detected.
    "detector.py",
    # infrastructure/observability/anomaly/detectors/iqr.py
    # IQR-based anomaly detector: timestamp in detection result for monitoring.
    "iqr.py",
    # infrastructure/observability/anomaly/detectors/mad.py
    # MAD-based anomaly detector: timestamp in detection result for monitoring.
    "mad.py",
    # infrastructure/observability/anomaly/detectors/zscore.py
    # Z-score anomaly detector: timestamp in detection result for monitoring.
    "zscore.py",
    # infrastructure/adapters/**/client.py
    # Reserved for TTL-based HTTP response caching logic.
    "client.py",
    # infrastructure/storage/delta_writer.py
    # Uses datetime.now(UTC) for audit logging timestamps.
    "delta_writer.py",
    # infrastructure/storage/gold_writer.py
    # Uses datetime.now(UTC) for audit logging timestamps.
    "gold_writer.py",
    # infrastructure/storage/silver_writer.py
    # Uses datetime.now(UTC) for audit logging timestamps.
    "silver_writer.py",
}


class TestNoDatetimeNowInInfrastructure:
    """Tests ensuring infrastructure layer doesn't create timestamps."""

    @pytest.fixture
    def infrastructure_python_files(self) -> list[Path]:
        """Get all Python files in infrastructure directory."""
        # Handle both running from project root and tests directory
        if INFRASTRUCTURE_DIR.exists():
            base = INFRASTRUCTURE_DIR
        else:
            base = Path(__file__).parent.parent.parent / INFRASTRUCTURE_DIR
        return list(base.rglob("*.py"))

    def test_no_datetime_now_in_infrastructure(
        self, infrastructure_python_files: list[Path]
    ) -> None:
        """Infrastructure MUST NOT call datetime.now() or datetime.utcnow() directly.

        Timestamps should be created in application layer (e.g., PipelineContext)
        and passed as parameters to infrastructure components.

        Note: datetime.utcnow() is deprecated in Python 3.12+ (PEP 692).
        """
        violations = []

        for py_file in infrastructure_python_files:
            if py_file.name in ALLOWED_FILES:
                continue

            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check for datetime.now() and datetime.utcnow() patterns
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in ("now", "utcnow"):
                            # datetime.now()/utcnow() after "from datetime import datetime"
                            if isinstance(node.func.value, ast.Name):
                                if node.func.value.id == "datetime":
                                    relative_path = py_file.relative_to(
                                        INFRASTRUCTURE_DIR
                                        if INFRASTRUCTURE_DIR.exists()
                                        else Path(__file__).parent.parent.parent
                                        / INFRASTRUCTURE_DIR
                                    )
                                    violations.append(
                                        f"{relative_path}:{node.lineno}: datetime.{node.func.attr}()"
                                    )
                            # datetime.datetime.now()/utcnow() - full path
                            elif isinstance(node.func.value, ast.Attribute):
                                if node.func.value.attr == "datetime":
                                    relative_path = py_file.relative_to(
                                        INFRASTRUCTURE_DIR
                                        if INFRASTRUCTURE_DIR.exists()
                                        else Path(__file__).parent.parent.parent
                                        / INFRASTRUCTURE_DIR
                                    )
                                    violations.append(
                                        f"{relative_path}:{node.lineno}: datetime.datetime.{node.func.attr}()"
                                    )

        assert not violations, (
            "datetime.now()/utcnow() found in infrastructure layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nTimestamps should be created in application layer "
            "(e.g., PipelineContext.started_at) and passed as parameters. "
            "See ADR-014."
        )

    def test_allowed_files_still_exist(
        self, infrastructure_python_files: list[Path]
    ) -> None:
        """Verify that files in ALLOWED_FILES actually exist.

        This prevents stale exceptions from accumulating.
        """
        existing_names = {f.name for f in infrastructure_python_files}
        missing = ALLOWED_FILES - existing_names

        assert not missing, (
            f"ALLOWED_FILES contains non-existent files: {missing}. "
            "Remove stale entries from the allowed list."
        )
