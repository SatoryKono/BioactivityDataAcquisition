# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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


def test_vibe_powershell_launcher_passes_prompt_as_data() -> None:
    root = Path(__file__).resolve().parents[2]
    launcher = (root / "scripts" / "ai" / "vibe" / "launch.ps1").read_text(
        encoding="utf-8"
    )

    assert "wsl -e bash -c $VibeCommand -- $PromptB64" in launcher
    assert 'decoded_prompt="$(printf \'\'%s\'\' "$1" | base64 -d)"' in launcher
    assert '\\$(printf' not in launcher
