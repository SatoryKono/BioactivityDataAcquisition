# Coverage Tail And Branch Gate Plan

Generated for GitHub issue #5978 and follow-up issues #5980-#5983.

## Current Coverage State

Source: `reports/coverage/coverage.xml`

- Line rate: `95.88%`
- Branch rate: `85.002%`
- Branch threshold margin: `0` branch outcomes above the 85% threshold
- CI line gate: `coverage report --fail-under=85`
- Branch measurement: enabled in `pyproject.toml` via `branch = true`

Source: `reports/quality/module-coverage-inventory.json`

- Current inventory has no unmeasured or uncovered modules.
- The tail is now a partially-covered-module risk, not a zero-coverage risk.

Source: `reports/quality/branch-coverage-gap-report.json`

- `552` files remain below 85% branch coverage.
- The largest open branch gaps are now ranked in
  `reports/quality/branch-coverage-gap-report.md`.

## Branch Gate Decision

Promote the hard branch gate in the canonical `coverage-verify` lane. Branch
coverage is now at the existing 85% threshold and the promotion evidence is
captured in `reports/quality/branch-coverage-gate-evidence.json`. The gate uses
the existing threshold and does not increase any debt budget.

Branch policy:

- keep `branch = true` in `pyproject.toml`;
- keep the existing line gate at `85`;
- enforce branch rate with
  `python -m scripts.engineering.qa check-branch-coverage --coverage-xml reports/coverage/coverage.xml --min-percent 85`;
- keep adding focused branch/error-path tests for low-tail modules;
- use the branch gap report to keep burning down low-tail modules so the gate
  gains margin above the threshold.

## First Tail Slice

Target module: `src/bioetl/infrastructure/observability/tracing.py`

Reason: the module owns runtime exporter selection and env interpretation for
OpenTelemetry tracing. It has several branch-heavy paths that are cheap to test
without network or real collector dependencies.

Added/required test focus:

- OTLP endpoint host normalization;
- trace-specific env var priority over generic env vars;
- trace-specific insecure override priority;
- Console exporter fallback when OTLP is unavailable;
- explicit insecure override behavior for local endpoints;
- insecure override behavior without an endpoint.

## Required Checks

- Run `tests/unit/infrastructure/observability/test_tracing.py`.
- Run coverage inventory refresh/check after source changes.
- Run `python -m scripts.engineering.qa check-branch-coverage --coverage-xml reports/coverage/coverage.xml --min-percent 85`.
- Confirm `reports/quality/module-coverage-inventory.json` still has no
  unmeasured or uncovered modules.
- Track branch-rate trend after promotion to build margin above the hard gate.
