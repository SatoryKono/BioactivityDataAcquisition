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
"""Architecture checks for composite runtime-config import boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.architecture
@pytest.mark.parametrize(
    "relative_path",
    [
        Path("bioetl/interfaces/cli/commands/run_composite.py"),
        Path("bioetl/interfaces/cli/commands/domains/composite/execution.py"),
        Path("bioetl/interfaces/cli/commands/domains/composite/runtime.py"),
        Path("bioetl/interfaces/cli/commands/domains/composite/support.py"),
        Path("bioetl/composition/bootstrap/runtime/composite.py"),
        Path("bioetl/composition/bootstrap/runtime/runtime_basics.py"),
        Path("bioetl/composition/bootstrap/runtime/runner_factory_builder_service.py"),
        Path(
            "bioetl/composition/bootstrap/runtime/composite_support_services_factory.py"
        ),
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
        "from bioetl.application.composite.runtime_models import CompositeRuntimeConfig"
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
        "CompositeRuntimeConfig" not in content
    ), f"{relative_path} must not import CompositeRuntimeConfig from runner_models."


@pytest.mark.architecture
def test_composite_support_service_builder_shims_stay_removed(src_dir: Path) -> None:
    """Facade-only builder/bundle shims were collapsed in #10595 and must not return."""
    runtime_dir = src_dir / "bioetl" / "composition" / "bootstrap" / "runtime"
    removed = (
        "composite_support_service_builders.py",
        "composite_support_service_bundles.py",
        "composite_bootstrap_builders.py",
    )
    present = [name for name in removed if (runtime_dir / name).exists()]
    assert present == [], f"re-export shims must stay deleted: {present}"
