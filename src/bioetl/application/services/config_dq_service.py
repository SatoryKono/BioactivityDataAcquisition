"""DQ-focused configuration operations for CLI/config tooling."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol, cast

from bioetl.application.services.control_plane.effective_config_service import (
    EffectiveConfigService,
)
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane.config_source_hashing import (
    ConfigSourceHashStrategy,
    compute_config_source_hashes,
)
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


def _compute_file_hashes(
    *,
    relative_path: str,
    path: Path,
) -> tuple[str | None, str | None, str | None]:
    """Return semantic and raw hashes for one config source file when available."""
    if not path.exists() or not path.is_file():
        return None, None, None
    hashes = compute_config_source_hashes(
        source_path=relative_path,
        raw_bytes=path.read_bytes(),
    )
    return hashes.semantic_hash, hashes.raw_hash, hashes.hash_strategy


def _build_config_source_ref(
    *,
    relative_path: str,
    priority: int,
    repo_root: Path,
) -> ConfigSourceRef:
    """Build one file-backed source ref for admin effective-config tooling."""
    source_path = repo_root / relative_path
    source_hash, raw_source_hash, source_hash_strategy = _compute_file_hashes(
        relative_path=relative_path,
        path=source_path,
    )
    return ConfigSourceRef(
        source_type="file",
        source_path=relative_path,
        source_hash=source_hash,
        raw_source_hash=raw_source_hash,
        source_hash_strategy=source_hash_strategy,
        priority=priority,
    )


def _build_source_refs(artifact_dict: JsonDict) -> list[ConfigSourceRef]:
    """Reconstruct source references from the serialized artifact payload."""
    return [
        ConfigSourceRef(
            source_type=str(src["source_type"]),
            source_path=str(src["source_path"]),
            source_hash=str(src["source_hash"]) if src.get("source_hash") else None,
            raw_source_hash=(
                str(src["raw_source_hash"]) if src.get("raw_source_hash") else None
            ),
            source_hash_strategy=(
                cast("ConfigSourceHashStrategy", str(src["source_hash_strategy"]))
                if src.get("source_hash_strategy")
                else None
            ),
            priority=int(src["priority"]),
        )
        for src in artifact_dict["source_refs"]
    ]


def _build_resolved_config_snapshot(
    artifact_dict: JsonDict,
) -> ResolvedConfigSnapshot:
    """Reconstruct the resolved config snapshot from serialized state."""
    resolved = artifact_dict["resolved_config"]
    return ResolvedConfigSnapshot(
        config_type=str(resolved["config_type"]),
        config_data=dict(resolved["config_data"]),
        config_hash=str(resolved["config_hash"]),
        timestamp=datetime.fromisoformat(str(resolved["timestamp"])),
    )


def _build_runtime_override_snapshot(
    artifact_dict: JsonDict,
) -> RuntimeOverrideSnapshot:
    """Reconstruct runtime override state from serialized artifact data."""
    runtime_overrides = artifact_dict["runtime_overrides"]
    return RuntimeOverrideSnapshot(
        cli_overrides=dict(runtime_overrides["cli_overrides"]),
        env_overrides=dict(runtime_overrides["env_overrides"]),
        runtime_adjustments=dict(runtime_overrides["runtime_adjustments"]),
        override_hash=str(runtime_overrides.get("override_hash", "")),
    )


def _build_effective_execution_config(
    artifact_dict: JsonDict,
) -> EffectiveExecutionConfig:
    """Reconstruct the effective execution config snapshot."""
    effective = artifact_dict["effective_execution_config"]
    return EffectiveExecutionConfig(
        config_data=dict(effective["config_data"]),
        effective_hash=str(effective["effective_hash"]),
        timestamp=datetime.fromisoformat(str(effective["timestamp"])),
    )


def _build_dq_policy_refs(artifact_dict: JsonDict) -> list[DQPolicyRef]:
    """Reconstruct DQ policy references from the serialized artifact payload."""
    return [
        DQPolicyRef(
            contract_ref=str(ref["contract_ref"]),
            contract_version=str(ref["contract_version"]),
            rule_bundle_version=str(ref["rule_bundle_version"]),
            policy_hash=str(ref["policy_hash"]),
        )
        for ref in artifact_dict.get("dq_policy_refs", [])
    ]


def _build_dq_policy_snapshots(artifact_dict: JsonDict) -> list[DQPolicySnapshot]:
    """Reconstruct DQ policy snapshots from the serialized artifact payload."""
    return [
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


def _build_resolution_policy(artifact_dict: JsonDict) -> ConfigResolutionPolicy:
    """Reconstruct the config resolution policy from serialized artifact data."""
    policy = artifact_dict["resolution_policy"]
    return ConfigResolutionPolicy(
        merge_strategy=str(policy["merge_strategy"]),
        default_materialization=bool(policy["default_materialization"]),
        strict_validation=bool(policy["strict_validation"]),
        allow_runtime_overrides=bool(policy["allow_runtime_overrides"]),
    )


def _dict_to_artifact(artifact_dict: JsonDict) -> EffectiveConfigArtifact:
    return EffectiveConfigArtifact(
        artifact_id=str(artifact_dict["artifact_id"]),
        pipeline_name=str(artifact_dict["pipeline_name"]),
        pipeline_kind=str(artifact_dict["pipeline_kind"]),
        source_refs=_build_source_refs(artifact_dict),
        resolution_policy=_build_resolution_policy(artifact_dict),
        resolved_config=_build_resolved_config_snapshot(artifact_dict),
        runtime_overrides=_build_runtime_override_snapshot(artifact_dict),
        effective_execution_config=_build_effective_execution_config(artifact_dict),
        resolved_config_hash=str(artifact_dict["resolved_config_hash"]),
        effective_config_hash=str(artifact_dict["effective_config_hash"]),
        source_fingerprint=str(artifact_dict["source_fingerprint"]),
        schema_version=str(artifact_dict.get("schema_version", "1.0")),
        created_at=datetime.fromisoformat(str(artifact_dict["created_at"])),
        contract_refs=[str(value) for value in artifact_dict.get("contract_refs", [])],
        dq_policy_refs=_build_dq_policy_refs(artifact_dict),
        dq_rule_bundle_versions=dict(artifact_dict.get("dq_rule_bundle_versions", {})),
        dq_contract_compatibility_hash=str(
            artifact_dict.get("dq_contract_compatibility_hash", "")
        ),
        dq_policy_snapshots=_build_dq_policy_snapshots(artifact_dict),
    )


@dataclass
class ConfigDQService:
    """Provide DQ/effective-config operations behind injected dependencies."""

    logger: LoggerPort
    _pipeline_yaml_getter: PipelineYamlConfigGetterPort
    _dq_config_loader: DQConfigLoaderPort
    _effective_config_service: EffectiveConfigService
    _repo_root: Path | None = None

    def get_dq_config(self, pipeline_name: str) -> JsonDict:
        """Load and normalize the pipeline-level DQ configuration."""
        self.logger.debug("Getting DQ config", pipeline=pipeline_name)
        dq_config = self._dq_config_loader(pipeline_name)
        config_dict = _dq_config_to_dict(dq_config)
        self.logger.info("Got DQ config", pipeline=pipeline_name)
        return config_dict

    def validate_dq_config(self, pipeline_name: str, dq_config: JsonDict) -> bool:
        """Validate a candidate DQ config payload for one pipeline."""
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
        """Build the effective-config control-plane artifact for one pipeline."""
        self.logger.debug("Getting effective config artifact", pipeline=pipeline_name)
        pipeline_config = self._pipeline_yaml_getter(pipeline_name)
        provider = str(pipeline_config.get("provider", "unknown"))
        repo_root = self._repo_root or Path(__file__).resolve().parents[4]
        source_refs = [
            _build_config_source_ref(
                relative_path="configs/base/pipeline.yaml",
                priority=1,
                repo_root=repo_root,
            ),
            _build_config_source_ref(
                relative_path=f"configs/providers/{provider}.yaml",
                priority=2,
                repo_root=repo_root,
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
        """Compare two effective-config artifacts for compatibility."""
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
