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


@dataclass(frozen=True, slots=True)
class RunContextFactory:
    """Build ``RunContext`` for metadata coordinator wiring."""

    pipeline_name: str
    provider: str
    entity_type_extractor: EntityTypeExtractor
    pipeline_version_getter: Callable[[PipelineYamlConfig], str] = get_pipeline_version
    git_commit_getter: Callable[[], str | None] = get_git_commit
    config_hash_getter: Callable[[PipelineYamlConfig], str] = compute_config_hash

    def create(
        self,
        *,
        run_id: RunID,
        runtime: RuntimeConfig,
        yaml_config: PipelineYamlConfig,
        manifest_id: str | None = None,
    ) -> RunContext:
        """Create metadata ``RunContext`` from runtime and resolved YAML."""
        entity = self.entity_type_extractor(self.pipeline_name) or self.pipeline_name
        return RunContext.create(
            run_id=run_id,
            run_type=runtime.run_type,
            started_at=datetime.now(UTC),
            provider=self.provider,
            entity=entity,
            pipeline_version=self.pipeline_version_getter(yaml_config),
            git_commit=self.git_commit_getter(),
            config_hash=self.config_hash_getter(yaml_config),
            manifest_id=manifest_id,
        )
