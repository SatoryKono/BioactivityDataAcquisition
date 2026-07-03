"""Guard lock terminology consistency for Local-Only runtime surfaces."""

from __future__ import annotations

import pytest

from pathlib import Path
import re


pytestmark = pytest.mark.architecture

_REPO_ROOT = Path(__file__).resolve().parents[2]

_LOCK_SURFACE_FILES = (
    "src/bioetl/domain/ports/runtime/locking.py",
    "src/bioetl/infrastructure/locking/memory_lock.py",
    "src/bioetl/application/core/lifecycle/lock_runtime_service.py",
    "src/bioetl/application/core/lifecycle/lock_lifecycle.py",
    "src/bioetl/application/core/lifecycle/heartbeat.py",
    "src/bioetl/application/core/pipeline_services.py",
    "src/bioetl/application/core/runner.py",
    "src/bioetl/application/core/config.py",
    "src/bioetl/domain/config/pipeline.py",
    "src/bioetl/domain/composite/config.py",
    "src/bioetl/domain/constants.py",
    "src/bioetl/domain/exceptions/internal_lock.py",
    "src/bioetl/domain/types/enums.py",
    "src/bioetl/application/composite/runner_pkg/runner.py",
    "src/bioetl/composition/bootstrap/runtime/composite_bootstrap_builders.py",
    "src/bioetl/composition/bootstrap/cli/lock.py",
    "docs/04-reference/api/domain.md",
    "docs/04-reference/api/application.md",
    "docs/04-reference/cli.md",
    "docs/05-operations/runbooks/scaling.md",
    "docs/02-architecture/diagrams/guide/architecture-reference.md",
    "docs/02-architecture/diagrams/descriptions/architecture/18-lock-checkpoint-shutdown.md",
)

_FORBIDDEN_LOCK_DISTRIBUTED_PATTERN = re.compile(
    r"distributed(?:[\s-]){0,2}(?:lock|locking)|(?:lock|locking)(?:[\s-]){0,2}distributed",
    flags=re.IGNORECASE,
)


def test_lock_terminology_avoids_distributed_wording() -> None:
    """Local-Only lock surfaces should use runtime/process-local wording."""
    violations: list[str] = []
    for relative_path in _LOCK_SURFACE_FILES:
        path = _REPO_ROOT / relative_path
        content = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(content.splitlines(), start=1):
            if _FORBIDDEN_LOCK_DISTRIBUTED_PATTERN.search(line):
                violations.append(f"{relative_path}:{line_no}: {line.strip()}")

    assert not violations, (
        "Lock terminology drift detected; use runtime/process-local wording "
        "for Local-Only lock surfaces:\n" + "\n".join(violations)
    )
