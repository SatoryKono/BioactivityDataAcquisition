______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Tutorial: Create a New Pipeline in 15 Minutes

**Issue:** #6539
**Audience:** developers adding an entity for an **existing** provider
**Normative SSOT:** [add-pipeline-existing-source.md](../add-pipeline-existing-source.md),
[pipeline-config cheatsheet](../cheatsheets/pipeline-config.md), ADR-005 / ADR-014 / ADR-018

> Timed walkthrough. Full checklists live in the linked guides.

## Prerequisites (before the clock)

1. Local bootstrap: [getting-started.md](../getting-started.md) / [quick-start.md](../quick-start.md).
2. Provider already integrated (adapters + HTTP client exist).
3. Known provider/entity slugs.
4. Medallion basics: [data-layers.md](../../02-architecture/data-layers.md).

## 0–3 min — Domain contract and schema

1. Add/extend Silver Pandera schema under `src/bioetl/domain/schemas/{provider}/`.
2. Add/extend Gold contract under `src/bioetl/domain/contracts/gold/`.
3. Export only where existing family packages require it.
4. Domain stays **I/O-free** (RULES §1).

## 3–7 min — Transformer

1. Prefer application transformer under
   `src/bioetl/application/pipelines/{provider}/…`.
2. Reuse family FieldSpec / profile mapping patterns.
3. Normalization lives in **domain normalization profiles**, not ad-hoc adapter strings.
4. Composition owns DI registration — never wire adapters from domain.

## 7–10 min — Config

Create `configs/entities/{provider}/{entity}.yaml`:

- pipeline id / provider / entity
- extract source settings (reuse provider defaults)
- Silver + Gold sinks with **`sort_by`** (ADR-014 — common pitfall)
- `quality:` hierarchy or intentional inherit from base
- filters only when justified

## 10–12 min — Composition registration

1. Register transformer in composition factory / pipeline registry.
2. Confirm entity config path resolves in registry validation.
3. Never put factories in domain/application beyond established patterns.

## 12–15 min — Tests and smoke

1. Unit-test mapping with a tiny fixture.
2. HTTP tests: VCR under governed `tests/fixtures/vcr` policy.
3. Local smoke with project CLI (see CLI cheatsheet).
4. Confirm Bronze append + Silver Delta under `data/output/…`.

## Common pitfalls

| Pitfall | Fix |
| --- | --- |
| Missing `sort_by` | ADR-014 deterministic writes |
| Domain imports infrastructure | Forbidden — ports only |
| Raising DQ thresholds to go green | Evidence gate in dq docs — not a local “fix” |
| Composite treated as provider | [composites.md](../../04-reference/pipelines/composites.md) |

## Done checklist

- [ ] Entity YAML + schemas + transformer + composition registration
- [ ] Tests + cassette policy respected
- [ ] Local run produces Bronze/Silver artifacts
