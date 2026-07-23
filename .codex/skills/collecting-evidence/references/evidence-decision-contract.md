# Evidence And Decision Contract

This is the shared contract for the BioETL-style evidence-to-decision skill
chain. Use it from `collecting-evidence`, `synthesizing-pillars`,
`making-decisions`, `initializing-ledger`, and
`hierarchical-evidence-orchestration`.

## Artifact Chain

| Stage | Skill | Required Output | Next Handoff |
| --- | --- | --- | --- |
| Ledger setup | `initializing-ledger` | `00-brief/BRIEF.md`, `01-pillars/PILLARS.md` | evidence collection |
| Evidence collection | `collecting-evidence` | `02-evidence/<pillar>/EV-*.yaml` | pillar synthesis |
| Pillar synthesis | `synthesizing-pillars` | `03-synthesis/SYN-<pillar>.md` | cross-synthesis or decisions |
| Hierarchical wave | `hierarchical-evidence-orchestration` | parent `ORCHESTRATION.md`, shard summaries, parent cross-synthesis | synthesis or decision work |
| Decisions | `making-decisions` | `04-decisions/DECISIONS.yaml`, `05-risks/RISKS.yaml` | constrained specs |

## Shared Rules

- Keep collection, synthesis, and decisions as separate phases.
- Use semantic IDs: `EV-*`, `SYN-*`, `DEC-*`, and `RISK-*`.
- Every synthesis insight must cite one or more `EV-*` IDs.
- Every accepted decision should cite supporting `EV-*` IDs and list at least
  one considered alternative.
- Risks created by decisions must link back to the creating `DEC-*`.
- Treat missing evidence as a gap, not as permission to invent rationale.
- Preserve contradictions explicitly until a user decision or stronger evidence
  resolves them.

## Evidence Object Minimum

`EV-*.yaml` must contain:

- `id`
- `pillar`
- `source.type`
- `source.ref`
- `source.retrieved_at`
- `claim`
- `confidence`
- `assumptions`

Use `collecting-evidence/references/evidence-object-schema.md` for the full
schema and example.

## Synthesis Minimum

`SYN-<pillar>.md` must contain:

- executive summary
- key insights with evidence citations
- contradictions and resolutions
- gaps and uncertainties
- recommended decisions

Use `synthesizing-pillars/references/synthesis-template.md` for the document
shape.

## Decision Minimum

`DECISIONS.yaml` entries must contain:

- semantic `DEC-*` id
- decision statement
- status
- owner
- created date
- alternatives considered
- evidence IDs
- wins and loses

Use `making-decisions/references/decision-ledger-schema.md` and
`making-decisions/references/risk-ledger-schema.md` for the detailed schemas.

## Hierarchical Wave Minimum

Parent evidence waves must keep child shard output roots disjoint and report:

- shard map
- shard evidence counts
- shard gate status
- synthesis status
- parent cross-synthesis status
- unresolved gaps

Use `hierarchical-evidence-orchestration/references/orchestration-contract.md`
for the parent artifact.
