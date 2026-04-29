"""Architecture checks for the packaged docs build route."""

from __future__ import annotations

import importlib
from pathlib import Path


def test_build_site_router_targets_importable_backend() -> None:
    root = Path(__file__).resolve().parents[2]
    router = (root / "scripts" / "docs" / "__main__.py").read_text(encoding="utf-8")
    shell_wrapper = (root / "scripts" / "docs" / "build_docs_site.sh").read_text(
        encoding="utf-8"
    )

    assert '"build-site": "scripts.docs.build.mkdocs_build"' in router
    assert 'BUILD_MODULE="scripts.docs.build.mkdocs_build"' in shell_wrapper

    module = importlib.import_module("scripts.docs.build.mkdocs_build")
    assert hasattr(module, "main")
