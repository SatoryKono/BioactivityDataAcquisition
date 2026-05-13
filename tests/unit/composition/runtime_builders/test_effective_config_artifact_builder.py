"""Unit tests for effective-config artifact builder provenance helpers."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from bioetl.application.services.control_plane.effective_config_service import (
    create_effective_config_service,
)
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.runtime_builders._effective_config_artifact_builder_support import (
    build_effective_config_source_refs as _build_effective_config_source_refs,
)
from bioetl.composition.runtime_builders._effective_config_artifact_builder_support import (
    build_execution_settings_snapshot as _build_execution_settings_snapshot,
)
from bioetl.composition.runtime_builders._effective_config_artifact_builder_support import (
    build_runtime_overrides_snapshot as _build_runtime_overrides_snapshot,
)
from bioetl.composition.runtime_builders.effective_config_artifact_builder import (
    create_and_persist_composite_effective_config_artifact,
    create_and_persist_effective_config_artifact,
)
from bioetl.domain.control_plane.effective_config_environment import (
    SEMANTIC_RUNTIME_ENV_DEPENDENCIES,
)
from bioetl.composition.runtime_builders.inputs_resolver import RunnerInputs
from bioetl.domain.control_plane.config_source_hashing import (
    compute_canonical_yaml_sha256,
)
from bioetl.domain.context import PipelineRunContext
from bioetl.domain.context_cached_bronze import CachedBronzeContext
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.ports.noop import NoOpAudit, NoOpMetrics, NoOpTracing
from bioetl.domain.types import RunID
from bioetl.domain.types import RunType
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def test_build_effective_config_source_refs_persists_semantic_and_raw_source_hashes(
    tmp_path: Path,
) -> None:
    base_config = tmp_path / "configs" / "base" / "pipeline.yaml"
    base_quality = tmp_path / "configs" / "base" / "quality.yaml"
    provider_config = tmp_path / "configs" / "providers" / "chembl.yaml"
    contract_registry = tmp_path / "configs" / "base" / "contract_registry.yaml"
    entity_config = tmp_path / "configs" / "entities" / "chembl" / "activity.yaml"
    entity_quality = (
        tmp_path / "configs" / "quality" / "entities" / "chembl" / "activity.yaml"
    )
    base_config.parent.mkdir(parents=True, exist_ok=True)
    provider_config.parent.mkdir(parents=True, exist_ok=True)
    entity_config.parent.mkdir(parents=True, exist_ok=True)
    entity_quality.parent.mkdir(parents=True, exist_ok=True)
    base_config.write_text("pipeline:\n  version: 1\n", encoding="utf-8")
    base_quality.write_text("quality:\n  mode: strict\n", encoding="utf-8")
    provider_config.write_text("provider:\n  retries: 3\n", encoding="utf-8")
    contract_registry.write_text(
        "contracts:\n  chembl.activity: 1.0.0\n", encoding="utf-8"
    )
    entity_config.write_text("entity:\n  provider: chembl\n", encoding="utf-8")
    entity_quality.write_text("dq:\n  contract: chembl.activity\n", encoding="utf-8")

    refs = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=tmp_path,
    )

    assert [ref.source_path for ref in refs] == [
        "configs/base/pipeline.yaml",
        "configs/base/quality.yaml",
        "configs/providers/chembl.yaml",
        "configs/entities/chembl/activity.yaml",
        "configs/quality/entities/chembl/activity.yaml",
        "configs/base/contract_registry.yaml",
    ]
    assert [ref.source_hash for ref in refs] == [
        compute_canonical_yaml_sha256(base_config.read_bytes()),
        compute_canonical_yaml_sha256(base_quality.read_bytes()),
        compute_canonical_yaml_sha256(provider_config.read_bytes()),
        compute_canonical_yaml_sha256(entity_config.read_bytes()),
        compute_canonical_yaml_sha256(entity_quality.read_bytes()),
        compute_canonical_yaml_sha256(contract_registry.read_bytes()),
    ]


def test_build_effective_config_source_refs_include_dependency_provenance_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "configs" / "base").mkdir(parents=True, exist_ok=True)
    (tmp_path / "configs" / "entities" / "chembl").mkdir(parents=True, exist_ok=True)
    (tmp_path / "configs" / "base" / "pipeline.yaml").write_text(
        "pipeline:\n  version: 1\n",
        encoding="utf-8",
    )
    (tmp_path / "configs" / "base" / "contract_registry.yaml").write_text(
        "contracts:\n  chembl.activity: 1.0.0\n",
        encoding="utf-8",
    )
    (tmp_path / "configs" / "entities" / "chembl" / "activity.yaml").write_text(
        "entity:\n  provider: chembl\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "bioetl"\n',
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")

    refs = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=tmp_path,
    )

    assert "pyproject.toml" in [ref.source_path for ref in refs]
    assert "uv.lock" in [ref.source_path for ref in refs]


def _build_runner_inputs(
    settings: Settings,
    observability: ObservabilityBundle,
) -> RunnerInputs:
    return RunnerInputs(
        settings=settings,
        yaml_config=PipelineYamlConfig(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            business_primary_keys=["activity_id"],
        ),
        observability=observability,
        runtime_config=RuntimeConfig(run_type=RunType.INCREMENTAL),
        filter_config=None,
        cached_bronze=CachedBronzeContext.disabled(),
    )


def _build_pipeline_run_context() -> PipelineRunContext:
    return PipelineRunContext(
        pipeline_name="chembl_activity",
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
    )


def test_execution_settings_snapshot_redacts_secret_values_and_hashes_surfaces() -> (
    None
):
    settings = Settings(
        data_dir=Path("data"),
        pubmed_api_key="pubmed-secret",
        semanticscholar_api_key="semantic-secret",
    )

    snapshot = _build_execution_settings_snapshot(settings)
    rendered = json.dumps(snapshot, sort_keys=True, default=str)
    secret_redaction = snapshot["secret_redaction"]
    assert isinstance(secret_redaction, dict)
    secret_surfaces = secret_redaction["secret_surfaces"]
    assert isinstance(secret_surfaces, dict)

    assert "pubmed-secret" not in rendered
    assert "semantic-secret" not in rendered
    assert snapshot["snapshot_hash"].startswith("sha256:")
    assert "settings.pubmed_api_key" in snapshot["materialized_surfaces"]
    pubmed_surface = secret_surfaces["settings.pubmed_api_key"]
    semantic_scholar_surface = secret_surfaces["settings.semanticscholar_api_key"]
    assert isinstance(pubmed_surface, dict)
    assert isinstance(semantic_scholar_surface, dict)
    assert pubmed_surface["present"] is True
    assert semantic_scholar_surface["present"] is True
    assert str(pubmed_surface["value_hash"]).startswith("sha256:")
    assert str(semantic_scholar_surface["value_hash"]).startswith("sha256:")
    assert snapshot["non_materialized_semantic_env_dependencies"] == list(
        SEMANTIC_RUNTIME_ENV_DEPENDENCIES
    )


def test_effective_config_artifact_publishes_semantic_runtime_env_dependencies() -> (
    None
):
    service = create_effective_config_service()

    artifact = service.create_effective_config_artifact(
        pipeline_name="chembl_activity",
        pipeline_kind="standard",
        resolved_config={"pipeline": {"name": "chembl_activity"}},
        runtime_overrides={
            "cli": {"limit": 25},
            "runtime": {"exact_replay": True},
        },
        source_refs=[],
    )

    assert artifact.execution_environment.materialized_env_keys == ()
    assert artifact.execution_environment.ambient_environment_policy == (
        "excluded_unless_explicitly_materialized"
    )
    assert (
        artifact.execution_environment.non_materialized_semantic_env_dependencies
        == (SEMANTIC_RUNTIME_ENV_DEPENDENCIES)
    )


def test_runtime_overrides_snapshot_materializes_execution_environment_provenance() -> (
    None
):
    settings = Settings(env="prod", data_dir=Path("data"), debug=True)

    snapshot = _build_runtime_overrides_snapshot(
        _build_pipeline_run_context(),
        settings,
    )

    env_snapshot = snapshot["env"]["execution_environment"]
    assert env_snapshot["schema_version"] == "execution-environment-v1"
    assert env_snapshot["settings_env"] == "prod"
    assert env_snapshot["debug"] is True
    assert env_snapshot["data_root_mode"] == "explicit"
    assert "settings_snapshot_hash" in env_snapshot
    assert env_snapshot["settings_snapshot_hash"].startswith("sha256:")


def test_runtime_overrides_snapshot_materializes_silver_filter_compatibility() -> (
    None
):
    """Silver compatibility mode must be part of effective-config identity."""
    settings = Settings(env="prod", data_dir=Path("data"), debug=True)

    snapshot = _build_runtime_overrides_snapshot(
        _build_pipeline_run_context(),
        settings,
    )

    assert snapshot["cli"]["silver_filter_compatibility_mode"] == (
        "structural_only_auto_promote"
    )
    assert snapshot["runtime"]["silver_filter_compatibility_mode"] == (
        "structural_only_auto_promote"
    )
    assert snapshot["runtime"]["silver_filter_compatibility"] == {
        "schema_version": "silver-filter-compatibility-v1",
        "mode": "structural_only_auto_promote",
        "source": "default",
    }
    assert snapshot["runtime"]["settings_snapshot"]["silver_filter_compatibility"][
        "mode"
    ] == "structural_only_auto_promote"


def test_build_effective_config_source_refs_is_stable_across_equivalent_calls(
    tmp_path: Path,
) -> None:
    base_config = tmp_path / "configs" / "base" / "pipeline.yaml"
    contract_registry = tmp_path / "configs" / "base" / "contract_registry.yaml"
    entity_config = tmp_path / "configs" / "entities" / "chembl" / "activity.yaml"
    base_config.parent.mkdir(parents=True, exist_ok=True)
    entity_config.parent.mkdir(parents=True, exist_ok=True)
    base_config.write_text("pipeline:\n  version: 1\n", encoding="utf-8")
    contract_registry.write_text(
        "contracts:\n  chembl.activity: 1.0.0\n", encoding="utf-8"
    )
    entity_config.write_text("entity:\n  provider: chembl\n", encoding="utf-8")

    refs_first = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=tmp_path,
    )
    refs_second = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=tmp_path,
    )

    assert refs_first == refs_second


def test_effective_config_source_refs_ignore_yaml_formatting_for_semantic_identity(
    tmp_path: Path,
) -> None:
    left_root = tmp_path / "left"
    right_root = tmp_path / "right"
    for root in (left_root, right_root):
        (root / "configs" / "base").mkdir(parents=True, exist_ok=True)
        (root / "configs" / "entities" / "chembl").mkdir(parents=True, exist_ok=True)

    (left_root / "configs" / "base" / "pipeline.yaml").write_text(
        "pipeline:\n  version: 1\n  name: chembl_activity\n",
        encoding="utf-8",
    )
    (right_root / "configs" / "base" / "pipeline.yaml").write_text(
        "# same semantics, different bytes\n"
        "pipeline: {name: chembl_activity, version: 1}\n",
        encoding="utf-8",
    )
    for root in (left_root, right_root):
        (root / "configs" / "entities" / "chembl" / "activity.yaml").write_text(
            "entity:\n  provider: chembl\n",
            encoding="utf-8",
        )
        (root / "configs" / "base" / "contract_registry.yaml").write_text(
            "contracts:\n  chembl.activity: 1.0.0\n",
            encoding="utf-8",
        )

    refs_left = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=left_root,
    )
    refs_right = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=right_root,
    )

    assert [ref.source_hash for ref in refs_left] == [
        ref.source_hash for ref in refs_right
    ]
    assert refs_left[0].raw_source_hash != refs_right[0].raw_source_hash

    service = create_effective_config_service()
    artifact_left = service.create_effective_config_artifact(
        pipeline_name="chembl_activity",
        pipeline_kind="standard",
        resolved_config={"pipeline": {"name": "chembl_activity"}},
        runtime_overrides={},
        source_refs=refs_left,
    )
    artifact_right = service.create_effective_config_artifact(
        pipeline_name="chembl_activity",
        pipeline_kind="standard",
        resolved_config={"pipeline": {"name": "chembl_activity"}},
        runtime_overrides={},
        source_refs=refs_right,
    )

    assert artifact_left.source_fingerprint == artifact_right.source_fingerprint
    assert artifact_left.artifact_id == artifact_right.artifact_id


def test_effective_config_source_fingerprint_changes_when_provider_config_changes(
    tmp_path: Path,
) -> None:
    left_root = tmp_path / "left"
    right_root = tmp_path / "right"
    for root in (left_root, right_root):
        (root / "configs" / "base").mkdir(parents=True, exist_ok=True)
        (root / "configs" / "providers").mkdir(parents=True, exist_ok=True)
        (root / "configs" / "entities" / "chembl").mkdir(parents=True, exist_ok=True)
        (root / "configs" / "base" / "pipeline.yaml").write_text(
            "pipeline:\n  version: 1\n",
            encoding="utf-8",
        )
        (root / "configs" / "entities" / "chembl" / "activity.yaml").write_text(
            "entity:\n  provider: chembl\n",
            encoding="utf-8",
        )
        (root / "configs" / "base" / "contract_registry.yaml").write_text(
            "contracts:\n  chembl.activity: 1.0.0\n",
            encoding="utf-8",
        )

    (left_root / "configs" / "providers" / "chembl.yaml").write_text(
        "provider:\n  retries: 2\n",
        encoding="utf-8",
    )
    (right_root / "configs" / "providers" / "chembl.yaml").write_text(
        "provider:\n  retries: 5\n",
        encoding="utf-8",
    )

    refs_left = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=left_root,
    )
    refs_right = _build_effective_config_source_refs(
        provider="chembl",
        entity="activity",
        repo_root=right_root,
    )

    service = create_effective_config_service()
    artifact_left = service.create_effective_config_artifact(
        pipeline_name="chembl_activity",
        pipeline_kind="standard",
        resolved_config={"pipeline": {"name": "chembl_activity"}},
        runtime_overrides={},
        source_refs=refs_left,
    )
    artifact_right = service.create_effective_config_artifact(
        pipeline_name="chembl_activity",
        pipeline_kind="standard",
        resolved_config={"pipeline": {"name": "chembl_activity"}},
        runtime_overrides={},
        source_refs=refs_right,
    )

    assert artifact_left.source_fingerprint != artifact_right.source_fingerprint


def test_create_and_persist_effective_config_artifact_forwards_required_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_payload(
        *,
        pipeline_name: str,
        pipeline_kind: str,
        resolved_config: object,
        runtime_overrides: dict[str, object],
        provider: str,
        entity: str,
        required_persistence_profile: str,
        resolution_policy: object,
        normalization_profile_ref: str | None,
        normalization_profile_version: str | None,
        normalization_profile_hash: str | None,
        settings: Settings,
        logger: object,
        run_id: RunID,
    ) -> tuple[str, str, str, str]:
        captured.update(
            pipeline_name=pipeline_name,
            pipeline_kind=pipeline_kind,
            resolved_config=resolved_config,
            runtime_overrides=runtime_overrides,
            provider=provider,
            entity=entity,
            required_persistence_profile=required_persistence_profile,
            resolution_policy=resolution_policy,
            normalization_profile_ref=normalization_profile_ref,
            normalization_profile_version=normalization_profile_version,
            normalization_profile_hash=normalization_profile_hash,
            settings=settings,
            logger=logger,
            run_id=run_id,
        )
        return ("artifact-1", "resolved-hash", "effective-hash", "dq-hash")

    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.effective_config_artifact_builder._create_and_persist_effective_config_artifact_payload",
        _fake_payload,
    )

    settings = Settings(data_dir=Path("data"))
    observability = ObservabilityBundle.create(
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        tracer=NoOpTracing(),
        audit=NoOpAudit(),
    )
    inputs: RunnerInputs = _build_runner_inputs(settings, observability)
    ctx: PipelineRunContext = _build_pipeline_run_context()
    result = create_and_persist_effective_config_artifact(
        ctx=ctx,
        inputs=inputs,
        provider="chembl",
        entity="activity",
    )

    assert result == ("artifact-1", "resolved-hash", "effective-hash", "dq-hash")
    assert captured["required_persistence_profile"] == "degraded_observable"
    assert captured["resolution_policy"].strict_validation is True
    assert captured["normalization_profile_ref"] == "chembl.activity"
    assert captured["normalization_profile_version"] == "1.0.0"
    assert isinstance(captured["normalization_profile_hash"], str)
    settings_snapshot = captured["runtime_overrides"]["runtime"]["settings_snapshot"]
    env_snapshot = captured["runtime_overrides"]["env"]["execution_environment"]
    assert settings_snapshot["schema_version"] == "execution-settings-v1"
    assert settings_snapshot["settings"]["data_dir"] == "data"
    assert env_snapshot["schema_version"] == "execution-environment-v1"
    assert env_snapshot["dependency_lock_present"] in {True, False}
    assert (
        "settings.pipeline.control_plane.required_persistence_profile"
        in settings_snapshot["materialized_surfaces"]
    )


def test_create_and_persist_effective_config_artifact_uses_effective_replay_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_payload(
        *,
        pipeline_name: str,
        pipeline_kind: str,
        resolved_config: object,
        runtime_overrides: dict[str, object],
        provider: str,
        entity: str,
        required_persistence_profile: str,
        resolution_policy: object,
        normalization_profile_ref: str | None,
        normalization_profile_version: str | None,
        normalization_profile_hash: str | None,
        settings: Settings,
        logger: object,
        run_id: RunID,
    ) -> tuple[str, str, str, str]:
        captured.update(
            pipeline_name=pipeline_name,
            pipeline_kind=pipeline_kind,
            resolved_config=resolved_config,
            runtime_overrides=runtime_overrides,
            provider=provider,
            entity=entity,
            required_persistence_profile=required_persistence_profile,
            resolution_policy=resolution_policy,
            normalization_profile_ref=normalization_profile_ref,
            normalization_profile_version=normalization_profile_version,
            normalization_profile_hash=normalization_profile_hash,
            settings=settings,
            logger=logger,
            run_id=run_id,
        )
        return ("artifact-1", "resolved-hash", "effective-hash", "dq-hash")

    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.effective_config_artifact_builder._create_and_persist_effective_config_artifact_payload",
        _fake_payload,
    )

    settings = Settings(
        data_dir=Path("data"),
        pipeline={
            "control_plane": {
                "run_manifest_enabled": True,
                "run_ledger_enabled": True,
                "required_persistence_profile": "degraded_observable",
            }
        },
    )
    observability = ObservabilityBundle.create(
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        tracer=NoOpTracing(),
        audit=NoOpAudit(),
    )
    inputs: RunnerInputs = _build_runner_inputs(settings, observability)
    ctx = PipelineRunContext(
        pipeline_name="chembl_activity",
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        exact_replay=True,
    )

    create_and_persist_effective_config_artifact(
        ctx=ctx,
        inputs=inputs,
        provider="chembl",
        entity="activity",
    )

    assert captured["required_persistence_profile"] == "replay_ready"
    assert captured["resolution_policy"].strict_validation is True
    assert captured["normalization_profile_ref"] == "chembl.activity"
    assert captured["runtime_overrides"]["cli"]["exact_replay"] is True


def test_create_and_persist_effective_config_artifact_promotes_prod_family_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_payload(
        *,
        pipeline_name: str,
        pipeline_kind: str,
        resolved_config: object,
        runtime_overrides: dict[str, object],
        provider: str,
        entity: str,
        required_persistence_profile: str,
        resolution_policy: object,
        normalization_profile_ref: str | None,
        normalization_profile_version: str | None,
        normalization_profile_hash: str | None,
        settings: Settings,
        logger: object,
        run_id: RunID,
    ) -> tuple[str, str, str, str]:
        captured["required_persistence_profile"] = required_persistence_profile
        captured["resolution_policy"] = resolution_policy
        captured["normalization_profile_ref"] = normalization_profile_ref
        return ("artifact-1", "resolved-hash", "effective-hash", "dq-hash")

    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.effective_config_artifact_builder._create_and_persist_effective_config_artifact_payload",
        _fake_payload,
    )

    observability = ObservabilityBundle.create(
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        tracer=NoOpTracing(),
        audit=NoOpAudit(),
    )
    inputs = _build_runner_inputs(
        Settings(env="prod", data_dir=Path("data")), observability
    )

    create_and_persist_effective_config_artifact(
        ctx=_build_pipeline_run_context(),
        inputs=inputs,
        provider="chembl",
        entity="activity",
    )

    assert captured["required_persistence_profile"] == "replay_ready"
    assert captured["resolution_policy"].strict_validation is True
    assert captured["normalization_profile_ref"] == "chembl.activity"


def test_create_and_persist_effective_config_artifact_forwards_runtime_strictness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_payload(
        *,
        pipeline_name: str,
        pipeline_kind: str,
        resolved_config: object,
        runtime_overrides: dict[str, object],
        provider: str,
        entity: str,
        required_persistence_profile: str,
        resolution_policy: object,
        normalization_profile_ref: str | None,
        normalization_profile_version: str | None,
        normalization_profile_hash: str | None,
        settings: Settings,
        logger: object,
        run_id: RunID,
    ) -> tuple[str, str, str, str]:
        captured["resolution_policy"] = resolution_policy
        captured["normalization_profile_ref"] = normalization_profile_ref
        return ("artifact-1", "resolved-hash", "effective-hash", "dq-hash")

    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.effective_config_artifact_builder._create_and_persist_effective_config_artifact_payload",
        _fake_payload,
    )

    observability = ObservabilityBundle.create(
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        tracer=NoOpTracing(),
        audit=NoOpAudit(),
    )
    inputs = RunnerInputs(
        settings=Settings(data_dir=Path("data")),
        yaml_config=PipelineYamlConfig(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            business_primary_keys=["activity_id"],
        ),
        observability=observability,
        runtime_config=RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            strict_gold_validation=False,
        ),
        filter_config=None,
        cached_bronze=CachedBronzeContext.disabled(),
    )

    create_and_persist_effective_config_artifact(
        ctx=_build_pipeline_run_context(),
        inputs=inputs,
        provider="chembl",
        entity="activity",
    )

    assert captured["resolution_policy"].strict_validation is False
    assert captured["normalization_profile_ref"] == "chembl.activity"


def test_create_and_persist_composite_effective_config_artifact_forwards_required_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_payload(
        *,
        pipeline_name: str,
        pipeline_kind: str,
        resolved_config: object,
        runtime_overrides: dict[str, object],
        provider: str,
        entity: str,
        required_persistence_profile: str,
        resolution_policy: object,
        normalization_profile_ref: str | None,
        normalization_profile_version: str | None,
        normalization_profile_hash: str | None,
        settings: Settings,
        logger: object,
        run_id: RunID,
    ) -> tuple[str, str, str, str]:
        captured.update(
            pipeline_name=pipeline_name,
            pipeline_kind=pipeline_kind,
            resolved_config=resolved_config,
            runtime_overrides=runtime_overrides,
            provider=provider,
            entity=entity,
            required_persistence_profile=required_persistence_profile,
            resolution_policy=resolution_policy,
            normalization_profile_ref=normalization_profile_ref,
            normalization_profile_version=normalization_profile_version,
            normalization_profile_hash=normalization_profile_hash,
            settings=settings,
            logger=logger,
            run_id=run_id,
        )
        return ("artifact-2", "resolved-hash", "effective-hash", "dq-hash")

    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.effective_config_artifact_builder._create_and_persist_effective_config_artifact_payload",
        _fake_payload,
    )

    result = create_and_persist_composite_effective_config_artifact(
        pipeline_name="composite_publication",
        config=PipelineYamlConfig(
            pipeline_name="composite_publication",
            provider="composite",
            entity_type="publication",
            business_primary_keys=["publication_id"],
        ),
        runtime_config=RuntimeConfig(run_type=RunType.INCREMENTAL),
        required_persistence_profile="forensic_grade",
        settings=Settings(data_dir=Path("data")),
        logger=NoOpLogger(),
        run_id=RunID(uuid4()),
    )

    assert result == ("artifact-2", "resolved-hash", "effective-hash", "dq-hash")
    assert captured["required_persistence_profile"] == "forensic_grade"
    assert captured["resolution_policy"].strict_validation is True
    assert captured["normalization_profile_ref"] is None
    runtime_payload = captured["runtime_overrides"]["runtime"]
    assert (
        runtime_payload["settings_snapshot"]["control_plane"][
            "required_persistence_profile"
        ]
        == "degraded_observable"
    )
