"""DQ-focused configuration operations for CLI/config tooling."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, cast

from bioetl.application.services.effective_config_service import EffectiveConfigService
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
from bioetl.domain.ports import LoggerPort
from bioetl.domain.services.dq_policy_resolver import DQPolicyResolver
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import DQDisposition, DQPolicyRef


class DQConfigLoaderPort(Protocol):
    """Callable port for loading DQ configs by pipeline name."""

    def __call__(self, pipeline_name: str) -> DQConfig: ...


class PipelineYamlConfigGetterPort(Protocol):
    """Callable port returning mapped pipeline YAML config."""

    def __call__(self, pipeline_name: str) -> JsonDict: ...


DQStrictnessMode = Literal["lenient", "moderate", "strict"]
DQSnapshotStrictnessMode = Literal["lenient", "moderate", "standard", "strict"]


def _parse_disposition(value: object) -> DQDisposition:
    if isinstance(value, DQDisposition):
        return value
    if isinstance(value, str):
        return DQDisposition(value)
    raise ValueError(f"Invalid DQ disposition value: {value!r}")


def _parse_strictness_mode(value: object) -> DQStrictnessMode:
    if value in {"lenient", "moderate", "strict"}:
        return cast("DQStrictnessMode", value)
    raise ValueError(f"Invalid DQ strictness mode: {value!r}")


def _parse_snapshot_strictness_mode(value: object) -> DQSnapshotStrictnessMode:
    if value in {"lenient", "moderate", "standard", "strict"}:
        return cast("DQSnapshotStrictnessMode", value)
    raise ValueError(f"Invalid DQ snapshot strictness mode: {value!r}")


def _parse_disposition_overrides(overrides: object) -> dict[str, DQDisposition]:
    if isinstance(overrides, dict):
        return {str(key): _parse_disposition(value) for key, value in overrides.items()}
    if isinstance(overrides, (list, tuple)):
        parsed: dict[str, DQDisposition] = {}
        for pair in overrides:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise ValueError(
                    "Disposition overrides entries must be key/value pairs"
                )
            parsed[str(pair[0])] = _parse_disposition(pair[1])
        return parsed
    raise ValueError("Disposition overrides must be a mapping or sequence of pairs")


def _disposition_overrides_to_strings(overrides: object) -> dict[str, str]:
    parsed = _parse_disposition_overrides(overrides)
    return {key: value.value for key, value in parsed.items()}


def _dq_config_to_dict(dq_config: DQConfig) -> JsonDict:
    return {
        "contract_ref": dq_config.contract_ref,
        "contract_version": dq_config.contract_version,
        "rule_bundle_version": dq_config.rule_bundle_version,
        "default_disposition_policy": dq_config.default_disposition_policy.value,
        "disposition_overrides": _disposition_overrides_to_strings(
            dq_config.disposition_overrides
        ),
        "strictness_mode": dq_config.strictness_mode,
    }


def _dict_to_artifact(artifact_dict: JsonDict) -> EffectiveConfigArtifact:
    source_refs = [
        ConfigSourceRef(
            source_type=str(src["source_type"]),
            source_path=str(src["source_path"]),
            source_hash=str(src["source_hash"]) if src.get("source_hash") else None,
            priority=int(src["priority"]),
        )
        for src in artifact_dict["source_refs"]
    ]
    resolved_config = ResolvedConfigSnapshot(
        config_type=str(artifact_dict["resolved_config"]["config_type"]),
        config_data=dict(artifact_dict["resolved_config"]["config_data"]),
        config_hash=str(artifact_dict["resolved_config"]["config_hash"]),
        timestamp=datetime.fromisoformat(
            str(artifact_dict["resolved_config"]["timestamp"])
        ),
    )
    runtime_overrides = RuntimeOverrideSnapshot(
        cli_overrides=dict(artifact_dict["runtime_overrides"]["cli_overrides"]),
        env_overrides=dict(artifact_dict["runtime_overrides"]["env_overrides"]),
        runtime_adjustments=dict(
            artifact_dict["runtime_overrides"]["runtime_adjustments"]
        ),
        override_hash=str(artifact_dict["runtime_overrides"].get("override_hash", "")),
    )
    effective_execution_config = EffectiveExecutionConfig(
        config_data=dict(artifact_dict["effective_execution_config"]["config_data"]),
        effective_hash=str(
            artifact_dict["effective_execution_config"]["effective_hash"]
        ),
        timestamp=datetime.fromisoformat(
            str(artifact_dict["effective_execution_config"]["timestamp"])
        ),
    )
    dq_policy_refs = [
        DQPolicyRef(
            contract_ref=str(ref["contract_ref"]),
            contract_version=str(ref["contract_version"]),
            rule_bundle_version=str(ref["rule_bundle_version"]),
            policy_hash=str(ref["policy_hash"]),
        )
        for ref in artifact_dict.get("dq_policy_refs", [])
    ]
    dq_policy_snapshots = [
        DQPolicySnapshot(
            contract_ref=str(snapshot["contract_ref"]),
            contract_version=str(snapshot["contract_version"]),
            rule_bundle_version=str(snapshot["rule_bundle_version"]),
            policy_hash=str(snapshot["policy_hash"]),
            default_disposition=_parse_disposition(snapshot["default_disposition"]),
            disposition_overrides=_parse_disposition_overrides(
                snapshot["disposition_overrides"]
            ),
            strictness_mode=_parse_snapshot_strictness_mode(
                snapshot["strictness_mode"]
            ),
        )
        for snapshot in artifact_dict.get("dq_policy_snapshots", [])
    ]
    return EffectiveConfigArtifact(
        artifact_id=str(artifact_dict["artifact_id"]),
        pipeline_name=str(artifact_dict["pipeline_name"]),
        pipeline_kind=str(artifact_dict["pipeline_kind"]),
        source_refs=source_refs,
        resolution_policy=ConfigResolutionPolicy(
            merge_strategy=str(artifact_dict["resolution_policy"]["merge_strategy"]),
            default_materialization=bool(
                artifact_dict["resolution_policy"]["default_materialization"]
            ),
            strict_validation=bool(
                artifact_dict["resolution_policy"]["strict_validation"]
            ),
            allow_runtime_overrides=bool(
                artifact_dict["resolution_policy"]["allow_runtime_overrides"]
            ),
        ),
        resolved_config=resolved_config,
        runtime_overrides=runtime_overrides,
        effective_execution_config=effective_execution_config,
        resolved_config_hash=str(artifact_dict["resolved_config_hash"]),
        effective_config_hash=str(artifact_dict["effective_config_hash"]),
        source_fingerprint=str(artifact_dict["source_fingerprint"]),
        schema_version=str(artifact_dict.get("schema_version", "1.0")),
        created_at=datetime.fromisoformat(str(artifact_dict["created_at"])),
        contract_refs=[str(value) for value in artifact_dict.get("contract_refs", [])],
        dq_policy_refs=dq_policy_refs,
        dq_rule_bundle_versions=dict(artifact_dict.get("dq_rule_bundle_versions", {})),
        dq_contract_compatibility_hash=str(
            artifact_dict.get("dq_contract_compatibility_hash", "")
        ),
        dq_policy_snapshots=dq_policy_snapshots,
    )


@dataclass
class ConfigDQService:
    """Provide DQ/effective-config operations behind injected dependencies."""

    logger: LoggerPort
    _pipeline_yaml_getter: PipelineYamlConfigGetterPort
    _dq_config_loader: DQConfigLoaderPort
    _effective_config_service: EffectiveConfigService

    def get_dq_config(self, pipeline_name: str) -> JsonDict:
        self.logger.debug("Getting DQ config", pipeline=pipeline_name)
        dq_config = self._dq_config_loader(pipeline_name)
        config_dict = _dq_config_to_dict(dq_config)
        self.logger.info("Got DQ config", pipeline=pipeline_name)
        return config_dict

    def validate_dq_config(self, pipeline_name: str, dq_config: JsonDict) -> bool:
        self.logger.debug("Validating DQ config", pipeline=pipeline_name)
        try:
            validated_config = DQConfig(
                contract_ref=dq_config.get("contract_ref"),
                contract_version=dq_config.get("contract_version"),
                rule_bundle_version=dq_config.get("rule_bundle_version"),
                default_disposition_policy=_parse_disposition(
                    dq_config.get("default_disposition_policy", DQDisposition.WARN)
                ),
                disposition_overrides=_parse_disposition_overrides(
                    dq_config.get("disposition_overrides", {})
                ),
                strictness_mode=_parse_strictness_mode(
                    dq_config.get("strictness_mode", "moderate")
                ),
            )
            DQPolicyResolver(validated_config).build_policy_ref()
            self.logger.info("Validated DQ config", pipeline=pipeline_name)
            return True
        except (TypeError, ValueError) as error:
            self.logger.error(
                "DQ config validation failed",
                pipeline=pipeline_name,
                error=str(error),
            )
            return False

    def get_effective_config_artifact(
        self,
        pipeline_name: str,
        runtime_overrides: JsonDict | None = None,
    ) -> JsonDict:
        self.logger.debug("Getting effective config artifact", pipeline=pipeline_name)
        pipeline_config = self._pipeline_yaml_getter(pipeline_name)
        provider = str(pipeline_config.get("provider", "unknown"))
        source_refs = [
            ConfigSourceRef(
                source_type="file",
                source_path="configs/base/pipeline.yaml",
                source_hash="auto",
                priority=1,
            ),
            ConfigSourceRef(
                source_type="file",
                source_path=f"configs/providers/{provider}.yaml",
                source_hash="auto",
                priority=2,
            ),
        ]
        dq_config: DQConfig | None = None
        try:
            dq_config = self._dq_config_loader(pipeline_name)
        except (FileNotFoundError, ValueError):
            dq_config = None

        effective_runtime_overrides = runtime_overrides or {}
        artifact = self._effective_config_service.create_effective_config_artifact(
            pipeline_name=pipeline_name,
            pipeline_kind="standard",
            resolved_config=pipeline_config,
            runtime_overrides=effective_runtime_overrides,
            source_refs=source_refs,
            dq_config=dq_config,
        )
        artifact_dict = json.loads(
            self._effective_config_service.serialize_artifact(artifact)
        )
        self.logger.info("Created effective config artifact", pipeline=pipeline_name)
        if not isinstance(artifact_dict, dict):
            raise TypeError("Effective config artifact payload must be a mapping")
        return cast("JsonDict", artifact_dict)

    def check_config_compatibility(
        self, artifact1: JsonDict, artifact2: JsonDict
    ) -> bool:
        self.logger.debug("Checking config compatibility")
        try:
            artifact1_obj = _dict_to_artifact(artifact1)
            artifact2_obj = _dict_to_artifact(artifact2)
        except (TypeError, ValueError, KeyError) as error:
            self.logger.error("Config compatibility check failed", error=str(error))
            return False

        dq_compatible = self._effective_config_service.check_dq_compatibility(
            artifact1_obj,
            artifact2_obj,
        )
        effective_compatible = artifact1.get("effective_config_hash") == artifact2.get(
            "effective_config_hash"
        )
        self.logger.info(
            "Checked config compatibility",
            dq_compatible=dq_compatible,
            effective_compatible=effective_compatible,
        )
        return dq_compatible and effective_compatible
