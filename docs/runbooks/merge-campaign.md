# Runbook: Merge Campaign for Consolidation

This runbook outlines the steps for executing the BioETL consolidation merge campaign safely.

## Phase 1: Freeze Baseline

1. Cut the consolidation branch from `main`:
   ```bash
   git checkout main
   git checkout -b consolidation/2026-05-campaign
   ```
2. Run standard local bootstrap and snapshot:
   ```bash
   make install
   make test-deps
   make setup-plugins
   uv sync --locked --all-extras --dev
   ```

## Phase 2: Architecture & Gold Contracts Gate

Before accepting any PR into the campaign branch, run the core architecture and regression suite:
```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pytest tests/architecture/test_ci_test_strategy.py -q
uv run pytest tests/architecture/test_config_golden_master.py -q
uv run pytest tests/architecture/test_gold_schema_contracts.py -q
uv run pytest tests/architecture/test_medallion_invariants.py -q
uv run pytest tests/architecture/test_explicit_gold_scd2_policy.py -q
uv run pytest tests/architecture/test_no_random_in_writers.py -q
uv run pytest tests/architecture/test_no_datetime_now_in_infrastructure.py -q
uv run pytest tests/architecture/test_no_structlog_in_application_interfaces.py -q
uv run pytest tests/architecture/test_lock_safety_guard.py -q
uv run pytest tests/architecture/test_metadata_output_contract.py -q
uv run pytest tests/architecture/test_provider_regression_matrix.py -q
uv run pytest tests/contract -q
uv run pytest tests/smoke -q
uv run pytest tests/snapshots -q
```

## Phase 3: PR Rebase & Integration

For each PR anchor (e.g., #4728, #4727, #4738):
1. Rebase the PR onto `consolidation/2026-05-campaign`.
2. Re-run Phase 2 gates.
3. Validate deterministic output and idempotency.
   ```bash
   uv run pytest tests/integration/determinism -q
   uv run pytest tests/integration/idempotency -q
   uv run pytest tests/integration/composite_resume -q
   ```
4. Merge or squash PR into the campaign branch.

## Phase 4: Stale PR Triage

Evaluate stale PRs (e.g., #4590):
- If the PR contains unique changes not covered by the campaign, cherry-pick them into a new branch.
- If redundant, close as `superseded`.

## Phase 5: Mainline Merge

Once the campaign branch is complete and green:
- Add the campaign branch to the merge queue for `main`.
- Ensure squash merge.
