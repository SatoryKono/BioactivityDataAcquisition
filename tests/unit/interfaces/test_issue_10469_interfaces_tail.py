"""Behavioral coverage for residual CLI and HTTP guard branches."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import click
import pytest

from bioetl.domain.types import RunType
from bioetl.domain.workflow import WorkflowRunOptionsConfig
from bioetl.interfaces.cli.commands import _run_manifest_historical_support
from bioetl.interfaces.cli.commands._workflow_override_support import (
    build_workflow_run_options_override,
)
from bioetl.interfaces.cli.commands.domains.composite.runtime import (
    CompositeRuntimeCliInput,
    _build_overridden_cli_input,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    resolve_run_all_registry,
)
from bioetl.interfaces.http import _health_server_checkpoint_lookup
from bioetl.interfaces.http import _health_server_control_plane_scope
from bioetl.interfaces.http.control_plane_identity import formatting, replay_extractors


pytestmark = pytest.mark.unit


def test_json_boolean_loader_accepts_false_without_coercion() -> None:
    assert (
        _run_manifest_historical_support._require_json_bool(
            False,
            field_name="certified",
        )
        is False
    )


def test_workflow_override_kwargs_wrapper_preserves_explicit_values() -> None:
    override = build_workflow_run_options_override(dry_run=False, limit=7)

    assert isinstance(override, WorkflowRunOptionsConfig)
    assert override.dry_run is False
    assert override.limit == 7


def test_composite_runtime_rejects_unknown_override_key() -> None:
    with pytest.raises(ValueError, match="Unknown composite runtime override keys: typo"):
        _build_overridden_cli_input(
            CompositeRuntimeCliInput(),
            {"typo": True},
        )


def test_run_all_registry_resolves_click_context_object() -> None:
    registry = SimpleNamespace(list_pipelines=lambda: ["chembl_activity"])
    context = click.Context(click.Command("run-all"), obj=registry)

    with patch("click.get_current_context", return_value=context):
        assert resolve_run_all_registry() is registry


def test_stable_json_default_stringifies_nonstandard_value() -> None:
    value = SimpleNamespace(name="sample")

    assert formatting._json_stable_default(value) == str(value)


def test_replay_mode_falls_back_to_native_run_type() -> None:
    manifest = SimpleNamespace(
        replay_of_run_id=None,
        replay_of_manifest_id=None,
        run_type=RunType.INCREMENTAL,
        launch_context={},
        runtime_config={},
        resolved_config={},
    )

    assert replay_extractors.replay_mode(manifest) == "incremental"


def test_control_plane_scope_requires_manifest_port() -> None:
    host = SimpleNamespace(_run_manifest_port=None)

    with pytest.raises(RuntimeError, match="run_manifest_port is required"):
        _health_server_control_plane_scope.resolve_control_plane_identity_scope(
            host,
            {},
        )


@pytest.mark.asyncio
async def test_checkpoint_lookup_reports_unavailable_port() -> None:
    host = SimpleNamespace(_checkpoint_port=None)
    scope = _health_server_control_plane_scope._IdentityScope(
        requested_pipeline="chembl_activity",
        selected_pipelines=("chembl_activity",),
        selected_run_types=(),
        selected_run_id=None,
        resolved_manifest=None,
        resolved_via="selection_required",
    )

    result = await _health_server_checkpoint_lookup.load_checkpoint_freshness_evidence(
        host,
        scope=scope,
        target_pipeline="chembl_activity",
    )

    assert result == (None, "checkpoint_port_unavailable", None, False)
