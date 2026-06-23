from __future__ import annotations

import pytest

from bioetl.composition import control_plane_service_access


pytestmark = pytest.mark.unit


def test_control_plane_service_access_reexports_services_owner_seams() -> None:
    from bioetl.composition._services import (
        get_adr_service,
        get_config_service,
        get_export_service,
        get_forensic_run_diff_service,
        get_historical_replay_closure_service,
        get_historical_replay_corpus_service,
        get_historical_replay_universe_service,
        get_lineage_service,
        get_lock_service,
        get_run_manifest_service,
    )

    assert control_plane_service_access.get_adr_service is get_adr_service
    assert control_plane_service_access.get_config_service is get_config_service
    assert control_plane_service_access.get_export_service is get_export_service
    assert (
        control_plane_service_access.get_forensic_run_diff_service
        is get_forensic_run_diff_service
    )
    assert (
        control_plane_service_access.get_historical_replay_closure_service
        is get_historical_replay_closure_service
    )
    assert (
        control_plane_service_access.get_historical_replay_corpus_service
        is get_historical_replay_corpus_service
    )
    assert (
        control_plane_service_access.get_historical_replay_universe_service
        is get_historical_replay_universe_service
    )
    assert control_plane_service_access.get_lineage_service is get_lineage_service
    assert control_plane_service_access.get_lock_service is get_lock_service
    assert (
        control_plane_service_access.get_run_manifest_service
        is get_run_manifest_service
    )


def test_control_plane_service_access_reexports_resource_owner_seams() -> None:
    from bioetl.composition._resource_management import get_checkpoint_runtime_service

    assert (
        control_plane_service_access.get_checkpoint_runtime_service
        is get_checkpoint_runtime_service
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
