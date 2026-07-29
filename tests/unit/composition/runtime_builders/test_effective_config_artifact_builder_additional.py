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
"""Additional behavioral tests for effective-config artifact runtime builders."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.composition.runtime_builders import (
    effective_config_artifact_builder as effective_config_builder,
)
from bioetl.composition.runtime_builders.effective_config_artifact_builder import (
    create_and_persist_composite_effective_config_artifact,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.config._base import PipelineSettings, Settings
from bioetl.infrastructure.config._pipeline_settings import ControlPlaneSettings
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite


pytestmark = pytest.mark.unit


@pytest.mark.unit
def test_effective_config_payload_rejects_non_object_json_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = SimpleNamespace(
        artifact_id="artifact-1",
        resolved_config_hash="resolved-hash",
        effective_config_hash="effective-hash",
        source_fingerprint="source-hash",
        dq_contract_compatibility_hash="dq-hash",
    )

    class _FakeService:
        def create_effective_config_artifact(self, **_kwargs: object) -> object:
            return artifact

        def serialize_artifact(self, _artifact: object) -> str:
            return '["not", "an", "object"]'

    monkeypatch.setattr(
        effective_config_builder,
        "create_effective_config_service",
        lambda: _FakeService(),
    )
    monkeypatch.setattr(
        effective_config_builder,
        "build_effective_config_source_refs",
        lambda provider, entity: [],
    )

    with pytest.raises(
        ValueError,
        match="Effective-config artifact payload must be a JSON object",
    ):
        effective_config_builder._create_and_persist_effective_config_artifact_payload(
            pipeline_name="chembl_activity",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "chembl_activity"}},
            runtime_overrides={},
            provider="chembl",
            entity="activity",
            required_persistence_profile="replay_ready",
            resolution_policy=None,
            normalization_profile=(None, None, None),
            settings=Settings(data_dir=Path("data")),
            logger=NoOpLogger(),
            run_id=RunID(
                deterministic_run_uuid_from_callsite(
                    "test_effective_config_payload_rejects_non_object_json_payload"
                )
            ),
        )


@pytest.mark.unit
def test_effective_config_payload_logs_successful_persist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = SimpleNamespace(
        artifact_id="artifact-2",
        resolved_config_hash="resolved-hash",
        effective_config_hash="effective-hash",
        source_fingerprint="source-hash",
        dq_contract_compatibility_hash="dq-hash",
    )
    logger = Mock()
    saved: dict[str, object] = {}

    class _FakeService:
        def create_effective_config_artifact(self, **_kwargs: object) -> object:
            return artifact

        def serialize_artifact(self, _artifact: object) -> str:
            return '{"artifact_id": "artifact-2"}'

    class _FakeStore:
        def save(
            self, *, artifact_id: str, run_id: RunID, payload: dict[str, object]
        ) -> None:
            saved.update(artifact_id=artifact_id, run_id=run_id, payload=payload)

    monkeypatch.setattr(
        effective_config_builder,
        "create_effective_config_service",
        lambda: _FakeService(),
    )
    monkeypatch.setattr(
        effective_config_builder,
        "create_effective_config_artifact_store",
        lambda settings: _FakeStore(),
    )
    monkeypatch.setattr(
        effective_config_builder,
        "build_effective_config_source_refs",
        lambda provider, entity: [],
    )

    run_id = RunID(
        deterministic_run_uuid_from_callsite(
            "test_effective_config_payload_logs_successful_persist"
        )
    )
    result = (
        effective_config_builder._create_and_persist_effective_config_artifact_payload(
            pipeline_name="chembl_activity",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "chembl_activity"}},
            runtime_overrides={"start_offset": 10},
            provider="chembl",
            entity="activity",
            required_persistence_profile="replay_ready",
            resolution_policy=None,
            normalization_profile=(None, None, None),
            settings=Settings(data_dir=Path("data")),
            logger=logger,
            run_id=run_id,
        )
    )

    assert result == (
        "artifact-2",
        "resolved-hash",
        "effective-hash",
        "source-hash",
        "dq-hash",
    )
    assert saved == {
        "artifact_id": "artifact-2",
        "run_id": run_id,
        "payload": {"artifact_id": "artifact-2"},
    }
    logger.info.assert_called_once_with(
        "effective_config_artifact_persisted",
        artifact_id="artifact-2",
        pipeline_name="chembl_activity",
        resolved_config_hash="resolved-hash",
        effective_config_hash="effective-hash",
        dq_contract_compatibility_hash="dq-hash",
    )


@pytest.mark.unit
def test_composite_effective_config_artifact_uses_strict_validation_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_payload(**kwargs: object) -> tuple[str, str, str, str, str]:
        captured.update(kwargs)
        return (
            "artifact-3",
            "resolved-hash",
            "effective-hash",
            "source-hash",
            "dq-hash",
        )

    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.effective_config_artifact_builder._create_and_persist_effective_config_artifact_payload",
        _fake_payload,
    )

    runtime_config = SimpleNamespace(strict_validation=False)
    result = create_and_persist_composite_effective_config_artifact(
        pipeline_name="composite_publication",
        config=PipelineYamlConfig(
            pipeline_name="composite_publication",
            provider="composite",
            entity_type="publication",
            business_primary_keys=["publication_id"],
        ),
        runtime_config=runtime_config,
        required_persistence_profile="replay_ready",
        normalization_profile_ref=None,
        normalization_profile_version=None,
        normalization_profile_hash=None,
        settings=Settings(
            data_dir=Path("data"),
            pipeline=PipelineSettings(
                control_plane=ControlPlaneSettings(
                    required_persistence_profile="replay_ready"
                )
            ),
        ),
        logger=NoOpLogger(),
        run_id=RunID(
            deterministic_run_uuid_from_callsite(
                "test_composite_effective_config_artifact_uses_strict_validation_fallback"
            )
        ),
    )

    assert result == (
        "artifact-3",
        "resolved-hash",
        "effective-hash",
        "source-hash",
        "dq-hash",
    )
    assert captured["pipeline_kind"] == "composite"
    assert captured["resolution_policy"].strict_validation is False
    assert captured["required_persistence_profile"] == "replay_ready"
