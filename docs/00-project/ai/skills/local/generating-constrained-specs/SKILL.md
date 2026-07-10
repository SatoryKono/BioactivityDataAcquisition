> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/generating-constrained-specs/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: generating-constrained-specs
description: Use when generating PRD and architecture documents that must trace back to explicit decisions. Enforces citation requirements so no spec content exists without DEC-* references.
context: fork
agent: general-purpose
---

# Constrained Spec Generation

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`

## Core Principle

**No spec section without a DEC-* reference.**

Every requirement and architecture choice must trace back to an explicit
decision. See [references/constraint-rules.md](references/constraint-rules.md)
for detailed citation rules.

## Prerequisites

- Decisions complete (`/ledger-decide`)
- `04-decisions/DECISIONS.yaml` exists
- `05-risks/RISKS.yaml` exists

## Workflow

Use TodoWrite to track these mandatory steps:

<required>
1. Load decisions and risks
2. Generate PRD with decision citations
3. Validate PRD constraint gate
4. Generate architecture with decision citations
5. Validate architecture constraint gate
6. Cross-reference risks in both documents
</required>

### Step 1: Load Decisions and Risks

Read:
- `04-decisions/DECISIONS.yaml` - All decisions
- `05-risks/RISKS.yaml` - All risks
- `03-synthesis/CROSS-SYNTHESIS.md` - Context

Build decision index for quick lookup.

### Step 2: Generate PRD

Write `06-prd/PRD.md` using
[references/prd-template.md](references/prd-template.md). Every section and
requirement must cite `DEC-*`.

### Step 3: Validate PRD Constraint Gate

Use [references/constraint-rules.md](references/constraint-rules.md). Any PRD
section without a decision citation blocks completion.

### Step 4: Generate Architecture

Write `07-architecture/ARCHITECTURE.md` using
[references/architecture-template.md](references/architecture-template.md).
Every technical choice must cite `DEC-*`.

### Step 5: Validate Architecture Constraint Gate

Every architecture section must cite decisions and relevant `RISK-*` entries.

### Step 6: Cross-Reference Risks

In both documents, note relevant `RISK-*` entries and mitigation links.

## User Interaction

Use the **AskUserQuestion tool** when:

### Missing decision for section
```
Question: "PRD section '[X]' has no supporting decision. How to proceed?"
Options:
- "Skip this section (out of scope)"
- "Make a new decision for this"
- "It relates to existing decision [DEC-Y]"
```

### Decision conflict
```
Question: "Requirement '[X]' seems to conflict with [DEC-Y]. How to resolve?"
Options:
- "Revise requirement to align with decision"
- "The decision should be revisited"
- "They don't actually conflict - explain how"
```

### Risk acknowledgment
```
Question: "This section relates to [RISK-X]. Include risk note?"
Options:
- "Yes, note the risk"
- "No, not relevant here"
- "Yes, and add mitigation detail"
```

## Output

After spec generation:

```markdown
## Spec Generation Complete

**PRD Sections:** [N] (all constrained)
**Architecture Sections:** [M] (all constrained)
**Decisions Referenced:** [X] unique DEC-* IDs
**Risks Cross-Referenced:** [Y] RISK-* IDs

### Constraint Gate Status
- PRD gate: ✓ All sections cite decisions
- Architecture gate: ✓ All sections cite decisions

### Documents Generated
- `06-prd/PRD.md`
- `07-architecture/ARCHITECTURE.md`

### Decision Coverage
| Decision | PRD Sections | Arch Sections |
|----------|--------------|---------------|
| DEC-scope-power-users-first | 1, 2, 4 | 2, 3 |
| DEC-pricing-freemium | 3, 5 | 4 |
| DEC-tech-serverless | - | 1, 3, 5 |
| ... | ... | ... |

### Next Step
Run `/ledger-plan` to generate implementation backlog.
```

## References

- [references/constraint-rules.md](references/constraint-rules.md) - citation and gate rules
- [references/prd-template.md](references/prd-template.md) - PRD shape
- [references/architecture-template.md](references/architecture-template.md) - architecture shape
