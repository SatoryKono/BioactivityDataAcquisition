______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Composite Entity Pipelines (Reference)

Single reference page for composite entity configs (DOC-GOV-05 / #6885).

**Normative decision:** [ADR-026](../../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md)
**Code posture:** path-only composite stubs (entity registry validates paths;
runtime wiring remains composition-owned). Do not invent a second composite
provider layer in docs.

## Entity configs

| Entity | Config path |
| --- | --- |
| activity | `configs/entities/composite/activity.yaml` |
| assay | `configs/entities/composite/assay.yaml` |
| molecule | `configs/entities/composite/molecule.yaml` |
| publication | `configs/entities/composite/publication.yaml` |
| target | `configs/entities/composite/target.yaml` |

Shared composite policy surfaces:

- `configs/composites/**` — composite orchestration / merge policy YAML
- Entity contract facets under `configs/contracts/**` where applicable

## What composites are

Composite pipelines assemble **multi-provider** or **multi-source** views for a
business entity without replacing provider-native pipelines. They consume
already-governed Silver/Gold inputs and apply composite-specific merge,
identifier, and DQ policy described in ADR-026.

## What not to expect

- No five parallel “provider-style” deep specs under
  `docs/04-reference/providers/composite/` — one page + ADR-026 is enough.
- Composite entities are **not** a license to put I/O or provider clients in
  domain; adapters stay in infrastructure, DI in composition.
- Path-only registry stubs mean missing filesystem paths fail validation; they
  do not imply full runtime implementation for every composite name.

## Related docs

| Doc | Role |
| --- | --- |
| [ADR-026](../../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md) | Normative composite decision |
| [data-layers.md](../../02-architecture/data-layers.md) | Medallion storage semantics |
| [dq-configuration.md](../../03-guides/dq-configuration.md) | DQ multi-default thresholds |
| [contract-facet-matrix.md](contract-facet-matrix.md) | Contract facet coverage |
| Provider pipeline specs under `docs/04-reference/pipelines/` | Source entity pipelines |

## Operator entry

```bash
# List composite entity configs
ls configs/entities/composite/

# Validate configs via project quality/contract gates (see CI map)
# Prefer existing make/uv targets used in architecture and contract workflows.
```

When behavior is unclear, read **code + ADR-026 + entity YAML** before extending
narrative docs.
