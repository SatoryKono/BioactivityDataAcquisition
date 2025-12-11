"""Helpers for validating CLI input and building pipeline requests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bioetl.application.use_cases import RunPipelineRequest
from bioetl.interfaces.composition_root import CompositionRoot


@dataclass(frozen=True)
class RunCommandParams:
    """DTO with parsed CLI parameters for the run command."""

    pipeline_name: str
    config: str | None
    output: str | None
    limit: int | None
    dry_run: bool
    profile: str | None


class RunCommandRequestBuilder:
    """Builds validated :class:`RunPipelineRequest` from CLI params."""

    def __init__(self, composition_root: CompositionRoot) -> None:
        self._composition_root = composition_root

    def build(self, params: RunCommandParams) -> RunPipelineRequest:
        """Validate arguments and create a request object."""
        limit = self._validate_limit(params.limit)
        config_path = self.resolve_config_path(params.config)
        output_path = Path(params.output) if params.output else None

        return RunPipelineRequest(
            pipeline_name=params.pipeline_name,
            config_path=config_path,
            output_path=output_path,
            limit=limit,
            dry_run=params.dry_run,
            profile=params.profile or "default",
        )

    def resolve_config_path(self, config: str | None) -> Path | None:
        """Resolve provided config path or map to configs root."""
        if not config:
            return None

        provided_path = Path(config)
        if provided_path.exists():
            return provided_path

        path_resolver = self._composition_root.create_config_path_resolver()
        configs_root = path_resolver.configs_root
        candidate = configs_root / config if configs_root else None
        if candidate and candidate.exists():
            return candidate

        candidates = [str(provided_path)]
        if candidate:
            candidates.append(str(candidate))

        raise FileNotFoundError(
            "Config file not found: {config}; tried {attempts}".format(
                config=config, attempts=", ".join(candidates)
            )
        )

    @staticmethod
    def _validate_limit(limit: int | None) -> int | None:
        """Ensure limit is positive when provided."""
        if limit is None:
            return None
        if limit <= 0:
            raise ValueError("Limit must be a positive integer")
        return limit


__all__ = ["RunCommandParams", "RunCommandRequestBuilder"]
