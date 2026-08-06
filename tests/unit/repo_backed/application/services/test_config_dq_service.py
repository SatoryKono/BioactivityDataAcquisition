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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for ConfigDQService and helper parsers."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane.effective_config_artifact import (
    ConfigResolutionPolicy,
    ConfigSourceRef,
    DQPolicySnapshot,
    EffectiveConfigArtifact,
    EffectiveExecutionConfig,
    ResolvedConfigSnapshot,
    RuntimeOverrideSnapshot,
)
from bioetl.domain.types.dq_contracts import DQDisposition, DQPolicyRef

pytestmark = pytest.mark.repo_backed


def _load_config_dq_service_module() -> object:
    module_path = (
        Path(__file__).resolve().parents[5]
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "quality"
        / "config_dq_service.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_test_config_dq_service_module",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


service_mod = _load_config_dq_service_module()
ConfigDQService = service_mod.ConfigDQService


def _sample_artifact_dict(
    *, effective_hash: str = "effective-hash"
) -> dict[str, object]:
    return {
        "artifact_id": "artifact-1",
        "pipeline_name": "crossref_publication",
        "pipeline_kind": "standard",
        "source_refs": [
            {
                "source_type": "file",
                "source_path": "configs/base/pipeline.yaml",
                "source_hash": "hash-1",
                "priority": 1,
            }
        ],
        "resolution_policy": {
            "merge_strategy": "hierarchical",
            "default_materialization": True,
            "strict_validation": True,
            "allow_runtime_overrides": True,
        },
        "resolved_config": {
            "config_type": "standard",
            "config_data": {"provider": "crossref"},
            "config_hash": "resolved-hash",
            "timestamp": "2026-03-28T16:00:00",
        },
        "runtime_overrides": {
            "cli_overrides": {"limit": 10},
            "env_overrides": {"BIOETL_ENV": "test"},
            "runtime_adjustments": {"retry": 2},
            "override_hash": "override-hash",
        },
        "effective_execution_config": {
            "config_data": {"provider": "crossref", "limit": 10},
            "effective_hash": effective_hash,
            "timestamp": "2026-03-28T16:00:01",
        },
        "resolved_config_hash": "resolved-hash",
        "effective_config_hash": effective_hash,
        "source_fingerprint": "fingerprint",
        "schema_version": "1.0",
        "created_at": "2026-03-28T16:00:02",
        "contract_refs": ["dq.crossref"],
        "dq_policy_refs": [
            {
                "contract_ref": "dq.crossref",
                "contract_version": "1.0.0",
                "rule_bundle_version": "2026.03",
                "policy_hash": "policy-hash",
            }
        ],
        "dq_rule_bundle_versions": {"dq.crossref": "2026.03"},
        "dq_contract_compatibility_hash": "compat-hash",
        "dq_policy_snapshots": [
            {
                "contract_ref": "dq.crossref",
                "contract_version": "1.0.0",
                "rule_bundle_version": "2026.03",
                "policy_hash": "policy-hash",
                "default_disposition": "warn",
                "disposition_overrides": {"rule-1": "fail"},
                "strictness_mode": "strict",
            }
        ],
    }


class _StubEffectiveConfigService:
    """Test double for EffectiveConfigService with call capture."""

    def __init__(self, artifact_dict: dict[str, object]) -> None:
        self.artifact_dict = artifact_dict
        self.create_calls: list[dict[str, object]] = []
        self.compatibility_result = True

    def create_effective_config_artifact(
        self, **kwargs: object
    ) -> EffectiveConfigArtifact:
        self.create_calls.append(kwargs)
        return EffectiveConfigArtifact(
            artifact_id="artifact-1",
            pipeline_name="crossref_publication",
            pipeline_kind="standard",
            source_refs=[
                ConfigSourceRef(
                    source_type="file",
                    source_path="configs/base/pipeline.yaml",
                    source_hash="hash-1",
                    priority=1,
                )
            ],
            resolution_policy=ConfigResolutionPolicy(),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard",
                config_data={"provider": "crossref"},
                config_hash="resolved-hash",
                timestamp=datetime.fromisoformat("2026-03-28T16:00:00"),
            ),
            runtime_overrides=RuntimeOverrideSnapshot(
                cli_overrides={},
                env_overrides={},
                runtime_adjustments={},
                override_hash="override-hash",
            ),
            effective_execution_config=EffectiveExecutionConfig(
                config_data={"provider": "crossref"},
                effective_hash="effective-hash",
                timestamp=datetime.fromisoformat("2026-03-28T16:00:01"),
            ),
            resolved_config_hash="resolved-hash",
            effective_config_hash="effective-hash",
            source_fingerprint="fingerprint",
            dq_policy_refs=[
                DQPolicyRef(
                    contract_ref="dq.crossref",
                    contract_version="1.0.0",
                    rule_bundle_version="2026.03",
                    policy_hash="policy-hash",
                )
            ],
            dq_policy_snapshots=[
                DQPolicySnapshot(
                    contract_ref="dq.crossref",
                    contract_version="1.0.0",
                    rule_bundle_version="2026.03",
                    policy_hash="policy-hash",
                    default_disposition=DQDisposition.WARN,
                    disposition_overrides={"rule-1": DQDisposition.FAIL},
                    strictness_mode="strict",
                )
            ],
        )

    def serialize_artifact(self, artifact: object) -> str:
        return json.dumps(self.artifact_dict)

    def check_dq_compatibility(self, artifact1: object, artifact2: object) -> bool:
        assert hasattr(artifact1, "effective_config_hash")
        assert hasattr(artifact2, "effective_config_hash")
        return self.compatibility_result


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (DQDisposition.WARN, DQDisposition.WARN),
        ("fail", DQDisposition.FAIL),
    ],
)
def test_parse_disposition_accepts_enum_and_string(
    value: object,
    expected: DQDisposition,
) -> None:
    assert service_mod._parse_disposition(value) is expected


def test_parse_disposition_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="not a valid DQDisposition"):
        service_mod._parse_disposition("bad")


def test_parse_strictness_helpers_validate_allowed_values() -> None:
    assert service_mod._parse_strictness_mode("strict") == "strict"
    assert service_mod._parse_snapshot_strictness_mode("standard") == "standard"

    with pytest.raises(ValueError, match="Invalid DQ strictness mode"):
        service_mod._parse_strictness_mode("bad")
    with pytest.raises(ValueError, match="Invalid DQ snapshot strictness mode"):
        service_mod._parse_snapshot_strictness_mode("bad")


def test_parse_disposition_overrides_supports_mappings_and_pairs() -> None:
    assert service_mod._parse_disposition_overrides({"rule-1": "fail"}) == {
        "rule-1": DQDisposition.FAIL
    }
    assert service_mod._parse_disposition_overrides([("rule-2", "warn")]) == {
        "rule-2": DQDisposition.WARN
    }
    assert service_mod._disposition_overrides_to_strings({"rule-1": "fail"}) == {
        "rule-1": "fail"
    }

    with pytest.raises(ValueError, match="key/value pairs"):
        service_mod._parse_disposition_overrides([("rule-1",)])
    with pytest.raises(ValueError, match="mapping or sequence of pairs"):
        service_mod._parse_disposition_overrides("bad")


def test_dict_to_artifact_reconstructs_domain_object() -> None:
    artifact = service_mod._dict_to_artifact(_sample_artifact_dict())

    assert artifact.pipeline_name == "crossref_publication"
    assert artifact.source_refs[0].source_path == "configs/base/pipeline.yaml"
    assert artifact.dq_policy_refs[0].contract_ref == "dq.crossref"
    assert artifact.dq_policy_snapshots[0].default_disposition is DQDisposition.WARN
    assert artifact.dq_policy_snapshots[0].disposition_overrides == {
        "rule-1": DQDisposition.FAIL
    }


def test_get_dq_config_returns_normalized_dict() -> None:
    logger = MagicMock()
    dq_config = DQConfig(
        contract_ref="dq.crossref",
        contract_version="1.0.0",
        rule_bundle_version="2026.03",
        default_disposition_policy=DQDisposition.WARN,
        disposition_overrides={"rule-1": DQDisposition.FAIL},
        strictness_mode="strict",
    )
    service = ConfigDQService(
        logger=logger,
        _pipeline_yaml_getter=lambda pipeline_name: {"provider": "crossref"},
        _dq_config_loader=lambda pipeline_name: dq_config,
        _effective_config_service=_StubEffectiveConfigService(_sample_artifact_dict()),
    )

    result = service.get_dq_config("crossref_publication")

    assert result["contract_ref"] == "dq.crossref"
    assert result["default_disposition_policy"] == "warn"
    assert result["disposition_overrides"] == {"rule-1": "fail"}
    logger.debug.assert_called_once()
    logger.info.assert_called_once()


def test_validate_dq_config_handles_success_and_validation_failure() -> None:
    logger = MagicMock()
    service = ConfigDQService(
        logger=logger,
        _pipeline_yaml_getter=lambda pipeline_name: {"provider": "crossref"},
        _dq_config_loader=lambda pipeline_name: DQConfig(),
        _effective_config_service=_StubEffectiveConfigService(_sample_artifact_dict()),
    )

    valid = service.validate_dq_config(
        "crossref_publication",
        {
            "contract_ref": "dq.crossref",
            "contract_version": "1.0.0",
            "rule_bundle_version": "2026.03",
            "default_disposition_policy": "warn",
            "disposition_overrides": [("rule-1", "fail")],
            "strictness_mode": "moderate",
        },
    )
    invalid = service.validate_dq_config(
        "crossref_publication",
        {"default_disposition_policy": "warn", "strictness_mode": "invalid"},
    )

    assert valid is True
    assert invalid is False
    logger.error.assert_called_once()


def test_get_effective_config_artifact_handles_present_and_missing_dq_config() -> None:
    logger = MagicMock()
    artifact_dict = _sample_artifact_dict()
    effective_service = _StubEffectiveConfigService(artifact_dict)
    dq_config = DQConfig(contract_ref="dq.crossref")
    service = ConfigDQService(
        logger=logger,
        _pipeline_yaml_getter=lambda pipeline_name: {
            "provider": "crossref",
            "entity": "publication",
        },
        _dq_config_loader=lambda pipeline_name: dq_config,
        _effective_config_service=effective_service,
    )

    result = service.get_effective_config_artifact(
        "crossref_publication",
        runtime_overrides={"cli": {"limit": 10}},
    )

    assert result == artifact_dict
    first_call = effective_service.create_calls[0]
    assert first_call["pipeline_name"] == "crossref_publication"
    assert first_call["pipeline_kind"] == "standard"
    assert first_call["dq_config"] is dq_config
    assert first_call["resolution_policy"].strict_validation is False
    assert [src.source_path for src in first_call["source_refs"]] == [
        "configs/base/pipeline.yaml",
        "configs/providers/crossref.yaml",
        "configs/entities/crossref/publication.yaml",
    ]

    def _missing_dq_config(_pipeline_name: str) -> dict[str, object]:
        raise FileNotFoundError()

    missing_service = ConfigDQService(
        logger=logger,
        _pipeline_yaml_getter=lambda pipeline_name: {"provider": "crossref"},
        _dq_config_loader=_missing_dq_config,
        _effective_config_service=effective_service,
    )
    missing_service.get_effective_config_artifact("crossref_publication")
    second_call = effective_service.create_calls[1]
    assert second_call["dq_config"] is None
    assert second_call["resolution_policy"].strict_validation is False


def test_get_effective_config_artifact_publishes_explicit_dq_strict_validation() -> (
    None
):
    logger = MagicMock()
    effective_service = _StubEffectiveConfigService(_sample_artifact_dict())
    dq_config = DQConfig(contract_ref="dq.crossref", strict_validation=True)
    service = ConfigDQService(
        logger=logger,
        _pipeline_yaml_getter=lambda pipeline_name: {"provider": "crossref"},
        _dq_config_loader=lambda pipeline_name: dq_config,
        _effective_config_service=effective_service,
    )

    service.get_effective_config_artifact("crossref_publication")

    call = effective_service.create_calls[0]
    assert call["resolution_policy"].strict_validation is True


def test_get_effective_config_artifact_uses_injected_source_ref_provider() -> None:
    logger = MagicMock()
    provider_calls: list[dict[str, str]] = []

    def _source_ref_provider(*, provider: str, entity: str) -> list[ConfigSourceRef]:
        provider_calls.append({"provider": provider, "entity": entity})
        return [
            ConfigSourceRef(
                source_type="file",
                source_path="configs/base/pipeline.yaml",
                source_hash="semantic-base",
                raw_source_hash="raw-base",
                source_hash_strategy="canonical_yaml",
                priority=1,
            ),
            ConfigSourceRef(
                source_type="file",
                source_path="configs/entities/crossref/publication.yaml",
                source_hash="semantic-entity",
                raw_source_hash="raw-entity",
                source_hash_strategy="canonical_yaml",
                priority=2,
            ),
        ]

    effective_service = _StubEffectiveConfigService(_sample_artifact_dict())
    service = ConfigDQService(
        logger=logger,
        _pipeline_yaml_getter=lambda pipeline_name: {
            "provider": "crossref",
            "entity": "publication",
        },
        _dq_config_loader=lambda pipeline_name: DQConfig(contract_ref="dq.crossref"),
        _effective_config_service=effective_service,
        _config_source_ref_provider=_source_ref_provider,
    )

    service.get_effective_config_artifact("crossref_publication")

    source_refs = effective_service.create_calls[0]["source_refs"]
    assert provider_calls == [{"provider": "crossref", "entity": "publication"}]
    assert [src.source_hash for src in source_refs] == [
        "semantic-base",
        "semantic-entity",
    ]
    assert [src.raw_source_hash for src in source_refs] == [
        "raw-base",
        "raw-entity",
    ]
    assert [src.source_hash_strategy for src in source_refs] == [
        "canonical_yaml",
        "canonical_yaml",
    ]


def test_get_effective_config_artifact_rejects_non_mapping_payload() -> None:
    logger = MagicMock()

    class _BadEffectiveService(_StubEffectiveConfigService):
        def serialize_artifact(self, artifact: object) -> str:
            return json.dumps(["not", "a", "mapping"])

    service = ConfigDQService(
        logger=logger,
        _pipeline_yaml_getter=lambda pipeline_name: {"provider": "crossref"},
        _dq_config_loader=lambda pipeline_name: DQConfig(),
        _effective_config_service=_BadEffectiveService(_sample_artifact_dict()),
    )

    with pytest.raises(TypeError, match="must be a mapping"):
        service.get_effective_config_artifact("crossref_publication")


def test_check_config_compatibility_combines_dq_and_effective_hashes() -> None:
    logger = MagicMock()
    effective_service = _StubEffectiveConfigService(_sample_artifact_dict())
    service = ConfigDQService(
        logger=logger,
        _pipeline_yaml_getter=lambda pipeline_name: {"provider": "crossref"},
        _dq_config_loader=lambda pipeline_name: DQConfig(),
        _effective_config_service=effective_service,
    )

    artifact1 = _sample_artifact_dict(effective_hash="same-hash")
    artifact2 = _sample_artifact_dict(effective_hash="same-hash")
    assert service.check_config_compatibility(artifact1, artifact2) is True

    artifact3 = _sample_artifact_dict(effective_hash="different-hash")
    assert service.check_config_compatibility(artifact1, artifact3) is False

    effective_service.compatibility_result = False
    assert service.check_config_compatibility(artifact1, artifact2) is False


def test_check_config_compatibility_returns_false_for_invalid_artifacts() -> None:
    logger = MagicMock()
    service = ConfigDQService(
        logger=logger,
        _pipeline_yaml_getter=lambda pipeline_name: {"provider": "crossref"},
        _dq_config_loader=lambda pipeline_name: DQConfig(),
        _effective_config_service=_StubEffectiveConfigService(_sample_artifact_dict()),
    )

    assert (
        service.check_config_compatibility({"broken": True}, {"broken": True}) is False
    )
    logger.error.assert_called_once()
