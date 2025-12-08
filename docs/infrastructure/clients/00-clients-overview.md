# Clients Overview

## Hexagonal layout

- **Domain (ports):** API client contracts live in `src/bioetl/domain/clients/...` (e.g., `DataClientABC`, `RequestBuilderABC`, `ResponseParserABC`, `PaginatorABC`, `RateLimiterABC`). These are pure ABC/Protocol types with no network code.
- **Infrastructure (adapters):** Implementations live in `src/bioetl/infrastructure/clients/...` and must use `UnifiedAPIClient` + `HttpClientMiddleware` for retries, backoff, rate limiting, and circuit breaker. No network calls are allowed outside infrastructure.
- **Factories/DI:** Client factories assemble adapters and wire middleware; see `src/bioetl/infrastructure/clients/chembl/factories.py`. ABC → Default factory → Impl mapping is tracked in `abc_registry.yaml` and `abc_impls.yaml`.

## ChEMBL stack

- **Contract:** `DataClientABC` (`src/bioetl/domain/clients/contracts.py`).
- **HTTP adapter:** `ChemblDataClientHTTPImpl` (`infrastructure/clients/chembl/impl/http_client.py`) built on `UnifiedAPIClient` and `RateLimiterABC`.
- **Request builder:** `ChemblRequestBuilderImpl` (`infrastructure/clients/chembl/request_builder.py`).
- **Response parser:** `ChemblResponseParserImpl` (`infrastructure/clients/chembl/response_parser.py`).
- **Paginator:** `ChemblPaginatorImpl` (`infrastructure/clients/chembl/paginator.py`).
- **Factories:**
  - `default_chembl_client` / `default_chembl_extraction_service` (`infrastructure/clients/chembl/factories.py`) — собирают HTTP‑клиент и сервис экстракции.
  - Публичные точки входа `create_client` / `create_extraction_service` (`infrastructure/chembl_client.py`) используют фабрики по умолчанию.

## Policies

- Transport: all HTTP goes through `UnifiedAPIClient` + `HttpClientMiddleware` with configured timeouts, retries/backoff, rate limiting, and circuit breaker.
- Validation: JSON responses are parsed and validated; errors are wrapped in `ClientResponseError`.
- Pagination: handled by `ChemblPaginatorImpl` (next-marker strategy) and extensible for new endpoints.

## Usage in pipelines

- Pipelines consume only domain ports. `ChemblPipelineBase` receives `ExtractionServiceABC`, which internally uses the ChEMBL client adapter chain.
- Input source is selected by config (`input_mode=api|csv|id_only`); when `api`, the pipeline uses the stack above via the factory.
