from __future__ import annotations

from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.domain.configs import DummyProviderConfig, PipelineConfig
from bioetl.domain.provider_registry import InMemoryProviderRegistry


def _build_dummy_config() -> PipelineConfig:
    return PipelineConfig(
        id="dummy.pipeline",
        provider="dummy",
        entity="dummy",
        input_mode="auto_detect",
        input_path=None,
        output_path="out",
        batch_size=1,
        provider_config=DummyProviderConfig(
            base_url="https://example.com",
            timeout_sec=1,
            max_retries=0,
            rate_limit_per_sec=1.0,
        ),
    )


def test_orchestrator_uses_provider_loader_when_flag_enabled() -> None:
    class StubLoader:
        def __init__(self) -> None:
            self.registry = InMemoryProviderRegistry()
            self.calls = 0

        def load_registry(
            self, *, registry: InMemoryProviderRegistry | None = None
        ) -> InMemoryProviderRegistry:
            self.calls += 1
            return registry or self.registry

    loader = StubLoader()
    orchestrator = PipelineOrchestrator(
        "dummy.pipeline",
        _build_dummy_config(),
        provider_registry=None,
        provider_loader=loader,
        provider_loader_factory=lambda: loader,
        use_provider_loader_port=True,
    )

    registry = orchestrator._get_provider_registry()

    assert registry is loader.registry
    assert loader.calls == 1

