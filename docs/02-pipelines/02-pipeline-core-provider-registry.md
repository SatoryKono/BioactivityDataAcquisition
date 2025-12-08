# Pipeline Core Provider Registry

## Provider registry ports

- `ProviderRegistryABC` (`bioetl.domain.provider_registry`) exposes read/write access to provider definitions consumed across pipelines.
- `ProviderRegistryLoaderABC` (`bioetl.domain.provider_registry`) acts as the orchestrator-facing loader port so background runs can resolve registry content without global state.

## Factories and implementations

- Default loader factory: `bioetl.infrastructure.clients.provider_registry_loader.default_provider_registry_loader` producing `ProviderRegistryLoader`.
- Registries are backed by `InMemoryProviderRegistry` for deterministic, testable state.
- `abc_impls.yaml` maps `ProviderRegistryLoader` to the loader port to keep factories discoverable by containers.

## Orchestrator flow

`PipelineOrchestrator` (`src/bioetl/application/orchestrator.py`) всегда пытается загрузить реестр через `ProviderRegistryLoaderABC`, если загрузчик или фабрика переданы из composition root. Реестр создаётся как `InMemoryProviderRegistry`, заполняется на месте и передаётся контейнеру пайплайна без глобальных синглтонов. Если загрузчик недоступен (например, отсутствует `configs/providers.yaml`), orchestrator ожидает, что вызывающая сторона предоставит предсконфигурированный `ProviderRegistryABC`.
