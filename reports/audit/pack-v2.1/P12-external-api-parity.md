# P12. External API parity, resilience и provider contracts

## A. Audit Manifest
- **Audit ID**: pack-v2.1/P12
- **Pin Revision**: a5243cb4bbed67b267daecdc097b8c48501e140a
- **Scope**: provider adapters/clients + API models + extraction configs/tests
- **Sources of Truth**: Codebase (`src/bioetl/infrastructure/adapters/`, `src/bioetl/composition/factories/datasource/`), configurations, and explicit API contracts.
- **Exclusions/Not Verified**: Live provider endpoint / runtime drift checks are out of scope in `REPO_ONLY` mode (`Missing Evidence` — not a confirmed implementation defect).
- **Evidence Mode**: `REPO_ONLY`

## B. Scope/Ownership and Exclusions
- **Primary Owner**: P12 (Provider contract parity, external resilience, deterministic fallback/provenance).
- **Secondary Owner**: External contract facts (input for P05).
- **Exclusions**: Live API endpoint tests and runtime fetching.

## C. Evidence Ledger
- `E2 STATIC` (manual + targeted `rg`; no automated scanner suite run for this pack):
  - **Default HTTP wiring (production):** `HttpClientFactory._create_from_registry` → `UnifiedHTTPClient(..., circuit_breaker=CircuitBreakerGuard(...), retry_config=...)` in `src/bioetl/composition/factories/datasource/http_client.py`.
  - **PubChem path:** `src/bioetl/composition/factories/datasource/pubchem.py` constructs `CircuitBreakerGuard` and passes `retry_config` into the adapter client builders.
  - **Adapter clients:** `chembl/client.py`, `pubchem/client.py`, `crossref/client.py` (incl. `fetch_filtered_with_fallback` / `CrossRefFetchFlow`).
  - **Rate limit implementation:** `TokenBucketRateLimiter` in `src/bioetl/infrastructure/adapters/http/rate_limiter.py`.
  - **Optional decorator wrappers (available, not default HTTP factory path):** `RetryingDataSourceDecorator`, `CircuitBreakerDataSourceDecorator`, `wrap_with_resilience` under `src/bioetl/infrastructure/adapters/decorators/` — no production call sites outside that package on tip.
  - **Checks executed (exit 0):**
    - `rg -n -F --glob '*.py' -e 'class TokenBucketRateLimiter' -e 'class CircuitBreakerGuard' -e 'class RetryingDataSourceDecorator' -e 'class CircuitBreakerDataSourceDecorator' -e 'class HttpClientFactory' -e 'class UnifiedHTTPClient' src/bioetl`
    - `rg -n -F --glob '*.py' -e 'circuit_breaker=CircuitBreakerGuard' -e 'retry_config=' src/bioetl/composition/factories/datasource`
    - `rg -n -F --glob '*.py' -e 'RetryingDataSourceDecorator(' -e 'CircuitBreakerDataSourceDecorator(' -e 'wrap_with_resilience(' src/bioetl` excluding `**/decorators/**` → **no matches** (decorators not wired as default composition)
    - `rg -n -F --glob '*.py' -e 'fetch_filtered_with_fallback' -e 'CrossRefFetchFlow' src/bioetl/infrastructure/adapters/crossref src/bioetl/composition`
  - **Skipped:** live HTTP against ChEMBL/PubChem/CrossRef; full pytest provider suites; automated mkdocs/docs scan for this pack (handled by PR Docs lane separately).

## D. Findings Register
*(No actionable implementation defects confirmed from static REPO_ONLY evidence. See E for score; I for missing live evidence.)*

## E. Quantitative Scorecard
- **External API Parity, Resilience, and Provider Contracts**: 4
  - Strong static implementation of shared HTTP resilience and provider fallbacks; score limited by **доказательная база** (no live endpoint parity evidence in `REPO_ONLY`), not by a confirmed static defect.
  - Confirmed static paths: `TokenBucketRateLimiter`; factory-wired `CircuitBreakerGuard` + `retry_config` via `HttpClientFactory` / PubChem factory; CrossRef title/filter fallback via `CrossRefFetchFlow.fetch_filtered_with_fallback`.
  - Distinguish: `CircuitBreakerGuard` is the production circuit-breaker type on `UnifiedHTTPClient`; `CircuitBreakerDataSourceDecorator` / `RetryingDataSourceDecorator` are optional wrappers, not the default factory wiring.
  - Evidence: `E2 STATIC` (commands/results in section C).

## F. Cross-cutting/Root-cause Clusters
- N/A

## G. Prioritized Roadmap
- N/A

## H. Verification Matrix
- N/A

## I. NOT_VERIFIABLE and Missing Evidence
- **Missing Evidence** (`NOT_VERIFIABLE` in `REPO_ONLY`): Live endpoint verification against provider APIs (e.g., ChEMBL, PubChem, CrossRef). Drift checks for API models against current live provider responses cannot be verified statically. This is an evidence-base limitation, not a confirmed implementation defect.

## J. Self-check
- Assertions are restricted to repository evidence and the listed static commands.
- No stale artifacts have been utilized.
- Decorator types are not cited as proof of default HTTP adapter assembly.

## K. Verdict
- Default HTTP adapters are assembled through `HttpClientFactory` → `UnifiedHTTPClient` with `CircuitBreakerGuard` and `retry_config` (plus rate limiting via shared HTTP resources). PubChem follows the same `CircuitBreakerGuard` / retry-config pattern in its datasource factory. CrossRef deterministic fallback is present via `CrossRefFetchFlow` / `fetch_filtered_with_fallback`. Optional `RetryingDataSourceDecorator` / `CircuitBreakerDataSourceDecorator` exist but are not the default composition path. Live external drift detection remains `Missing Evidence` without runtime integration checks. Scope is robust for a repository-only snapshot.

## Issue drafts
- Mapping: `N/A` (No issues to create based on this audit).
