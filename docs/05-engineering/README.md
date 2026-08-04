______________________________________________________________________

Version: 1.1.1
Status: active
Class: repo-only
Owner: BioETL Team
Last verified: '2026-08-04'

______________________________________________________________________

# Engineering Documentation (nav stub)

> **Classification:** repo-only stub (MkDocs `exclude_docs: 05-engineering/**`).
> Not a published SSOT. DOC-GOV-08 / #6888 / #7421.

**DOC-GOV-08 / #6888:** closeout and migration plans formerly under
`docs/05-engineering/` were archived to
[docs/99-archive/engineering/](../99-archive/engineering/).

## Purpose of this path

Keep a stable dual-lane marker (`05-operations` vs historical `05-engineering`)
so existing links do not 404. This directory is **not** an active engineering
SSOT.

## Where to go instead

| Need | Location |
| --- | --- |
| Architecture / layering | `docs/02-architecture/` |
| Operator runbooks | `docs/05-operations/runbooks/` |
| Active plans | `docs/plans/` (thin; one active backlog) |
| Test telemetry baseline | [test-telemetry-baseline.md](test-telemetry-baseline.md) |
| Historical engineering closeouts | `docs/99-archive/engineering/` |
| Normalization / control-plane history | archived engineering plans + ADRs 014/044 |

## Dual-lane note

- **`05-operations`** — published operational surface
- **`05-engineering`** — stub + archive pointer only (MkDocs excluded)

Do not add new long-form plans here; use `docs/plans/` (active) or archive.
