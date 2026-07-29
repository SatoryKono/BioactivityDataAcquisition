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
from __future__ import annotations

from importlib import import_module

import pytest

from bioetl.composition import control_plane_service_access


pytestmark = pytest.mark.unit


def _owner_module(module_suffix: str) -> object:
    return import_module("bioetl.composition" + module_suffix)


def test_control_plane_service_access_reexports_services_owner_seams() -> None:
    owner_module = _owner_module("._services")

    assert control_plane_service_access.get_adr_service is owner_module.get_adr_service
    assert (
        control_plane_service_access.get_config_service
        is owner_module.get_config_service
    )
    assert (
        control_plane_service_access.get_export_service
        is owner_module.get_export_service
    )
    assert (
        control_plane_service_access.get_forensic_run_diff_service
        is owner_module.get_forensic_run_diff_service
    )
    assert (
        control_plane_service_access.get_historical_replay_closure_service
        is owner_module.get_historical_replay_closure_service
    )
    assert (
        control_plane_service_access.get_historical_replay_corpus_service
        is owner_module.get_historical_replay_corpus_service
    )
    assert (
        control_plane_service_access.get_historical_replay_universe_service
        is owner_module.get_historical_replay_universe_service
    )
    assert (
        control_plane_service_access.get_lineage_service
        is owner_module.get_lineage_service
    )
    assert (
        control_plane_service_access.get_lock_service is owner_module.get_lock_service
    )
    assert (
        control_plane_service_access.get_run_manifest_service
        is owner_module.get_run_manifest_service
    )


def test_control_plane_service_access_reexports_resource_owner_seams() -> None:
    owner_module = _owner_module("._resource_management")

    assert (
        control_plane_service_access.get_checkpoint_runtime_service
        is owner_module.get_checkpoint_runtime_service
    )


def test_control_plane_service_access_reexports_workflow_owner_seams() -> None:
    from bioetl.composition._workflow_services import (
        get_workflow_execution_service,
        get_workflow_inspection_service,
        get_workflow_runner_service,
        load_workflow_config,
    )

    assert (
        control_plane_service_access.get_workflow_execution_service
        is get_workflow_execution_service
    )
    assert (
        control_plane_service_access.get_workflow_inspection_service
        is get_workflow_inspection_service
    )
    assert (
        control_plane_service_access.get_workflow_runner_service
        is get_workflow_runner_service
    )
    assert control_plane_service_access.load_workflow_config is load_workflow_config


def test_control_plane_service_access_reexports_bootstrap_owner_seams() -> None:
    from bioetl.composition.bootstrap.cli import (
        bootstrap_control_plane_lifecycle_store,
    )
    from bioetl.composition.bootstrap.cli.run_manifest import (
        persist_historical_replay_closure_report,
        persist_historical_replay_universe_report,
    )
    from bioetl.composition.config_catalog import list_configured_pipeline_names

    assert (
        control_plane_service_access.bootstrap_control_plane_lifecycle_store
        is bootstrap_control_plane_lifecycle_store
    )
    assert (
        control_plane_service_access.persist_historical_replay_closure_report
        is persist_historical_replay_closure_report
    )
    assert (
        control_plane_service_access.persist_historical_replay_universe_report
        is persist_historical_replay_universe_report
    )
    assert (
        control_plane_service_access.list_configured_pipeline_names
        is list_configured_pipeline_names
    )
