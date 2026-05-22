______________________________________________________________________

Version: 1.2.0
Status: archived
Class: historical
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-22'

______________________________________________________________________

# VCR Test Tasks

> **Status:** Historical verification artifact.
> This page no longer carries actionable VCR recording, refresh, or pruning
> tasks. Current VCR governance is generated and enforced through the canonical
> metadata catalog.

## Current Source Of Truth

Use these active surfaces instead of the retired manual task list:

- `reports/quality/vcr-metadata-catalog.json`
- `scripts/engineering/qa/report_vcr_metadata_catalog.py --check`
- `configs/quality/integration_vcr_policy.yaml`
- `configs/quality/test_matrix.yaml`
- `docs/03-guides/testing.md`
- `tests/architecture/test_vcr_metadata_catalog_drift.py`

The tracked catalog now records every cassette, its metadata sidecar, duplicate
stem status, reachability status, and owner path. Cassettes without direct or
generated test reachability remain explicitly classified as
`metadata_review_required`; unowned cassettes are a blocking governance failure.

## Retired Content

The previous revision of this page contained hand-maintained provider counts,
orphan lists, field-name anomaly tasks, and cassette refresh recommendations
generated on 2026-02-17. Those entries were intentionally retired because the
current cassette corpus and metadata catalog have moved beyond that snapshot.

Do not reopen tasks from this archived page directly. File new work from current
catalog evidence and link the exact catalog row, metadata sidecar, and owning
test path.
