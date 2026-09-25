"""#11102: unsupported deployment manifests stay out of kubectl apply steps."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT = ROOT / "docs" / "05-operations" / "deployment"
GUIDE = DEPLOYMENT / "deployment-guide.md"
MANIFESTS = (
    "k8s-deployment.yaml",
    "k8s-monitoring.yaml",
    "k8s-networking.yaml",
)


def test_deployment_guide_does_not_apply_unsupported_manifests() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    for name in MANIFESTS:
        manifest = (DEPLOYMENT / name).read_text(encoding="utf-8")
        assert "UNSUPPORTED" in manifest
        assert "Do not apply" in manifest
        assert f"kubectl apply -f {name}" not in guide
    assert "BIOETL_DQ_HARD_THRESHOLD" not in guide
    assert "BIOETL_DQ_SOFT_THRESHOLD" not in guide
    assert "change_me_to_random" not in (DEPLOYMENT / "k8s-deployment.yaml").read_text(
        encoding="utf-8"
    )
