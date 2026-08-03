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
"""Enforce sanctioned HTTP client usage across adapter-family runtime code."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ADAPTER_ROOT = ROOT / "src" / "bioetl" / "infrastructure" / "adapters"
SANCTIONED_HTTP_ROOT = ADAPTER_ROOT / "http"
FORBIDDEN_PATTERNS = (
    "import requests",
    "from requests import",
    "httpx.AsyncClient(",
    "httpx.Client(",
    "from httpx import AsyncClient",
    "from httpx import Client",
)


def _iter_runtime_adapter_files() -> list[Path]:
    return sorted(
        path
        for path in ADAPTER_ROOT.rglob("*.py")
        if SANCTIONED_HTTP_ROOT not in path.parents and path != SANCTIONED_HTTP_ROOT
    )


@pytest.mark.architecture
def test_runtime_adapters_use_sanctioned_http_surface_only() -> None:
    violations: list[str] = []
    for path in _iter_runtime_adapter_files():
        content = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in content:
                violations.append(f"{path.relative_to(ROOT)}: {pattern}")

    assert not violations, (
        "Runtime adapters must route HTTP through the sanctioned "
        "`infrastructure.adapters.http` surface:\n" + "\n".join(violations)
    )
