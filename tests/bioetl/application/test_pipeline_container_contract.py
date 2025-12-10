from __future__ import annotations

from typing import Any, Callable

import pytest

from bioetl.application.contracts import PipelineContainerABC
from bioetl.domain.configs import ClientConfig, DummyProviderConfig, PipelineConfig

# Provider registry module was removed
# from bioetl.domain.provider_registry import InMemoryProviderRegistry

# Stubs for provider-registry-related names used only in skipped tests.
config: object | None = None
provider_registry: object | None = None


class StubContainer(PipelineContainerABC):
    def __init__(self, config: PipelineConfig) -> None:
        self._config = config
        self.record_source_calls: list[dict[str, Any]] = []
        self.post_transformer_version: str | None = None

    @property
    def config(self) -> PipelineConfig:
        return self._config

    def get_logger(self) -> str:
        return "logger"

    def get_validation_service(self) -> str:
        return "validation"

    def get_loader(self) -> str:
        return "loader"

    def get_extraction_service(self) -> str:
        return "extraction"

    def get_normalization_service(self) -> str:
        return "normalization"

    def get_record_source(
        self,
        extraction_service: Any,
        *,
        limit: int | None = None,
        logger: Any | None = None,
    ) -> str:
        self.record_source_calls.append({"limit": limit, "logger": logger})
        return "record_source"

    def get_metadata_builder(self) -> str:
        return "metadata_builder"

    def get_hash_service(self) -> str:
        return "hash"

    def get_post_transformer(
        self, *, version_provider: Callable[[], str] | None = None
    ) -> str:
        if version_provider:
            self.post_transformer_version = version_provider()
        return "post_transformer"

    def get_hooks(self) -> list[str]:
        return ["hook"]

    def get_error_policy(self) -> str:
        return "error_policy"


class DummyPipeline:
    def __init__(self, **deps: Any) -> None:
        self.dependencies = deps
        self.post_transformer: Any | None = None
        self.hooks: list[Any] = []
        self.error_policy: Any | None = None

    def set_post_transformer(self, transformer: Any) -> None:
        self.post_transformer = transformer

    def register_hooks(self, hooks: list[Any]) -> None:
        self.hooks.extend(hooks)

    def set_error_policy(self, error_policy: Any) -> None:
        self.error_policy = error_policy

    def get_version(self) -> str:
        return "pipeline-version"


def _build_config() -> PipelineConfig:
    return PipelineConfig(
        id="dummy.entity",
        provider="dummy",
        entity="entity",
        input_mode="auto_detect",
        input_path=None,
        output_path="/tmp/out",
        batch_size=10,
        provider_config=DummyProviderConfig(
            base_url="https://example.com",  # type: ignore[arg-type]
            client=ClientConfig(
                timeout_sec=1,
                max_retries=0,
                rate_limit_per_sec=1.0,
            ),
        ),
    )


def _assert_dependencies(
    pipeline: DummyPipeline, stub_container: StubContainer
) -> None:
    """Проверяет корректность зависимостей пайплайна."""
    expected_deps = {
        "logger": "logger",
        "validation_service": "validation",
        "loader": "loader",
        "extraction_service": "extraction",
        "normalization_service": "normalization",
        "record_source": "record_source",
        "hash_service": "hash",
        "hooks": ["hook"],
        "error_policy": "error_policy",
    }
    for key, expected_value in expected_deps.items():
        assert pipeline.dependencies[key] == expected_value

    assert stub_container.record_source_calls == [{"limit": 5, "logger": "logger"}]
    assert pipeline.post_transformer == "post_transformer"
    assert stub_container.post_transformer_version == "pipeline-version"
    assert pipeline.hooks == ["hook"]
    assert pipeline.error_policy == "error_policy"


@pytest.mark.skip(reason="Provider registry module was removed")
def test_pipeline_container_satisfies_contract() -> None:
    """Legacy provider registry contract test disabled until module returns."""
