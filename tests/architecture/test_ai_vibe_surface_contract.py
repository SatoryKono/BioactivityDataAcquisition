from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture


def test_vibe_readme_prefers_top_level_ai_surface() -> None:
    root = Path(__file__).resolve().parents[2]
    readme = (root / "scripts" / "ai" / "vibe" / "README.md").read_text(
        encoding="utf-8"
    )

    assert "python -m scripts.ai vibe" in readme
    assert "python -m scripts.ai.vibe" in readme
    assert "retired on 2026-05-21" in readme


def test_vibe_module_router_compatibility_entrypoint_stays_retired() -> None:
    root = Path(__file__).resolve().parents[2]
    router = root / "scripts" / "ai" / "vibe" / "__main__.py"
    top_level_router = (root / "scripts" / "ai" / "__main__.py").read_text(
        encoding="utf-8"
    )

    assert not router.exists()
    assert "scripts.ai.vibe" not in top_level_router
    assert "launch.sh" in top_level_router
    assert "launch.ps1" in top_level_router
