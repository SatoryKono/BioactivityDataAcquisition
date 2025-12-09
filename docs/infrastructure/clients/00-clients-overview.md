# 00-clients-overview

- **Domain layer:** Contracts live in `src/bioetl/domain/clients/...`.
- **Infrastructure (adapters):** Implementations live in `src/bioetl/infrastructure/clients/...` and rely on `UnifiedAPIClient` with explicit timeouts and rate limiting. No network calls are allowed outside infrastructure.
- **Application:** Wiring happens in the application layer through factories and providers (see `src/bioetl/infrastructure/chembl_client.py`).

## Key rules

- Transport: all HTTP goes through `UnifiedAPIClient` with configured timeouts and rate limiting.
- Builders/parsers/paginators: keep them pure and deterministic; no network access or IO.
- Observability: use structured logging, metrics, and tracing through the observability ports.
- Caching: provided by infrastructure caches; avoid ad-hoc caches in pipelines.
- Secrets: resolved through `SecretProviderABC` implementations; avoid reading env vars directly in business logic.
