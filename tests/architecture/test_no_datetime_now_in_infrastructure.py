"""Architecture test: datetime.now() only in application/composition layers.

REQ-ARCH-031: Single source of truth for timestamps.
Timestamps should be created in application layer and passed down.
See docs/02-architecture/decisions/ADR-014-deterministic-writes.md
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Path relative to project root
INFRASTRUCTURE_DIR = Path("src/bioetl/infrastructure")

# Files allowed to use datetime.now() - with justification
ALLOWED_FILES: set[str] = {
    # Operations use datetime.now() for calculating retention periods (cleanup)
    "operations.py",
    # Lineage tracking needs real-time timestamps for provenance
    "lineage.py",
    # Anomaly detectors need real-time timestamps for monitoring
    "detector.py",
    "iqr.py",
    "mad.py",
    "zscore.py",
    # ChEMBL client uses timestamps for caching logic
    "client.py",
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
        """Infrastructure MUST NOT call datetime.now() directly.

        Timestamps should be created in application layer (e.g., PipelineContext)
        and passed as parameters to infrastructure components.

        Exceptions:
        - operations.py: Uses datetime.now() for calculating retention cutoffs
        """
        violations = []

        for py_file in infrastructure_python_files:
            if py_file.name in ALLOWED_FILES:
                continue

            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check for datetime.now() patterns
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr == "now":
                            # datetime.now() after "from datetime import datetime"
                            if isinstance(node.func.value, ast.Name):
                                if node.func.value.id == "datetime":
                                    relative_path = py_file.relative_to(
                                        INFRASTRUCTURE_DIR
                                        if INFRASTRUCTURE_DIR.exists()
                                        else Path(__file__).parent.parent.parent
                                        / INFRASTRUCTURE_DIR
                                    )
                                    violations.append(
                                        f"{relative_path}:{node.lineno}: datetime.now()"
                                    )
                            # datetime.datetime.now() - full path
                            elif isinstance(node.func.value, ast.Attribute):
                                if node.func.value.attr == "datetime":
                                    relative_path = py_file.relative_to(
                                        INFRASTRUCTURE_DIR
                                        if INFRASTRUCTURE_DIR.exists()
                                        else Path(__file__).parent.parent.parent
                                        / INFRASTRUCTURE_DIR
                                    )
                                    violations.append(
                                        f"{relative_path}:{node.lineno}: datetime.datetime.now()"
                                    )

        assert not violations, (
            "datetime.now() found in infrastructure layer:\n"
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
