# Clients Layer (Ports & Adapters)

## Purpose
Describe how API clients are structured under the hexagonal model: domain defines ports, infrastructure provides adapters, application depends only on ports.

## Layout
- **Domain ports:** `src/bioetl/domain/clients/...` — ABC/Protocol definitions (no network code).
- **Infrastructure adapters:** `src/bioetl/infrastructure/clients/...` — concrete `*Impl` classes that use `UnifiedAPIClient` + `HttpClientMiddleware` for retries, backoff, rate limiting, and circuit breaker.
- **Registries:** `src/bioetl/infrastructure/clients/base/abc_registry.yaml` and `abc_impls.yaml` map ABC ↔ default factory ↔ implementation.

## Creation flow
1) Application/pipelines request a domain port (e.g., `ChemblDataClientABC`, `RequestBuilderABC`, `PaginatorABC`).  
2) Factories in infrastructure build adapters (`src/bioetl/infrastructure/clients/<provider>/factories.py`), wiring middleware and rate limiter.  
3) All HTTP goes through `UnifiedAPIClient`; no direct `requests` usage outside infrastructure.  
4) Assemblies are injected via DI/container; pipelines never import infrastructure modules directly.

## Naming
- Ports: `*_client_protocol.py` / `*_client_abc.py` live in `domain/clients`.
- Adapters: `<provider>_client_impl.py` (and helpers `request_builder.py`, `response_parser.py`, `paginator.py`) live in `infrastructure/clients/<provider>/impl` or sibling modules.
- Class suffixes: contracts end with `ABC`/`Protocol`; implementations end with `Impl`; factories end with `Factory`.

## Testing guidance
- Unit tests mock domain ports; no network calls.  
- Adapter tests live under `tests/bioetl/infrastructure/clients/...` and mock HTTP transport (`UnifiedAPIClient`/middleware).  
- No network in CI; use golden/property tests where applicable.

