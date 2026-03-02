"""Contract tests for external API providers.

These tests verify that external API contracts (schemas, endpoints, response formats)
haven't changed since the last verification.

Run with: pytest tests/contract/ -v

Environment:
    BIOETL_LIVE_API_TESTS: Set to "true" to enable live API tests (required)

See:
    - RULES.md §4.2 for contract test policies
    - .github/workflows/contract-tests.yml for CI configuration
"""
