"""Contract tests for external API providers.

These tests verify that external API contracts (schemas, endpoints, response formats)
haven't changed since the last verification.

Run with: pytest tests/contract/ -v

Environment:
    VCR replay drift checks under `tests/contract/test_provider_contract_drift_replay.py`
        are offline by default and read from `tests/fixtures/vcr/**`.
    BIOETL_LIVE_API_TESTS: Set to "true" to enable live API tests (or pass --live-api)
    BIOETL_NETWORK_TESTS: Set to "true" to opt into outbound network tests (or pass --network)
    BIOETL_PILOT_SOAK_TESTS: Set to "true" to enable richer pilot-only live suites
        (or pass --pilot-soak)
    UPDATE_SNAPSHOTS: Set to "1" only when intentionally rebaselining provider
        contract snapshots in `tests/fixtures/contracts/{provider}/v{version}.json`.

See:
    - RULES.md §4.2 for contract test policies
    - .github/workflows/provider-contract-drift.yml for PR/CI replay gate
    - .github/workflows/contract-tests.yml for CI configuration
    - tests/fixtures/contracts/README.md for provider snapshot registry guidance
"""
