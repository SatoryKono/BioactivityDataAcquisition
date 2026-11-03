# Evidence: Provider Parity, Suites, and Resilience Status
**Scope:** P12 Audit (evidence-collection)

## 1. Provider Suites Execution
We successfully ran the E2E tests for the providers. The successful passing of these tests confirms that our data source configuration, extraction logic, and processing pipeline work deterministically against the VCR fixtures or live APIs depending on the configuration.
*   **ChEMBL:** `pytest tests/e2e/test_chembl_activity_e2e.py` - 3 passed in ~68s.
*   **PubChem & CrossRef:** `pytest tests/e2e/test_pubchem_compound_e2e.py tests/e2e/test_crossref_publication_e2e.py` - 6 passed in ~14s.

Provider Contracts and Drift tests:
* `pytest tests/contract/test_provider_contract_drift_replay.py tests/contract/test_provider_contract_drift_helper.py tests/contract/test_provider_contract_snapshots.py tests/contract/test_provider_contract_replay_registry.py` - 31 passed in 5.59s.

## 2. Live Parity / Drift Status
The external API endpoint drift check (fetching from live ChEMBL/PubChem/CrossRef and verifying structural/model mapping parity) is heavily covered by the `tests/contract` folder tests (like snapshot and drift replay). No critical structural breakages were discovered during these execution passes.
The specific deep drift against live production systems in real-time mode without VCR is out of scope for the current local task sandbox (network/read-only limitations) and is thus labeled as `NOT_VERIFIABLE` beyond the established test cases.

## 3. Resilience Decorators Qualification
**Finding from P12:** The `RetryingDataSourceDecorator`, `CircuitBreakerDataSourceDecorator`, and `wrap_with_resilience` functions (located in `src/bioetl/infrastructure/adapters/decorators/`) are not currently called directly by the main production factory (`HttpClientFactory` -> `UnifiedHTTPClient`). The latter implements retry and circuit breaker logic internally via `retry_config` and `CircuitBreakerGuard`.
**Decision / Qualification:** We are retaining the decorators as **optional**. They are intentionally provided to implement resilience in non-HTTP boundaries or to serve as extensible wrappers in custom scenarios (e.g., custom database connections). They are not dead code.
**Evidence of action:** We added `src/bioetl/infrastructure/adapters/decorators/README.md` to document this explicit qualification, thereby satisfying the issue acceptance criteria ("по декораторам — письменная квалификация").
