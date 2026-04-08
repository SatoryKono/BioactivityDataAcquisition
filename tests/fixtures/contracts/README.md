# Provider Contract Snapshots

This directory stores provider-facing contract snapshot baselines referenced by
`configs/quality/test_matrix.yaml` via
`tests/fixtures/contracts/{provider}/v{version}.json`.

The current bounded live-provider baseline is declared in
`fixture_governance.contract_snapshot_registry` inside
`configs/quality/test_matrix.yaml`.

Current coverage:

- `chembl/v1.json`
- `crossref/v1.json`
- `openalex/v1.json`
- `pubchem/v1.json`
- `pubmed/v1.json`
- `semanticscholar/v1.json`
- `uniprot/v1.json`

Update path:

- review intentional provider API contract changes first
- then run the targeted drift tests with `UPDATE_SNAPSHOTS=1`
- commit the updated snapshot files together with the contract test changes

These snapshots are intentionally narrower than the Silver schema snapshots:
they protect a minimal external provider payload shape, not the full transformed
schema surface.

Replay usage:

- PR/CI replay gate reads the current snapshots via
  `tests/contract/_provider_contract_drift.py`
- replay payloads come from curated VCR cassettes under `tests/fixtures/vcr/**`
- scheduled/manual live verification remains in `.github/workflows/contract-tests.yml`
  and revalidates the same provider-facing probes against the network

Recommended maintenance pattern:

- prefer stable JSON probes over XML-heavy endpoints for the managed slice
- freeze only a few high-signal path/type expectations per probe
- avoid full-payload snapshots when a smaller provider-facing shape contract is
  enough to detect meaningful drift
- reuse existing provider VCR cassettes when possible; add dedicated replay
  cassettes only for probes that are otherwise uncovered
