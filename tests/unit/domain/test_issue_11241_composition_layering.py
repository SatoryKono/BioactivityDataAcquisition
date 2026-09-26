"""Regression coverage for composition boundary policy (#11241)."""

from __future__ import annotations

from bioetl.domain.control_plane.artifact_lineage_layers import (
    resolve_required_artifact_lineage_layers,
)
from bioetl.domain.runtime.composition_boundary_policy import (
    memory_adaptive_sizing_allowed,
    pipeline_name_fallbacks,
    resolve_health_check_mode,
    resolve_metrics_publication_modes,
    resolve_seed_run_type,
    resolve_skip_gold,
    resolve_uniprot_mapping_databases,
)


def test_metrics_and_run_type_modes() -> None:
    assert resolve_metrics_publication_modes(
        metrics_enabled=True,
        metrics_server_enabled=False,
    ) == ("disabled", "best_effort_on_run_completion")
    assert resolve_seed_run_type("  rebuild ", None) == "rebuild"
    assert resolve_seed_run_type(None, None) == "incremental"
    assert resolve_seed_run_type(None, "wf") == ""


def test_runtime_projection_decisions() -> None:
    assert resolve_health_check_mode(
        test_mode=True,
        configured_mode="strict",
        default_health_check_mode="strict",
    ) == "probe"
    assert resolve_skip_gold(cli_skip_gold=False, gold_sink_enabled=False) is True
    assert memory_adaptive_sizing_allowed(exact_replay=True) is False
    assert pipeline_name_fallbacks("chembl_activity") == ("chembl", "activity")
    assert resolve_uniprot_mapping_databases(
        configured_from_db=None,
        configured_to_db=None,
    ) == ("ChEMBL", "UniProtKB")


def test_lineage_layers_skip_gold_without_sink() -> None:
    active, missing = resolve_required_artifact_lineage_layers(
        yaml_config=None,
        skip_gold=True,
    )
    assert active == ("bronze", "silver")
    assert missing == ()
