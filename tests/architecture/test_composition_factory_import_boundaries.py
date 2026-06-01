"""Architecture tests for composition factory import boundaries."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

def test_runner_factory_has_no_bootstrap_back_edge(src_dir: Path) -> None:
    """runner_factory must not depend on composition.bootstrap re-export layer."""
    runner_factory = (
        src_dir / "bioetl" / "composition" / "factories" / "pipeline" / "runner.py"
    )
    content = runner_factory.read_text(encoding="utf-8")

    assert "bioetl.composition.bootstrap" not in content, (
        "composition.factories.runner_factory must not import from composition.bootstrap; "
        "import leaf runtime builder directly to avoid back-edge dependencies"
    )

    assert "bioetl.composition.runtime_builders.runner_builder" in content, (
        "composition.factories.runner_factory should import leaf builder module "
        "for pipeline runner construction"
    )
