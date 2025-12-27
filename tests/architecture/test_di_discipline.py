"""Architecture test: DI discipline in application layer.

REQ-ARCH-DI-010: Application layer MUST NOT create infrastructure services.

Application services (LockManager, PreflightService, PostrunService,
LifecycleOrchestrator, PipelineObserver) should be created in the composition
layer and injected via constructors.

See CLAUDE.md §2.2 Dependency Injection and §11 Anti-Patterns.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Path relative to project root
APPLICATION_DIR = Path("src/bioetl/application")

# Forbidden patterns: service creation in application layer.
# These services MUST be injected, not created directly.
FORBIDDEN_IN_APPLICATION = [
    "LockManager.create",
    "PreflightService(",
    "PostrunService(",
    "LifecycleOrchestrator(",
    "PipelineObserver(",
]

# Files where these classes are defined (class definitions are allowed)
DEFINITION_FILES = {
    "PipelineObserver(": {"observability/observer.py"},
    "PreflightService(": {"core/preflight_service.py"},
    "PostrunService(": {"core/postrun_service.py"},
    "LifecycleOrchestrator(": {"core/lifecycle_orchestrator.py"},
}


def _get_base_path(relative_path: Path) -> Path:
    """Resolve path - works from project root or tests directory."""
    if relative_path.exists():
        return relative_path
    return Path(__file__).parent.parent.parent / relative_path


class TestDIDiscipline:
    """Tests ensuring DI discipline in application layer."""

    @pytest.fixture
    def application_python_files(self) -> list[Path]:
        """Get all Python files in application directory.

        Excludes composition layer files since they are allowed to create services.
        """
        base = _get_base_path(APPLICATION_DIR)
        if not base.exists():
            pytest.skip("Application layer not found")

        files = []
        for py_file in base.rglob("*.py"):
            # Skip composition layer
            if "composition" in str(py_file):
                continue
            files.append(py_file)
        return files

    def test_no_service_creation_in_application(
        self, application_python_files: list[Path]
    ) -> None:
        """Application layer must not create infrastructure services.

        REQ-ARCH-DI-010: Services like LockManager, PreflightService,
        PostrunService, LifecycleOrchestrator, and PipelineObserver must be
        injected, not created directly in application layer.

        These services should be created in composition/bootstrap.py or
        composition/factories/ and passed via constructor injection.

        See CLAUDE.md §2.2 and §11 Anti-Patterns.
        """
        violations = []

        for py_file in application_python_files:
            content = py_file.read_text(encoding="utf-8")
            relative = py_file.relative_to(_get_base_path(APPLICATION_DIR))
            relative_str = str(relative).replace("\\", "/")

            for pattern in FORBIDDEN_IN_APPLICATION:
                # Skip files where the class is defined
                allowed_files = DEFINITION_FILES.get(pattern, set())
                if relative_str in allowed_files:
                    continue

                if pattern in content:
                    # Find line numbers for better error messages
                    for i, line in enumerate(content.splitlines(), 1):
                        if pattern in line:
                            violations.append(f"{relative}:{i}: {pattern}")

        assert not violations, (
            "DI discipline violations: Application layer must not create "
            "services directly.\n"
            "Move service creation to composition layer (factories/bootstrap).\n\n"
            "Violations found:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nSee CLAUDE.md §2.2 Dependency Injection for details."
        )
