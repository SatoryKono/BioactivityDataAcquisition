# 02 Pipeline Core Provider Registry

## Provider registry ports

- `ProviderRegistryABC` / `MutableProviderRegistryABC` (`bioetl.domain.provider_registry`) expose read/write access to provider definitions consumed across pipelines.
- `ProviderRegistryLoaderABC` (`bioetl.domain.provider_registry`) acts as the orchestrator-facing loader port so background runs can resolve registry content without global state.

## Factories and implementations

- Default loader factory: `bioetl.infrastructure.clients.provider_registry_loader.default_provider_registry_loader` producing `ProviderRegistryLoader`.
- Registries are backed by `InMemoryProviderRegistry` for deterministic, testable state.
- `abc_impls.yaml` maps `ProviderRegistryLoader` to the loader port to keep factories discoverable by containers.

## Orchestrator flow

`PipelineOrchestrator` (`src/bioetl/application/orchestrator.py`) optionally enables the loader port for background execution. When `use_provider_loader_port` is set, the orchestrator resolves a `ProviderRegistryLoaderABC` instance, loads registry definitions into an `InMemoryProviderRegistry`, and injects it into the pipeline container for consistent provider resolution across processes.
