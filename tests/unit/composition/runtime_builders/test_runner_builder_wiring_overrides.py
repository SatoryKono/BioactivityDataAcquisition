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
"""Override contracts for runner builder factory and input wiring."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition.runtime_builders import runner_builder_wiring

pytestmark = pytest.mark.unit


def test_runner_input_wiring_resolves_overrides() -> None:
    """Input wiring should resolve optional active overrides correctly."""
    get_settings_mock = MagicMock(name="get_settings")
    load_pipeline_config_mock = MagicMock(name="load_pipeline_config")
    load_source_config_mock = MagicMock(name="load_source_config")

    wiring = runner_builder_wiring.resolve_runner_input_wiring(
        runner_builder_wiring.RunnerInputWiring(),
        get_settings_fn=get_settings_mock,
        load_pipeline_config_fn=load_pipeline_config_mock,
        load_source_config_fn=load_source_config_mock,
    )

    assert wiring.get_settings is get_settings_mock
    assert wiring.load_pipeline_config is load_pipeline_config_mock
    assert callable(wiring.load_source_config)
    assert wiring.load_source_config is load_source_config_mock
    assert wiring.build_observability_bundle is None


def test_runner_factory_wiring_preserves_unmodified_collaborators() -> None:
    original = runner_builder_wiring.RunnerFactoryWiring()
    ensure_providers_loaded = MagicMock(name="ensure_providers_loaded")
    register_all_pipelines = MagicMock(name="register_all_pipelines")

    resolved = runner_builder_wiring.resolve_runner_factory_wiring(
        original,
        ensure_providers_loaded_fn=ensure_providers_loaded,
        register_all_pipelines_fn=register_all_pipelines,
    )

    assert resolved is not original
    assert resolved.create_registry is original.create_registry
    assert resolved.ensure_providers_loaded is ensure_providers_loaded
    assert resolved.register_all_pipelines is register_all_pipelines
