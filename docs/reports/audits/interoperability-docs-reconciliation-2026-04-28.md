# Documentation Audit Report (BioETL v5.23+)

## Summary

- Date: 2026-04-28
- Scope: README, provider/pipeline references, operator runbooks, export manifest docs, and provider-drift governance surfaces for issues #3212-#3218.
- Overall status: reconciled for the implemented interoperability refactor surfaces; remaining xwalk gaps are explicitly tracked through `configs/quality/xwalk_missing_backlog.yaml` and owner issue #3211.

## Inventory

- Docs scanned: 1726 files under `docs/`.
- Entry points: `README.md`, `mkdocs.yml`.

## Findings by severity

### Critical

- None found in the scoped reconciliation pass.

### High

- OpenAlex docs still contained email/polite-pool wording in active operator docs. Updated active references to API-key / credit-model wording and kept `BIOETL_OPENALEX_EMAIL` as attribution-only metadata.

### Medium

- UniProt docs needed clearer optional-key wording. Updated provider docs to reflect `auth_type: public` plus optional higher-throughput key behavior.
- Compact pipeline specs needed explicit references to the implemented ChEMBL publication identifiers, PubChem chemical standardization fields, and ChEMBL BAO/UO/QUDT companion IRI/version fields.
- Export docs needed a visible distinction between MIT code licensing and provider-specific dataset licensing. README, CLI, running guide, and API reference now document provenance, licensing, and checksum sidecars.
- Provider-drift governance needed operator-facing instructions. `docs/03-guides/testing.md` now documents the replay-only drift gate, xwalk backlog check, normalization matrix check, and snapshot refresh policy.

### Low

- Several version/date headers were stale on touched active docs. Updated touched pages to `2026-04-28`.

## Proposed changes (prioritized)

1. Keep provider-drift PR checks replay-only and use live contract tests only in the scheduled/manual workflow.
2. Treat unresolved xwalk `MISSING_*` markers as tracked backlog, not ambiguous documentation drift.
3. Continue documenting exported dataset licensing through sidecar manifests rather than implying MIT coverage for data outputs.

## Required decisions

- None for the implemented scope. Future removal of legacy OpenAlex `grants` output compatibility remains a separate schema/backward-compatibility decision.

## Updated files

- `README.md`
- `docs/03-guides/getting-started.md`
- `docs/03-guides/running-pipelines.md`
- `docs/03-guides/testing.md`
- `docs/04-reference/cli.md`
- `docs/04-reference/contracts/observability.md`
- `docs/04-reference/pipelines/README.md`
- `docs/04-reference/pipelines/chembl/05-activity-spec.md`
- `docs/04-reference/pipelines/openalex/01-publication-spec.md`
- `docs/04-reference/pipelines/pubchem/01-compound-spec.md`
- `docs/04-reference/providers/openalex/publication.md`
- `docs/04-reference/providers/uniprot/idmapping.md`
- `docs/04-reference/providers/uniprot/protein.md`
- `docs/04-reference/publication-validation-index.md`
- `docs/05-operations/deployment/deployment-guide.md`
- `docs/05-operations/runbooks/publication-validation-runbook.md`
- `docs/05-operations/verification/endpoint-validation-checklist.md`

## Dead or orphan docs (candidates)

- Not evaluated in this scoped reconciliation pass.

## Verification

- RULES.md and REQUIREMENTS.md sync: not changed in this scoped pass.
- ADR alignment: ADR-010 local-only and ADR-014 deterministic output assumptions preserved; provider-drift workflow remains replay/snapshot-only.
- Link check: strict docs build and generated artifact checks should be run as #3218 verification.
