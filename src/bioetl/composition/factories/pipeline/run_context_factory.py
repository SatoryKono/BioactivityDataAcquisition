"""Run-context assembly helpers for pipeline construction."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from bioetl.composition.factories.pipeline.construction_types import (
    EntityTypeExtractor,
)
from bioetl.composition.services.versioning import (
    compute_config_hash,
    get_git_commit,
    get_pipeline_version,
)
from bioetl.domain.context import current_utc_time
from bioetl.domain.value_objects.run_context import RunContext, RunContextCreateInput

if TYPE_CHECKING:
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _get_transform_version(yaml_config: PipelineYamlConfig) -> str | None:
    """Extract transform version from resolved pipeline YAML config."""
    transform = getattr(yaml_config, "transform", None)
    version = getattr(transform, "version", None)
    return str(version) if version is not None else None


def _get_transform_steps(yaml_config: PipelineYamlConfig) -> tuple[str, ...]:
    """Extract transform steps from resolved pipeline YAML config."""
    transform = getattr(yaml_config, "transform", None)
    steps = getattr(transform, "steps", ())
    return tuple(str(step) for step in (steps or ()))


def _coerce_optional_text(value: object) -> str | None:
    """Return normalized non-empty text when available."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_contract_identity_snapshot(
    provider: str,
    entity: str,
) -> tuple[str, str | None, str | None, str | None, str | None]:
    """Resolve contract identity fields from the canonical registry."""
    contract_ref = f"{provider}.{entity}"
    registry_path = Path("configs/base/contract_registry.yaml")
    if not registry_path.exists():
        return contract_ref, None, None, None, None
    try:
        payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return contract_ref, None, None, None, None
    if not isinstance(payload, dict):
        return contract_ref, None, None, None, None
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        return contract_ref, None, None, None, None
    entry = entries.get(contract_ref)
    if not isinstance(entry, dict):
        return contract_ref, None, None, None, None
    identity = entry.get("identity")
    identity_payload = identity if isinstance(identity, dict) else {}
    contract_version = _coerce_optional_text(identity_payload.get("contract_version"))
    contract_schema_hash = _coerce_optional_text(identity_payload.get("schema_hash"))
    dq_policy_ref = _coerce_optional_text(
        identity_payload.get("dq_policy_ref") or entry.get("dq_policy_ref")
    )
    rule_bundle_version = _coerce_optional_text(
        identity_payload.get("rule_bundle_version") or entry.get("rule_bundle_version")
    )
    return (
        contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
    )


@dataclass(frozen=True, slots=True)
class RunContextFactory:
    """Build ``RunContext`` for metadata coordinator wiring."""

    pipeline_name: str
    provider: str
    entity_type_extractor: EntityTypeExtractor
    pipeline_version_getter: Callable[[PipelineYamlConfig], str] = get_pipeline_version
    git_commit_getter: Callable[[], str | None] = get_git_commit
    config_hash_getter: Callable[[PipelineYamlConfig], str] = compute_config_hash
    transform_version_getter: Callable[[PipelineYamlConfig], str | None] = (
        _get_transform_version
    )
    transform_steps_getter: Callable[[PipelineYamlConfig], tuple[str, ...]] = (
        _get_transform_steps
    )
    started_at_factory: Callable[[], datetime] = current_utc_time
    contract_identity_resolver: Callable[
        [str, str], tuple[str, str | None, str | None, str | None, str | None]
    ] = _resolve_contract_identity_snapshot

    def create(
        self,
        *,
        run_id: RunID,
        runtime: RuntimeConfig,
        yaml_config: PipelineYamlConfig,
        manifest_id: str | None = None,
        execution_fingerprint: str | None = None,
        config_hash: str | None = None,
        resolved_config_hash: str | None = None,
        effective_config_hash: str | None = None,
        dq_contract_compatibility_hash: str | None = None,
        effective_config_artifact_id: str | None = None,
    ) -> RunContext:
        """Create metadata ``RunContext`` from runtime and resolved YAML."""
        entity = self.entity_type_extractor(self.pipeline_name) or self.pipeline_name
        (
            contract_ref,
            contract_version,
            contract_schema_hash,
            dq_policy_ref,
            rule_bundle_version,
        ) = self.contract_identity_resolver(self.provider, entity)
        resolved_hash = (
            self.config_hash_getter(yaml_config)
            if resolved_config_hash is None
            else resolved_config_hash
        )
        legacy_config_hash = config_hash if config_hash is not None else resolved_hash
        return RunContext.create(
            RunContextCreateInput(
                run_id=run_id,
                run_type=runtime.run_type,
                started_at=self.started_at_factory(),
                provider=self.provider,
                entity=entity,
                transform_version=self.transform_version_getter(yaml_config),
                transform_steps=self.transform_steps_getter(yaml_config),
                pipeline_version=self.pipeline_version_getter(yaml_config),
                git_commit=self.git_commit_getter(),
                config_hash=legacy_config_hash,
                resolved_config_hash=resolved_hash,
                effective_config_hash=effective_config_hash,
                manifest_id=manifest_id,
                execution_fingerprint=execution_fingerprint,
                contract_ref=contract_ref,
                contract_version=contract_version,
                contract_schema_hash=contract_schema_hash,
                dq_policy_ref=dq_policy_ref,
                rule_bundle_version=rule_bundle_version,
                dq_contract_compatibility_hash=dq_contract_compatibility_hash,
                effective_config_artifact_id=effective_config_artifact_id,
            )
        )
