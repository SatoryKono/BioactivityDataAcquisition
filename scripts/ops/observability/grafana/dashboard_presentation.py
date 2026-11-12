"""Select a fixed, source-verified dashboard presentation within this checkout."""

from __future__ import annotations

import os
from pathlib import Path


def dashboard_directory(root: Path) -> Path:
    profile = os.environ.get("BIOETL_GRAFANA_PRESENTATION_PROFILE", "native")
    if profile == "native":
        return root / "grafana/dashboards"
    if profile != "adaptive":
        raise ValueError("Dashboard presentation must be native or adaptive")
    from scripts.ops.observability.grafana.generate_adaptive_dashboards import generate

    if not generate(root, check=True):
        raise ValueError("Adaptive profile is stale; run generate_adaptive_dashboards")
    from scripts.ops.observability.grafana.start_adaptive_monitoring import (
        verify_bundle,
    )

    verify_bundle(root)
    return root / "grafana/dashboards-adaptive"
