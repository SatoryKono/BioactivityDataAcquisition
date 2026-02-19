---
trigger: model_decision
description: USE WHEN managing VCR cassettes for integration and E2E tests.
---

vcr-policy

> Scope:
>
> - USE WHEN writing integration or E2E tests that perform HTTP requests.
> - USE WHEN organizing cassette files in `tests/fixtures/vcr/`.

# ORGANIZATION

- **Provider Folders**: Cassettes MUST be stored in provider-specific subdirectories:
  - `tests/fixtures/vcr/chembl/`
  - `tests/fixtures/vcr/uniprot/`
  - `tests/fixtures/vcr/multi_provider/` (for cross-provider tests)
- **Misplaced Files**: NEVER store cassettes in the project root or direct `tests/` directory.

# CONFIGURATION

- **Record Mode**:
  - `once`: Default for local development (allows initial recording).
  - `none`: Mandatory for CI (fails if cassette is missing/mismatched).
- **Sanitization**: Filter sensitive headers (`Authorization`, `X-API-Key`) and query parameters (`email`, `api_key`).
- **Matchers**: Use `method`, `scheme`, `host`, `port`, `path`, and `query` matchers. Use `query_ignore_email` for providers that include PII in URL.

# MAINTENANCE

- **Deterministic Tests**: Ensure tests provide the same parameters to the adapter every time to match the recorded cassette.
- **Cassette Rewriting**: If API response format changes, delete the old cassette and record a new one using `VCR_RECORD_MODE=all`.
- **Cleanup**: Unused cassettes SHOULD be removed to keep the repository clean.
