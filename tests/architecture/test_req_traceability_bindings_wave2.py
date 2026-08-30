from __future__ import annotations

"""Wave2 concrete REQ traceability bindings — issue #9805.

Binds 26 concrete untraced REQ IDs to existing surfaces (existence guard).
Full list (26):

- REQ-DATA-007 (.parquet; _delta_log/)
- REQ-DATA-008 (SilverWriteMode; silver_filters)
- REQ-DELTA-001 (import deltalake)
- REQ-CLEAR-001 (test-rebuild-lifecycle-order)
- REQ-CLEAR-003 (test-incremental-skips-clear)
- REQ-CLEAR-004 (async def; await)
- REQ-NULL-003 (Pandera nullable)
- REQ-LOAD-001 (CheckpointRuntimeService; full_scan_only)
- REQ-LOAD-002 (tests/architecture/test_force_full_scan_publication.py)
- REQ-STACK-001 (httpx in adapters)
- REQ-STACK-003 (__init__)
- REQ-STACK-004 (ruff in dev)
- REQ-PYTHON-001 (ruff --select FA)
- REQ-PYTHON-002 (List/Dict/Set/Tuple)
- REQ-PYTHON-003 (Optional)
- REQ-TEST-003 (tests/fixtures/vcr/)
- REQ-GOV-001 (mypy --strict)
- REQ-GOV-002 (golden; os.replace)
- REQ-GOV-008 (.importlinter)
- REQ-GOV-009 (Delta; Pandera)
- REQ-SECRET-004 (.gitignore .env)
- REQ-CLEANUP-001 (async def aclose)
- REQ-ENV-003 (.env.example)
- REQ-DX-004 (docker-compose.yml legacy)
- REQ-DEP-001 (uv.lock; ==)
- REQ-DEP-002 (pip-audit CI)
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

_ROOT = Path(__file__).resolve().parents[2]

WAVE2_CONCRETE_SURFACES: dict[str, tuple[str, ...]] = {
    "REQ-DATA-007": (
        "src/bioetl/infrastructure/storage/silver_writer.py",
        "src/bioetl/infrastructure/storage/bronze_writer.py",
        "pyproject.toml",
    ),
    "REQ-DATA-008": (
        "src/bioetl/infrastructure/storage/silver_writer.py",
        "pyproject.toml",
    ),
    "REQ-DELTA-001": (
        "pyproject.toml",
        "src/bioetl/infrastructure/storage/delta_reader.py",
        "uv.lock",
    ),
    "REQ-CLEAR-001": (
        "src/bioetl/infrastructure/storage/silver_writer.py",
        "tests/architecture/test_medallion_invariants.py",
    ),
    "REQ-CLEAR-003": (
        "src/bioetl/infrastructure/storage/silver_writer.py",
        "tests/architecture/test_medallion_policy.py",
    ),
    "REQ-CLEAR-004": (
        "src/bioetl/infrastructure/storage/silver_writer.py",
        "pyproject.toml",
    ),
    "REQ-NULL-003": (
        "pyproject.toml",
        "src/bioetl/infrastructure/validation",
        "uv.lock",
    ),
    "REQ-LOAD-001": (
        "src/bioetl/infrastructure/checkpoint/local_checkpoint.py",
        "tests/architecture/test_force_full_scan_publication.py",
    ),
    "REQ-LOAD-002": (
        "tests/architecture/test_force_full_scan_publication.py",
        "src/bioetl/infrastructure/checkpoint/local_checkpoint.py",
    ),
    "REQ-STACK-001": (
        "src/bioetl/infrastructure/adapters",
        "pyproject.toml",
        "uv.lock",
    ),
    "REQ-STACK-003": (
        "src/bioetl/__init__.py",
        "src/bioetl/infrastructure/__init__.py",
    ),
    "REQ-STACK-004": ("pyproject.toml", ".pre-commit-config.yaml", "uv.lock"),
    "REQ-PYTHON-001": ("pyproject.toml", ".pre-commit-config.yaml"),
    "REQ-PYTHON-002": (
        "pyproject.toml",
        "src/bioetl/infrastructure/storage/silver_writer.py",
    ),
    "REQ-PYTHON-003": ("pyproject.toml", "src/bioetl/infrastructure/storage/atomic.py"),
    "REQ-TEST-003": ("tests/fixtures/vcr", "pyproject.toml"),
    "REQ-GOV-001": ("pyproject.toml", ".pre-commit-config.yaml"),
    "REQ-GOV-002": ("src/bioetl/infrastructure/storage/atomic.py", "pyproject.toml"),
    "REQ-GOV-008": (".importlinter", "pyproject.toml"),
    "REQ-GOV-009": (
        "pyproject.toml",
        "src/bioetl/infrastructure/storage/delta_reader.py",
    ),
    "REQ-SECRET-004": (".gitignore", ".env.example", ".gitleaks.toml"),
    "REQ-CLEANUP-001": (
        "src/bioetl/infrastructure/adapters",
        "src/bioetl/infrastructure/storage/silver_writer.py",
    ),
    "REQ-ENV-003": (".env.example", "pyproject.toml"),
    "REQ-DX-004": ("docker-compose.yml", "pyproject.toml"),
    "REQ-DEP-001": ("uv.lock", "pyproject.toml"),
    "REQ-DEP-002": ("pyproject.toml", ".pre-commit-config.yaml", ".github/workflows"),
}


def test_concrete_req_surfaces_exist() -> None:
    """All 26 Wave2 concrete REQ surfaces MUST exist on disk."""
    assert len(WAVE2_CONCRETE_SURFACES) == 26
    missing: list[str] = []
    for req_id, surfaces in sorted(WAVE2_CONCRETE_SURFACES.items()):
        for rel in surfaces:
            if not (_ROOT / rel).exists():
                missing.append(f"{req_id}: {rel}")
    assert not missing, "Missing surfaces:\n" + "\n".join(missing)
