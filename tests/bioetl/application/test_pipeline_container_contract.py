from __future__ import annotations

from typing import Any, Callable

from bioetl.application.container import PipelineContainer
from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.application.pipelines.contracts import PipelineContainerABC
from bioetl.domain.configs import DummyProviderConfig, PipelineConfig


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

    def get_output_writer(self) -> str:
        return "writer"

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

    def add_hooks(self, hooks: list[Any]) -> None:
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
            timeout_sec=1,
            max_retries=0,
            rate_limit_per_sec=1.0,
        ),
    )


def test_pipeline_container_satisfies_contract(monkeypatch: Any) -> None:
    config = _build_config()
    container = PipelineContainer(config)

    assert isinstance(container, PipelineContainerABC)

    stub_container = StubContainer(config)
    monkeypatch.setattr(
        "bioetl.application.orchestrator.get_pipeline_class", lambda _: DummyPipeline
    )

    orchestrator = PipelineOrchestrator(
        "dummy.entity",
        config,
        container_factory=lambda *args, **kwargs: stub_container,
    )

    pipeline = orchestrator.build_pipeline(limit=5)

    assert isinstance(pipeline, DummyPipeline)
    assert pipeline.dependencies["logger"] == "logger"
    assert pipeline.dependencies["validation_service"] == "validation"
    assert pipeline.dependencies["output_writer"] == "writer"
    assert pipeline.dependencies["extraction_service"] == "extraction"
    assert pipeline.dependencies["normalization_service"] == "normalization"
    assert pipeline.dependencies["record_source"] == "record_source"
    assert pipeline.dependencies["hash_service"] == "hash"
    assert pipeline.dependencies["hooks"] == ["hook"]
    assert pipeline.dependencies["error_policy"] == "error_policy"
    assert stub_container.record_source_calls == [{"limit": 5, "logger": "logger"}]
    assert pipeline.post_transformer == "post_transformer"
    assert stub_container.post_transformer_version == "pipeline-version"
    assert pipeline.hooks == ["hook"]
    assert pipeline.error_policy == "error_policy"
