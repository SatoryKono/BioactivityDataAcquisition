"""Run-context assembly helpers for pipeline construction."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.composition.factories.pipeline.construction_types import (
    EntityTypeExtractor,
)
from bioetl.composition.services.versioning import (
    compute_config_hash,
    get_git_commit,
    get_pipeline_version,
)
from bioetl.domain.value_objects.run_context import RunContext

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

    def create(
        self,
        *,
        run_id: RunID,
        runtime: RuntimeConfig,
        yaml_config: PipelineYamlConfig,
        manifest_id: str | None = None,
        config_hash: str | None = None,
        dq_contract_compatibility_hash: str | None = None,
        effective_config_artifact_id: str | None = None,
    ) -> RunContext:
        """Create metadata ``RunContext`` from runtime and resolved YAML."""
        entity = self.entity_type_extractor(self.pipeline_name) or self.pipeline_name
        resolved_config_hash = (
            self.config_hash_getter(yaml_config) if config_hash is None else config_hash
        )
        return RunContext.create(
            run_id=run_id,
            run_type=runtime.run_type,
            started_at=datetime.now(UTC),
            provider=self.provider,
            entity=entity,
            transform_version=self.transform_version_getter(yaml_config),
            transform_steps=self.transform_steps_getter(yaml_config),
            pipeline_version=self.pipeline_version_getter(yaml_config),
            git_commit=self.git_commit_getter(),
            config_hash=resolved_config_hash,
            manifest_id=manifest_id,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            effective_config_artifact_id=effective_config_artifact_id,
        )
