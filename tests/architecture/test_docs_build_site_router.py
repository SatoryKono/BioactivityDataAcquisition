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
"""Architecture checks for the packaged docs build route."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import yaml


pytestmark = pytest.mark.architecture


def test_build_site_router_targets_importable_backend() -> None:
    root = Path(__file__).resolve().parents[2]
    router = (root / "scripts" / "docs" / "__main__.py").read_text(encoding="utf-8")
    shell_wrapper = (root / "scripts" / "docs" / "build_docs_site.sh").read_text(
        encoding="utf-8"
    )

    assert '"build-site": "scripts.docs.build.mkdocs_build"' in router
    assert 'ROUTER_MODULE="scripts.docs"' in shell_wrapper
    assert 'ROUTER_COMMAND="build-site"' in shell_wrapper
    assert "TMP_SITE_DIR=" not in shell_wrapper
    assert "OUT_SITE_DIR=" not in shell_wrapper
    assert "LEGACY_SITE_DIR=" not in shell_wrapper

    module = importlib.import_module("scripts.docs.build.mkdocs_build")
    assert hasattr(module, "main")


def test_strict_docs_build_enforces_heading_anchors() -> None:
    root = Path(__file__).resolve().parents[2]
    config = yaml.safe_load((root / "mkdocs.yml").read_text(encoding="utf-8"))

    assert config["validation"]["links"]["anchors"] in {"warn", "error"}
    assert "attr_list" in config["markdown_extensions"]
