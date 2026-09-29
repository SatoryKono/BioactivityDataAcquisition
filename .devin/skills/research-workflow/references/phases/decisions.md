# Phase: decisions

> Router: `research-workflow --phase decisions`. This file holds the phase
> body for the single `research-workflow` router skill (`../SKILL.md`).
> Do not promote it to a standalone skill.

## When to Use
- Transforming synthesis insights into explicit decisions
- Making documented trade-offs between options
- Creating decision ledger with risk identification

## Prerequisites
- Synthesis complete (Phase 3)
- `03-synthesis/CROSS-SYNTHESIS.md` exists with decision candidates
- Per-pillar syntheses in `03-synthesis/SYN-*.md`

## Workflow Steps

<required>
1. Load decision candidates from cross-synthesis
2. For each candidate, gather evidence and options
3. Present trade-offs for user decision
4. Create decision entry with semantic ID
5. Identify risks created by each decision
6. Generate DECISIONS.yaml and RISKS.yaml
7. Validate decision quality gates
</required>

## Decision Entry Schema

```yaml
- id: DEC-scope-smb-first
  decision: "Target SMB segment before enterprise"
  status: accepted
  owner: user
  created_at: 2026-01-21
  alternatives:
    - Enterprise-first
    - Multi-segment simultaneous
  evidence:
    - EV-users-smb-pain-points
    - EV-economics-smb-unit-economics
    - EV-market-enterprise-tam
  tradeoffs:
    wins:
      - "Faster iteration cycles with smaller customers"
      - "Lower sales friction (self-serve possible)"
      - "Better unit economics at start"
    loses:
      - "Smaller initial contract values"
      - "May need significant pivot for enterprise later"
  risks:
    - RISK-market-smb-churn-rate
  implications:
    - "MVP UX must optimize for self-serve onboarding"
    - "Pricing must fit SMB budget constraints"
```

## Quality Gates

**Decision quality gate:**
- Every decision cites ≥2 evidence IDs
- Every decision lists ≥1 alternative considered
- Every decision documents wins AND loses

**Risk quality gate:**
- Every risk links to creating decision
- Every risk has severity and likelihood
- Every risk has ≥1 mitigation

## Output

```markdown
## Decisions Complete

**Decisions Made:** [N]
**Status:** [X] accepted, [Y] provisional
**Risks Identified:** [Z]

### Decisions Summary
| ID | Decision | Status | Evidence Count |
|----|----------|--------|----------------|
| DEC-scope-smb-first | Target SMB first | accepted | 4 |

### Risks Created
| ID | Risk | Severity | Linked Decision |
|----|------|----------|-----------------|
| RISK-market-smb-churn | SMB churn rate | medium | DEC-scope-smb-first |
```

See also: [../decision-ledger-schema.md](../decision-ledger-schema.md),
[../risk-ledger-schema.md](../risk-ledger-schema.md),
[../evidence-decision-contract.md](../evidence-decision-contract.md).
