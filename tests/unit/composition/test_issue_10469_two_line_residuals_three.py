"""Behavior coverage for remaining two-line composition residuals in #10469."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.pipeline import _registry_factory_catalog as catalog
from bioetl.composition.factories.services._bundle_support import (
    ServiceBundleDependencies,
    _PipelineCreationIdentity,
    build_pipeline_creation_inputs,
    resolve_service_bundle_dependencies,
)
from bioetl.composition.factories.services._record_processor_policy_support import (
    extract_gold_schema_policy_by_version,
    extract_hash_policy_by_version,
)
from bioetl.composition.factories.storage.health_mixin import StorageBundleHealthMixin
from bioetl.composition.providers._creation import (
    ProviderCreator,
    ProviderDataSourceCreationRequest,
    create_provider_data_source,
)
from bioetl.composition.runtime_builders import _run_manifest_builder_policy as policy
from bioetl.composition.runtime_builders.ledger_collaborator import (
    _attach_contract_evidence_recorder,
)


pytestmark = pytest.mark.unit


def test_registry_catalog_rejects_duplicates_and_rechecks_cache_under_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    duplicate = SimpleNamespace(pipeline_name="duplicate")
    monkeypatch.setattr(catalog, "PIPELINE_CONFIGS", (duplicate, duplicate))
    with pytest.raises(RuntimeError, match="Duplicate pipeline_name"):
        catalog._build_configs_by_name()

    instance = catalog.LazyFactoryCatalog()
    expected = object()

    class _PopulatingLock:
        def __enter__(self) -> None:
            instance._cache["late"] = expected

        def __exit__(self, *_args: object) -> None:
            return None

    instance._lock = _PopulatingLock()  # type: ignore[assignment]
    assert instance["late"] is expected


def test_service_bundle_override_and_pipeline_input_envelope() -> None:
    override = ServiceBundleDependencies(
        load_pipeline_config=MagicMock(),
        yaml_config_to_domain=MagicMock(),
        compute_config_hash=MagicMock(),
        base_services_factory=MagicMock(),
    )
    assert (
        resolve_service_bundle_dependencies(
            override=override,
            load_pipeline_config_fn=MagicMock(),
            yaml_config_to_domain_fn=MagicMock(),
            compute_config_hash_fn=MagicMock(),
            base_services_factory=MagicMock(),
        )
        is override
    )

    request = object()
    built = build_pipeline_creation_inputs(
        identity=_PipelineCreationIdentity(
            pipeline_name="chembl_activity",
            pipeline_class=object,  # type: ignore[arg-type]
            provider="chembl",
            create_data_source_fn=MagicMock(),
            transformer_class=None,
            pandera_silver_schema=None,
        ),
        request=request,  # type: ignore[arg-type]
    )
    assert built.pipeline_name == "chembl_activity"
    assert built.request is request


def test_record_processor_policies_default_to_active_write_version() -> None:
    gold_schema = object()
    pipeline = SimpleNamespace(
        transformer=SimpleNamespace(
            _contract_policy=SimpleNamespace(
                active_version="v2",
                rollout=SimpleNamespace(write_versions=None, affects_hash=True),
                hash_datetime_policy="v2_datetime_utc",
            )
        ),
        gold_schema_by_version=None,
    )

    hash_policy = extract_hash_policy_by_version(
        pipeline,
        include_fields=frozenset({"id"}),
        exclude_fields=frozenset({"updated_at"}),
    )
    schema_policy = extract_gold_schema_policy_by_version(
        pipeline,
        gold_schema=gold_schema,  # type: ignore[arg-type]
    )

    assert hash_policy is not None
    assert tuple(item.version for item in hash_policy.policies) == ("v2",)
    assert schema_policy is not None
    assert schema_policy.policies[0].schema is gold_schema


def test_storage_health_audit_lookup_rejects_objects_without_dict() -> None:
    assert StorageBundleHealthMixin._get_explicit_writer_audit(object()) is None


def test_provider_creator_reports_capability_and_fails_closed_without_creator() -> None:
    config = SimpleNamespace(data_source_creator=None)
    creator = ProviderCreator()

    assert not creator.has_data_source_creator(config)  # type: ignore[arg-type]
    request = ProviderDataSourceCreationRequest(
        name="missing",
        config=config,  # type: ignore[arg-type]
        settings=SimpleNamespace(),
        pipeline_config=SimpleNamespace(),
        logger=MagicMock(),
    )
    with pytest.raises(ValueError, match="does not have a data_source_creator"):
        create_provider_data_source(request)


def test_manifest_policy_rejects_missing_family_and_strict_context_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = SimpleNamespace(
        family=None,
        default_required_persistence_profile="best_effort",
        strict_exact_replay_supported=False,
    )
    monkeypatch.setattr(
        policy, "resolve_reproducibility_family_profile", lambda **_kwargs: profile
    )
    monkeypatch.setattr(
        policy, "normalize_required_persistence_profile", lambda value: str(value)
    )
    monkeypatch.setattr(
        policy, "is_critical_reproducibility_runtime", lambda **_kwargs: False
    )
    monkeypatch.setattr(policy, "is_degraded_opt_down_eligible", lambda **_kwargs: False)
    monkeypatch.setattr(
        policy,
        "resolve_effective_required_persistence_profile",
        lambda **_kwargs: "best_effort",
    )
    with pytest.raises(RuntimeError, match="has no family"):
        policy.resolve_manifest_reproducibility_context(
            ctx=SimpleNamespace(
                required_persistence_profile="best_effort",
                required_persistence_profile_opt_down=False,
                exact_replay=False,
            ),
            inputs=SimpleNamespace(
                settings=SimpleNamespace(pipeline=None, env="test", debug=False),
                yaml_config=SimpleNamespace(),
            ),
            provider="provider",
            entity="entity",
            contract_ref="contract",
        )

    monkeypatch.setattr(
        policy,
        "assess_reproducibility_policy",
        lambda **_kwargs: SimpleNamespace(
            strict_requirement_requested=True,
            blocking_gaps={"strict_replay_execution_context_support"},
        ),
    )
    with pytest.raises(RuntimeError, match="outside the published"):
        policy.validate_required_runtime_persistence_profile(
            request=SimpleNamespace(
                source_refs=(),
                launch_context={},
                replay_capability=None,
                run_type="incremental",
            ),
            required_persistence_profile="replay_ready",
            strict_exact_replay_supported=False,
        )


def test_contract_evidence_attachment_handles_missing_root_and_plain_context(
    tmp_path: Path,
) -> None:
    runner = SimpleNamespace(attach_contract_evidence_recorder=MagicMock())
    _attach_contract_evidence_recorder(
        runner, SimpleNamespace(ledger_port=SimpleNamespace(base_path=None))
    )
    runner.attach_contract_evidence_recorder.assert_not_called()

    _attach_contract_evidence_recorder(
        runner,
        SimpleNamespace(
            ledger_port=SimpleNamespace(base_path=tmp_path / "ledger" / "events.jsonl")
        ),
    )
    recorder = runner.attach_contract_evidence_recorder.call_args.args[0]
    assert recorder.base_path == tmp_path / "ledger" / "run_manifest"
