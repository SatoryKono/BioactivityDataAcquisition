"""Tests for run-context assembly control-plane hash surfaces."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from bioetl.composition.factories.pipeline.run_context_factory import RunContextFactory
from bioetl.domain.types import RunID, RunType


def _factory() -> RunContextFactory:
    return RunContextFactory(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type_extractor=lambda _pipeline_name: "activity",
        pipeline_version_getter=lambda _yaml_config: "1.0.0",
        git_commit_getter=lambda: "abc123",
        config_hash_getter=lambda _yaml_config: "resolved-hash",
        transform_version_getter=lambda _yaml_config: None,
        transform_steps_getter=lambda _yaml_config: (),
        contract_identity_resolver=lambda _provider, _entity: (
            "chembl.activity",
            "1.0.0",
            None,
            None,
            None,
        ),
    )


def test_run_context_factory_preserves_distinct_config_hash_surfaces() -> None:
    """Legacy, resolved, and effective config hashes are independent anchors."""
    context = _factory().create(
        run_id=RunID(uuid4()),
        runtime=SimpleNamespace(run_type=RunType.INCREMENTAL),
        yaml_config=SimpleNamespace(),
        config_hash="legacy-config-hash",
        resolved_config_hash="resolved-config-hash",
        effective_config_hash="effective-config-hash",
    )

    assert context.config_hash == "legacy-config-hash"
    assert context.resolved_config_hash == "resolved-config-hash"
    assert context.effective_config_hash == "effective-config-hash"


def test_run_context_factory_does_not_alias_missing_effective_hash() -> None:
    """Missing effective hash remains explicit instead of falling back to config_hash."""
    context = _factory().create(
        run_id=RunID(uuid4()),
        runtime=SimpleNamespace(run_type=RunType.INCREMENTAL),
        yaml_config=SimpleNamespace(),
        config_hash="legacy-config-hash",
        resolved_config_hash="resolved-config-hash",
        effective_config_hash=None,
    )

    assert context.config_hash == "legacy-config-hash"
    assert context.resolved_config_hash == "resolved-config-hash"
    assert context.effective_config_hash is None
