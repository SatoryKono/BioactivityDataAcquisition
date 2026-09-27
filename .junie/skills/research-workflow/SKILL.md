---
name: research-workflow
description: "Use for structured research, deep investigation, traceable evidence, and multi-stream synthesis with explicit decisions and constrained specifications. Single router: select work via --phase initialize|evidence|synthesis|decisions|specs|complete; phase bodies live in references/phases/."
context: fork
agent: general-purpose
---

# Research Workflow (router)

## Source Of Truth
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`

This skill is the single router for structured research, deep
investigation, traceable evidence, and multi-stream synthesis. It replaces the
retired `deep-research`, `collecting-evidence`, and
`hierarchical-evidence-orchestration` routes. Use `mode=single` by default and
`mode=multi-stream` only when the task genuinely benefits from independent
evidence streams.

Do **not** create phase-specific skills: one `research-workflow` skill serves
all phases through `--phase`, the same way `py-test-bot` serves
`mode=focused|broad` from one `SKILL.md`.

## Phase Index

| `--phase` | Stage | Phase file | Output |
| --- | --- | --- | --- |
| `initialize` | Workspace from brief | [references/phases/initialize.md](references/phases/initialize.md) | `BRIEF.md`, `PILLARS.md`, ledger dirs |
| `evidence` | Evidence per pillar | [references/phases/evidence.md](references/phases/evidence.md) | `EV-*` objects, evidence gate |
| `synthesis` | Insights from evidence | [references/phases/synthesis.md](references/phases/synthesis.md) | `SYN-*.md`, contradiction log |
| `decisions` | Explicit decisions | [references/phases/decisions.md](references/phases/decisions.md) | `DECISIONS.yaml`, `RISKS.yaml` |
| `specs` | Constrained specs | [references/phases/specs.md](references/phases/specs.md) | `PRD.md`, `ARCHITECTURE.md` (DEC-*-cited) |
| `complete` | All phases in order | run the five files above in order | full ledger |

## Router Workflow

1. Resolve scope and confirm this router (not a phase skill) is the entrypoint.
2. Read the phase file for the requested `--phase` (`complete` = all five, in order).
3. Apply that file's Workflow Steps, schemas, and gates; do not invent inputs
   a phase's Prerequisites declare missing.
4. Produce the phase Output; state gate status explicitly.

## Validation (gates per phase)

- `initialize`: brief parsed into components; ledger dirs, `BRIEF.md`, and
  `PILLARS.md` exist.
- `evidence`: ≥5 Evidence Objects per pillar; every object passes the quality
  gates (falsifiable claim, confidence, ≥1 assumption, traceable source,
  semantic ID).
- `synthesis`: insights link `EV-*` IDs; contradictions resolved or flagged
  for decisions.
- `decisions`: every decision cites ≥2 evidence IDs and ≥1 alternative and
  documents wins AND loses; every risk links its decision and has severity,
  likelihood, and ≥1 mitigation.
- `specs`: no spec section without a `DEC-*` reference (PRD + architecture
  constraint gates).

## Fallback

- Unknown `--phase`: list the Phase Index above and stop.
- Missing prerequisites (e.g. `--phase evidence` without a ledger): run or
  request the earlier phase first; do not invent pillar scope.
- Incomplete brief: state assumptions and mark decisions that require user
  input before implementation.

## User Interaction

Use the **AskUserQuestion tool** at key decision points:

### Phase 1 (Initialize)
- Brief ambiguity clarification
- Missing critical information
- Pillar prioritization
- Custom workspace path

### Phase 2 (Evidence)
- Source prioritization
- Confidence assessment
- Contradictory evidence handling
- Evidence gate failures

### Phase 3 (Synthesis)
- Contradiction resolution
- Insight interpretation
- Gap identification

### Phase 4 (Decisions)
- Decision selection among options
- Trade-off confirmation
- Decision status (accepted/provisional)
- Risk severity assessment

### Phase 5 (Specs)
- Missing decision for section
- Decision conflict resolution
- Risk acknowledgment

## Usage Examples

### Start New Research Project
```
skill research-workflow --phase initialize
```

### Collect Evidence for Specific Pillar
```
skill research-workflow --phase evidence --pillar market
```

### Synthesize Evidence into Insights
```
skill research-workflow --phase synthesis --pillar market
```

### Make Explicit Decisions
```
skill research-workflow --phase decisions
```

### Generate Constrained Specifications
```
skill research-workflow --phase specs
```

### Run Complete Workflow
```
skill research-workflow --phase complete
```

## References

- [references/phases/initialize.md](references/phases/initialize.md) - Phase router: workspace init
- [references/phases/evidence.md](references/phases/evidence.md) - Phase router: evidence collection
- [references/phases/synthesis.md](references/phases/synthesis.md) - Phase router: synthesis
- [references/phases/decisions.md](references/phases/decisions.md) - Phase router: decisions and risks
- [references/phases/specs.md](references/phases/specs.md) - Phase router: constrained specs
- [references/evidence-object-schema.md](references/evidence-object-schema.md) - Evidence YAML schema
- [references/synthesis-template.md](references/synthesis-template.md) - Synthesis document template
- [references/decision-ledger-schema.md](references/decision-ledger-schema.md) - DECISIONS.yaml schema
- [references/risk-ledger-schema.md](references/risk-ledger-schema.md) - RISKS.yaml schema
- [references/prd-template.md](references/prd-template.md) - PRD template
- [references/architecture-template.md](references/architecture-template.md) - Architecture template
- [references/constraint-rules.md](references/constraint-rules.md) - Detailed constraint rules
- [references/brief-template.md](references/brief-template.md) - BRIEF.md template
- [references/pillar-definitions.md](references/pillar-definitions.md) - Pillar definitions and scope
- [references/id-generation-rules.md](references/id-generation-rules.md) - Semantic ID creation
- [references/research-protocols.md](references/research-protocols.md) - Pillar-specific research guidance
