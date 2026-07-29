# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Structural contract tests for runner builder wiring seams."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition.runtime_builders import registry_manifest
from bioetl.composition.runtime_builders import runner_builder
from bioetl.composition.runtime_builders import runner_builder_wiring

pytestmark = pytest.mark.unit


def test_runner_builder_exposes_typed_wiring_bundles() -> None:
    """Runtime builder fan-in should be grouped behind typed wiring bundles."""
    assert hasattr(runner_builder, "RunnerBuilderWiring")
    assert hasattr(runner_builder, "RunnerFactoryWiring")
    assert hasattr(runner_builder, "RunnerInputWiring")

    create_registry = MagicMock(name="create_registry")
    wiring = runner_builder_wiring.resolve_runner_factory_wiring(
        runner_builder_wiring.RunnerFactoryWiring(),
        create_registry_fn=create_registry,
    )

    assert wiring.create_registry is create_registry
    assert callable(wiring.ensure_providers_loaded)
    assert callable(wiring.register_all_pipelines)


def test_runtime_builder_public_exports_stay_narrow() -> None:
    """RF-002 split must not add new public runtime-builder exports."""
    assert set(registry_manifest.PUBLIC_LAZY_EXPORTS) == {
        "build_pipeline_runner",
        "control_plane_root",
    }
    assert set(runner_builder.__all__) == {
        "PipelineRunnerProtocol",
        "RunnerBuilderWiring",
        "RunnerFactoryWiring",
        "RunnerInputWiring",
        "build_pipeline_runner",
        "ensure_providers_loaded",
        "load_source_config",
    }


