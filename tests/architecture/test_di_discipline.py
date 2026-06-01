"""Architecture test: DI discipline in application layer.

REQ-ARCH-DI-010: Application layer MUST NOT create infrastructure services.

Application services (LockRuntimeService, PreflightService, PostrunService,
MedallionLifecycleService, PipelineObserver) should be created in the composition
layer and injected via constructors.

See CLAUDE.md §2.2 Dependency Injection and §11 Anti-Patterns.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

# Path relative to project root
APPLICATION_DIR = Path("src/bioetl/application")

# Forbidden patterns: service creation in application layer.
# These services MUST be injected, not created directly.
FORBIDDEN_IN_APPLICATION = [
    "LockRuntimeService.create",
    "PreflightService(",
    "PostrunService(",
    "MedallionLifecycleService(",
    "PipelineObserver(",
]

# Files where these classes are defined (class definitions are allowed)
DEFINITION_FILES = {
    "PipelineObserver(": {"observability/observer.py"},
    "PreflightService(": {"core/preflight_service.py"},
    "PostrunService(": {"core/postrun/service.py"},
    "MedallionLifecycleService(": {"services/medallion_lifecycle.py"},
}


def _get_base_path(relative_path: Path) -> Path:
    """Resolve path - works from project root or tests directory."""
    if relative_path.exists():
        return relative_path
    return Path(__file__).parent.parent.parent / relative_path


def _line_pattern_violations(
    content: str, *, pattern: str, relative: Path
) -> list[str]:
    return [
        f"{relative}:{line_number}: {pattern}"
        for line_number, line in enumerate(content.splitlines(), 1)
        if pattern in line
    ]


def _pattern_violations_for_file(
    *,
    content: str,
    relative: Path,
    relative_str: str,
) -> list[str]:
    violations: list[str] = []
    for pattern in FORBIDDEN_IN_APPLICATION:
        allowed_files = DEFINITION_FILES.get(pattern, set())
        if relative_str in allowed_files:
            continue
        if pattern in content:
            violations.extend(
                _line_pattern_violations(content, pattern=pattern, relative=relative)
            )
    return violations


def _application_python_files(base: Path) -> list[Path]:
    return [
        py_file for py_file in base.rglob("*.py") if "composition" not in str(py_file)
    ]


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
        return _application_python_files(base)

    def test_no_service_creation_in_application(
        self, application_python_files: list[Path]
    ) -> None:
        """Application layer must not create infrastructure services.

        REQ-ARCH-DI-010: Services like LockRuntimeService, PreflightService,
        PostrunService, MedallionLifecycleService, and PipelineObserver must be
        injected, not created directly in application layer.

        These services should be created in composition/bootstrap.py or
        composition/factories/ and passed via constructor injection.

        See CLAUDE.md §2.2 and §11 Anti-Patterns.
        """
        base = _get_base_path(APPLICATION_DIR)
        violations = [
            violation
            for py_file in application_python_files
            for relative in [py_file.relative_to(base)]
            for relative_str in [str(relative).replace("\\", "/")]
            for violation in _pattern_violations_for_file(
                content=py_file.read_text(encoding="utf-8"),
                relative=relative,
                relative_str=relative_str,
            )
        ]

        assert not violations, (
            "DI discipline violations: Application layer must not create "
            "services directly.\n"
            "Move service creation to composition layer (factories/bootstrap).\n\n"
            "Violations found:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nSee CLAUDE.md §2.2 Dependency Injection for details."
        )
