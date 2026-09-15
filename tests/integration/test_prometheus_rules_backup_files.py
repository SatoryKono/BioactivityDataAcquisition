# pyright: reportArgumentType=false
"""Guard Prometheus rule_files wildcards against backup copies."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def test_prometheus_rules_directory_has_no_duplicate_backup_rule_files() -> None:
    """Wildcard rule loading must not pick up backup/scratch copies of rule files."""
    rules_dir = Path("grafana/prometheus-rules")
    duplicate_candidates = sorted(
        path.name
        for path in rules_dir.iterdir()
        if path.is_file()
        and (
            path.suffix == ".bak"
            or path.name.endswith(".yml.bak")
            or "fixed" in path.name.lower()
            or "scratch" in path.name.lower()
        )
    )
    assert not duplicate_candidates, (
        "Prometheus rule_files uses /etc/prometheus/rules/*.yml, so backup/scratch "
        f"copies would be loaded as duplicate rules: {duplicate_candidates}"
    )
