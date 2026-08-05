"""ARCH-REF-R2 / #7728: application/services root is package-first (no shims)."""

from __future__ import annotations

from pathlib import Path

import pytest

SERVICES_ROOT = Path("src/bioetl/application/services")

# After #7728 only package init may remain at root.
ALLOWED_ROOT_MODULES = frozenset({"__init__.py"})

REQUIRED_BC_PACKAGES = frozenset(
    {
        "control_plane",
        "execution",
        "dq",
        "lineage",
        "quality",
        "ops",
        "export_lineage",
        "workflow",
        "checkpoint",
        "contract",
    }
)


@pytest.mark.architecture
def test_services_bc_packages_exist() -> None:
    for name in REQUIRED_BC_PACKAGES:
        path = SERVICES_ROOT / name
        assert path.is_dir(), f"missing BC package: {path}"
        assert (path / "__init__.py").is_file(), f"missing package init: {path}"


@pytest.mark.architecture
def test_no_unexpected_root_service_modules() -> None:
    root_py = sorted(p.name for p in SERVICES_ROOT.glob("*.py"))
    unexpected = [name for name in root_py if name not in ALLOWED_ROOT_MODULES]
    assert unexpected == [], (
        "Root application/services modules must live in BC packages only. "
        f"Unexpected: {unexpected}"
    )


@pytest.mark.architecture
def test_services_root_is_package_init_only() -> None:
    assert list(SERVICES_ROOT.glob("*.py")) == [SERVICES_ROOT / "__init__.py"]
