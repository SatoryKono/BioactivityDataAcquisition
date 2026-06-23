"""Architecture guard for canonical test topology paths."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.architecture
def test_cli_unit_tests_use_interfaces_cli_canonical_path() -> None:
    """CLI unit tests should live under tests/unit/interfaces/cli."""
    legacy_unit_root = ROOT / "tests" / "unit"
    legacy_cli_dir = legacy_unit_root / "cli"
    legacy_top_level_cli = legacy_unit_root / "test_cli.py"
    legacy_interfaces_dir = legacy_unit_root / "interfaces"

    legacy_cli_tests = sorted(
        path.relative_to(ROOT).as_posix() for path in legacy_cli_dir.rglob("test_*.py")
    )
    legacy_interfaces_cli_tests = sorted(
        path.relative_to(ROOT).as_posix()
        for path in legacy_interfaces_dir.glob("test_*.py")
        if path.name.startswith("test_cli")
        or path.name
        in {
            "test_exit_codes.py",
            "test_run_all_command.py",
            "test_run_all_service_mock.py",
            "test_vacuum_commands.py",
        }
    )

    assert not legacy_cli_tests, (
        "legacy tests/unit/cli ownership is deprecated; move files under "
        "tests/unit/interfaces/cli:\n"
        + "\n".join(f"  - {path}" for path in legacy_cli_tests)
    )
    assert not legacy_top_level_cli.exists(), (
        "legacy top-level tests/unit/test_cli.py is deprecated; move it under "
        "tests/unit/interfaces/cli/"
    )
    assert not legacy_interfaces_cli_tests, (
        "CLI unit tests should not live directly under tests/unit/interfaces:\n"
        + "\n".join(f"  - {path}" for path in legacy_interfaces_cli_tests)
    )


@pytest.mark.architecture
def test_infrastructure_unit_tests_use_canonical_roots() -> None:
    """Unit-style infrastructure tests should not remain under tests/infrastructure."""
    legacy_tests = sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "tests" / "infrastructure").rglob("test_*.py")
    )
    assert not legacy_tests, (
        "legacy tests/infrastructure paths are deprecated; move unit-style coverage "
        "under tests/unit/infrastructure or tests/unit/composition:\n"
        + "\n".join(f"  - {path}" for path in legacy_tests)
    )


@pytest.mark.architecture
def test_legacy_unit_test_paths_are_retired() -> None:
    """Legacy top-level and duplicate unit test paths should stay retired."""
    deprecated_paths = [
        "tests/unit/test_bootstrap.py",
        "tests/unit/test_context.py",
        "tests/unit/test_error_classifier.py",
        "tests/unit/test_ports.py",
        "tests/unit/test_registry.py",
        "tests/unit/test_transformations.py",
        "tests/unit/test_types.py",
        "tests/unit/application/test_error_classifier.py",
        "tests/unit/domain/test_types.py",
        "tests/unit/infrastructure/adapters/test_fallback_orchestrator.py",
    ]

    existing_paths = [path for path in deprecated_paths if (ROOT / path).exists()]

    assert not existing_paths, (
        "legacy unit test paths are deprecated; keep tests under their canonical "
        "layer/package owners:\n" + "\n".join(f"  - {path}" for path in existing_paths)
    )


@pytest.mark.architecture
def test_top_level_unit_root_has_no_legacy_test_modules() -> None:
    """`tests/unit/` should not accumulate layer-less top-level test modules."""
    top_level_tests = sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "tests" / "unit").glob("test_*.py")
    )

    assert not top_level_tests, (
        "top-level tests/unit/test_*.py files are deprecated; move them under the "
        "owning layer/package:\n" + "\n".join(f"  - {path}" for path in top_level_tests)
    )


@pytest.mark.architecture
def test_tests_root_has_no_legacy_top_level_test_modules() -> None:
    """`tests/` root should not accumulate unlabeled lane-less modules."""
    top_level_tests = sorted(
        path.relative_to(ROOT).as_posix() for path in (ROOT / "tests").glob("test_*.py")
    )

    assert not top_level_tests, (
        "top-level tests/test_*.py files are deprecated; move them into "
        "tests/architecture, tests/integration, or another owning lane:\n"
        + "\n".join(f"  - {path}" for path in top_level_tests)
    )


@pytest.mark.architecture
def test_retired_synthetic_e2e_modules_stay_absent() -> None:
    """Synthetic/mock-heavy suites retired from E2E must not reappear there."""
    retired_paths = [
        "tests/e2e/test_checkpoint_e2e.py",
        "tests/e2e/test_gold_layer_e2e.py",
        "tests/e2e/test_pipeline_with_dq_errors_e2e.py",
        "tests/e2e/test_run_types_e2e.py",
    ]

    existing_paths = [path for path in retired_paths if (ROOT / path).exists()]

    assert not existing_paths, (
        "synthetic E2E modules were retired because they bypassed runtime/bootstrap "
        "seams; keep that coverage in unit/integration lanes:\n"
        + "\n".join(f"  - {path}" for path in existing_paths)
    )
