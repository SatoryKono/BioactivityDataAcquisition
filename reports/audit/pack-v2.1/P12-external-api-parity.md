# P12. External API parity, resilience и provider contracts

## A. Audit Manifest
- **Audit ID**: pack-v2.1/P12
- **Pin Revision**: a5243cb4bbed67b267daecdc097b8c48501e140a
- **Scope**: provider adapters/clients + API models + extraction configs/tests
- **Sources of Truth**: Codebase (`src/bioetl/infrastructure/adapters/`), configurations, and explicit API contracts.
- **Exclusions/Not Verified**: Runtime external API verification is `NOT_VERIFIABLE` in `REPO_ONLY` mode. External assumptions regarding drift are not validated against live provider endpoints.
- **Evidence Mode**: `REPO_ONLY`

## B. Scope/Ownership and Exclusions
- **Primary Owner**: P12 (Provider contract parity, external resilience, deterministic fallback/provenance).
- **Secondary Owner**: External contract facts (input for P05).
- **Exclusions**: Live API endpoint tests and runtime fetching.

## C. Evidence Ledger
- `E2 STATIC`: `src/bioetl/infrastructure/adapters/` (codebase implementation of provider clients, models, and fallback logic).
  - `src/bioetl/infrastructure/adapters/chembl/client.py` (pagination, filtering, health checks)
  - `src/bioetl/infrastructure/adapters/pubchem/client.py` (sync pubchempy, health probe, circuit breaker)
  - `src/bioetl/infrastructure/adapters/crossref/client.py` (fallback resolver, pagination)
  - `src/bioetl/infrastructure/adapters/decorators/` (RetryingDataSourceDecorator, CircuitBreakerDataSourceDecorator)

## D. Findings Register
*(No actionable findings generated in REPO_ONLY scan beyond baseline mapping. See E for score).*

## E. Quantitative Scorecard
- **External API Parity, Resilience, and Provider Contracts**: 4
  - Сильная реализация, небольшие подтверждённые пробелы (missing live integration checks `NOT_VERIFIABLE` in this environment).
  - Explicit rate limits (`TokenBucketRateLimiter`), fallback resolution, resilient health checks (`CircuitBreakerGuard`), and typed API DTO validations are implemented across adapters (ChEMBL, PubChem, CrossRef, etc.).
  - Evidence: `E2 STATIC` codebase review.

## F. Cross-cutting/Root-cause Clusters
- N/A

## G. Prioritized Roadmap
- N/A

## H. Verification Matrix
- N/A

## I. NOT_VERIFIABLE and Missing Evidence
- **Missing Evidence**: Live endpoint verification against provider APIs (e.g., ChEMBL, PubChem, CrossRef) due to `REPO_ONLY` evidence mode. Drift checks for API models against current live provider responses cannot be verified statically.

## J. Self-check
- Assertions are restricted to repository evidence.
- No stale artifacts have been utilized.

## K. Verdict
- The provider adapters correctly implement retry (`RetryingDataSourceDecorator`), circuit breaker (`CircuitBreakerGuard`), rate limiting, and pagination policies. Fallback deterministic resolution is handled properly via custom fallbacks (e.g., CrossRef title-based fallback). External drift detection cannot be comprehensively performed without runtime integration tests. The scope is robust for a repository-only snapshot.

## Issue drafts
- Mapping: `N/A` (No issues to create based on this audit).
