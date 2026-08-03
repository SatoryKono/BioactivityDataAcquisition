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
"""Structural contract tests for runtime runner builder seams."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from bioetl.composition.runtime_builders._runner_control_plane_artifact_policy import (
    requires_artifact_publication_closure,
    validate_artifact_recorder_attachment,
)
from bioetl.composition.runtime_builders._runner_control_plane_data_root_policy import (
    validate_strict_data_root_policy,
)
from bioetl.composition.runtime_builders import inputs_resolver
from bioetl.composition.runtime_builders import runner_builder
from bioetl.composition.runtime_builders import runner_control_plane_assembly

pytestmark = pytest.mark.unit


def test_runner_builder_uses_runtime_config_access_seam() -> None:
    source = Path(
        "src/bioetl/composition/runtime_builders/runner_builder.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "bioetl.composition.runtime_builders.config_access" in imported_modules, (
        "runner_builder must use the runtime config_access seam."
    )
    assert "bioetl.infrastructure.config.pipeline_config_api" not in imported_modules, (
        "runner_builder must not import pipeline_config_api directly."
    )
    assert (
        "bioetl.infrastructure.config.source_config_loader" not in imported_modules
    ), "runner_builder must not import source_config_loader directly."


def test_runner_builder_does_not_expose_legacy_wrapper_patch_points() -> None:
    for attr_name in (
        "VacuumSettings",
        "_assemble_vacuum_settings",
        "_assemble_runtime_config",
        "_assemble_filter_config",
        "_assemble_cached_bronze_context",
        "_build_observability_bundle",
        "_validate_pk_contract",
        "_resolve_health_check_mode",
        "_resolve_filter_batch_size",
        "build_observability_bundle",
        "assemble_vacuum_settings",
        "assemble_runtime_config",
        "assemble_filter_config",
        "assemble_cached_bronze_context",
    ):
        assert not hasattr(runner_builder, attr_name)


def test_runner_builder_uses_dedicated_control_plane_assembler() -> None:
    assert hasattr(runner_control_plane_assembly, "ControlPlaneSetupResult")
    assert hasattr(runner_control_plane_assembly, "assemble_runner_control_plane")
    assert not hasattr(runner_builder, "_ControlPlaneSetupResult")
    assert not hasattr(runner_builder, "_handle_control_plane_setup")


def test_strict_artifact_publication_policy_requires_complete_attachment() -> None:
    assert requires_artifact_publication_closure("best_effort") is False
    assert requires_artifact_publication_closure("replay_ready") is True

    validate_artifact_recorder_attachment(
        required_profile="best_effort",
        candidate_count=0,
        attached_count=0,
        missing_attach_method_count=0,
        failed_count=0,
    )
    validate_artifact_recorder_attachment(
        required_profile="replay_ready",
        candidate_count=2,
        attached_count=2,
        missing_attach_method_count=0,
        failed_count=0,
    )
    with pytest.raises(RuntimeError, match="no metadata-writer candidates"):
        validate_artifact_recorder_attachment(
            required_profile="replay_ready",
            candidate_count=0,
            attached_count=0,
            missing_attach_method_count=0,
            failed_count=0,
        )
    with pytest.raises(RuntimeError, match="recorder attachment was incomplete"):
        validate_artifact_recorder_attachment(
            required_profile="replay_ready",
            candidate_count=2,
            attached_count=1,
            missing_attach_method_count=1,
            failed_count=0,
        )


def test_strict_data_root_policy_requires_explicit_data_dir() -> None:
    explicit_settings = SimpleNamespace(data_dir="/tmp/bioetl-data")
    fallback_settings = SimpleNamespace(data_dir=None)

    validate_strict_data_root_policy(
        settings=fallback_settings,
        required_profile="best_effort",
    )
    validate_strict_data_root_policy(
        settings=explicit_settings,
        required_profile="replay_ready",
    )
    with pytest.raises(RuntimeError) as replay_ready_error:
        validate_strict_data_root_policy(
            settings=fallback_settings,
            required_profile="replay_ready",
        )
    assert "require an explicit settings.data_dir" in str(replay_ready_error.value)
    with pytest.raises(RuntimeError) as exact_replay_error:
        validate_strict_data_root_policy(
            settings=fallback_settings,
            required_profile="best_effort",
            exact_replay=True,
        )
    assert "require an explicit settings.data_dir" in str(exact_replay_error.value)


def test_runner_builder_leaf_keeps_runtime_builder_stages_split() -> None:
    """The public builder stays a leaf orchestration surface."""
    source = Path(
        "src/bioetl/composition/runtime_builders/runner_builder.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert len(source.splitlines()) <= 120
    assert {
        "bioetl.composition.runtime_builders._runner_builder_orchestration",
        "bioetl.composition.runtime_builders.runner_input_assembly",
        "bioetl.composition.runtime_builders.runner_control_plane_assembly",
    }.issubset(imported_modules)
    assert (
        "bioetl.composition.runtime_builders._run_manifest_data_roots"
        not in imported_modules
    )
    assert (
        "bioetl.composition.runtime_builders._run_manifest_planned_artifacts"
        not in imported_modules
    )
    assert (
        "bioetl.composition.runtime_builders._exact_replay_cached_bronze_context"
        not in imported_modules
    )
    assert "FileRunManifestStore" not in source
    assert "FileRunLedgerStore" not in source
    assert "build_planned_artifacts" not in source


def test_inputs_resolver_uses_explicit_resolved_vacuumsettings_name() -> None:
    assert hasattr(inputs_resolver, "ResolvedVacuumSettings")
    assert not hasattr(inputs_resolver, "VacuumSettings")


def test_inputs_resolver_public_surface_is_narrowed_to_reviewed_exports() -> None:
    assert set(inputs_resolver.__all__) == {
        "ResolvedVacuumSettings",
        "RunnerInputs",
        "prepare_runner_inputs",
        "resolve_health_check_mode",
    }
    assert "assemble_runtime_config" not in inputs_resolver.__all__
    assert "assemble_filter_config" not in inputs_resolver.__all__
    assert "adjust_batch_size_for_filter" not in inputs_resolver.__all__
