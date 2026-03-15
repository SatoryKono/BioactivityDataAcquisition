"""Architecture checks for composite CLI runtime-config import boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("relative_path", "canonical_import"),
    [
        (
            Path("bioetl/interfaces/cli/commands/run_composite.py"),
            (
                "from bioetl.application.composite.runner_pkg.runner_models import "
                "CompositeRuntimeConfig"
            ),
        ),
        (
            Path("bioetl/interfaces/cli/commands/run_composite_runtime.py"),
            (
                "from bioetl.application.composite.runner_pkg.runner_models import "
                "CompositeRuntimeConfig"
            ),
        ),
        (
            Path("bioetl/interfaces/cli/commands/run_composite_helpers.py"),
            (
                "from bioetl.application.composite.runner_pkg.runner_models import "
                "CompositeRuntimeConfig"
            ),
        ),
    ],
)
def test_composite_cli_modules_import_runtime_config_from_runner_models(
    src_dir: Path,
    relative_path: Path,
    canonical_import: str,
) -> None:
    """CLI helpers should avoid runtime import of the full runner facade."""
    file_path = src_dir / relative_path
    content = file_path.read_text(encoding="utf-8")

    assert canonical_import in content, (
        f"{relative_path} must import CompositeRuntimeConfig from runner_models."
    )
    assert (
        "from bioetl.application.composite.runner_pkg import CompositeRuntimeConfig"
        not in content
    ), f"{relative_path} must not import CompositeRuntimeConfig from runner_pkg facade."
