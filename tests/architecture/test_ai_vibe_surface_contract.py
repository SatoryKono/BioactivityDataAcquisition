from pathlib import Path


def test_vibe_readme_prefers_top_level_ai_surface() -> None:
    root = Path(__file__).resolve().parents[2]
    readme = (root / "scripts" / "ai" / "vibe" / "README.md").read_text(
        encoding="utf-8"
    )

    assert "python -m scripts.ai vibe" in readme
    assert "compatibility path" in readme


def test_vibe_module_router_is_marked_as_compatibility_entrypoint() -> None:
    root = Path(__file__).resolve().parents[2]
    router = (root / "scripts" / "ai" / "vibe" / "__main__.py").read_text(
        encoding="utf-8"
    )

    assert "Compatibility entry point for Vibe launch tooling." in router
    assert (
        "The canonical public Python surface is ``python -m scripts.ai vibe``."
        in router
    )
