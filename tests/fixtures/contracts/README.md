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
- inspect the current drift report before changing snapshots:
  `python -m scripts.engineering.qa report-provider-contract-drift`
- update only the affected provider/probe snapshots with `UPDATE_SNAPSHOTS=1`
- commit the updated snapshot files together with the contract test changes
- document why the provider-facing shape change is acceptable before merging

These snapshots are intentionally narrower than the Silver schema snapshots:
they protect a minimal external provider payload shape, not the full transformed
schema surface.

Replay usage:

- PR/CI replay gate reads the current snapshots via
  `tests/contract/_provider_contract_drift.py`
- replay payloads come from curated VCR cassettes under `tests/fixtures/vcr/**`
- replay mode is expected to run without live network and without default API
  credentials
- scheduled/manual live verification remains in `.github/workflows/contract-tests.yml`
  and revalidates the same provider-facing probes against the network

Required env var and network policy:

- snapshot refresh is opt-in via `UPDATE_SNAPSHOTS=1`
- default provider-contract replay checks must remain offline
- live provider contract verification is opt-in and stays isolated in
  `.github/workflows/contract-tests.yml`
- `.github/workflows/provider-contract-drift.yml` is the replay/snapshot gate and
  must not become a second live-network workflow

Recommended maintenance pattern:

- prefer stable JSON probes over XML-heavy endpoints for the managed slice
- freeze only a few high-signal path/type expectations per probe
- avoid full-payload snapshots when a smaller provider-facing shape contract is
  enough to detect meaningful drift
- reuse existing provider VCR cassettes when possible; add dedicated replay
  cassettes only for probes that are otherwise uncovered
