"""Architecture checks for composite runtime-config import boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.architecture
@pytest.mark.parametrize(
    "relative_path",
    [
        Path("bioetl/interfaces/cli/commands/run_composite.py"),
        Path("bioetl/interfaces/cli/commands/run_composite_runtime.py"),
        Path("bioetl/interfaces/cli/commands/run_composite_helpers.py"),
        Path("bioetl/composition/bootstrap/runtime/composite.py"),
        Path("bioetl/composition/bootstrap/runtime/runtime_basics.py"),
        Path("bioetl/composition/bootstrap/runtime/runner_factory_builder_service.py"),
        Path("bioetl/composition/bootstrap/runtime/composite_support_service_builders.py"),
        Path("bioetl/composition/bootstrap/runtime/composite_support_services_factory.py"),
        Path("bioetl/composition/bootstrap/runtime/composite_bootstrap_builders.py"),
        Path("bioetl/composition/bootstrap/runtime/runner_assembly.py"),
    ],
)
def test_composite_runtime_modules_import_runtime_config_from_stable_facade(
    src_dir: Path,
    relative_path: Path,
) -> None:
    """Runtime-facing modules should import CompositeRuntimeConfig via stable facade."""
    file_path = src_dir / relative_path
    content = file_path.read_text(encoding="utf-8")
    canonical_import = (
        "from bioetl.application.composite.runtime_models import "
        "CompositeRuntimeConfig"
    )

    assert canonical_import in content, (
        f"{relative_path} must import CompositeRuntimeConfig from runtime_models."
    )
    assert (
        "from bioetl.application.composite.runner_pkg import CompositeRuntimeConfig"
        not in content
    ), f"{relative_path} must not import CompositeRuntimeConfig from runner_pkg facade."
    assert (
        "from bioetl.application.composite.runner_pkg.runner_models import "
        "CompositeRuntimeConfig"
        not in content
    ), f"{relative_path} must not import CompositeRuntimeConfig from runner_models."
