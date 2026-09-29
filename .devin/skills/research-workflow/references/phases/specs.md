# Phase: specs

> Router: `research-workflow --phase specs`. This file holds the phase body
> for the single `research-workflow` router skill (`../SKILL.md`). Do not
> promote it to a standalone skill.

## When to Use
- Generating PRD and architecture documents
- Ensuring all spec content traces back to explicit decisions
- Creating constrained specifications with decision citations

## Prerequisites
- Decisions complete (Phase 4)
- `04-decisions/DECISIONS.yaml` exists
- `05-risks/RISKS.yaml` exists

## Core Principle

**No spec section without a DEC-* reference.**

Every requirement, every architecture choice, must trace back to an explicit decision.

## Workflow Steps

<required>
1. Load decisions and risks
2. Generate PRD with decision citations
3. Validate PRD constraint gate
4. Generate architecture with decision citations
5. Validate architecture constraint gate
6. Cross-reference risks in both documents
</required>

## Citation Format

**Section headings:**
```markdown
## 2. MVP Scope (DEC-scope-power-users-first, DEC-scope-web-only)
```

**Inline citations:**
```markdown
Users will access the application via web browser only. (DEC-scope-web-only)
```

**Evidence when needed:**
```markdown
Based on user research showing 78% onboarding drop-off at team invitation
(EV-users-onboarding-dropoff), we will simplify the invitation flow.
(DEC-ux-simplified-onboarding)
```

## Constraint Gates

Check every PRD section:
- [ ] Section heading has DEC-* reference
- [ ] Requirements cite supporting decisions
- [ ] Risks are cross-referenced where relevant

Check every architecture section:
- [ ] Section heading has DEC-* reference
- [ ] Technical choices cite supporting decisions
- [ ] Risks are cross-referenced where relevant

## Output

```markdown
## Spec Generation Complete

**PRD Sections:** [N] (all constrained)
**Architecture Sections:** [M] (all constrained)
**Decisions Referenced:** [X] unique DEC-* IDs
**Risks Cross-Referenced:** [Y] RISK-* IDs

### Documents Generated
- `06-prd/PRD.md`
- `07-architecture/ARCHITECTURE.md`
```

See also: [../prd-template.md](../prd-template.md),
[../architecture-template.md](../architecture-template.md),
[../constraint-rules.md](../constraint-rules.md).
