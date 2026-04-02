# Provider Contract Snapshots

This directory stores provider-facing contract snapshot baselines referenced by
`configs/quality/test_matrix.yaml` via
`tests/fixtures/contracts/{provider}/v{version}.json`.

The current bounded publication rollout slice is declared in
`fixture_governance.contract_snapshot_registry` inside
`configs/quality/test_matrix.yaml`.

Current coverage:

- `crossref/v1.json`
- `openalex/v1.json`
- `semanticscholar/v1.json`

Update path:

- review intentional provider API contract changes first
- then run the targeted drift tests with `UPDATE_SNAPSHOTS=1`
- commit the updated snapshot files together with the contract test changes

These snapshots are intentionally narrower than the Silver schema snapshots:
they protect a minimal external provider payload shape, not the full transformed
schema surface.
