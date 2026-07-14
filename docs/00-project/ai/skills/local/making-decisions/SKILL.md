> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/making-decisions/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "making-decisions"
description: "Use when transforming synthesis insights into explicit decisions with documented trade-offs. Guides interactive decision-making and risk identification."
context: "fork"
agent: "general-purpose"
---

# Decision Ledger

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`

- Shared evidence/decision contract: [../collecting-evidence/references/evidence-decision-contract.md](../collecting-evidence/references/evidence-decision-contract.md)

This skill creates explicit decisions with evidence, alternatives, trade-offs,
and linked risks.

## Prerequisites

- Synthesis complete (`/ledger-synthesize`)
- `03-synthesis/CROSS-SYNTHESIS.md` exists with decision candidates
- Per-pillar syntheses in `03-synthesis/SYN-*.md`

## Workflow

Use TodoWrite to track these mandatory steps:

<required>
1. Load decision candidates from cross-synthesis
2. For each candidate, gather evidence and options
3. Present trade-offs for user decision
4. Create decision entry with semantic ID
5. Identify risks created by each decision
6. Generate DECISIONS.yaml and RISKS.yaml
7. Validate decision quality gates
</required>

### Step 1: Load Decision Candidates

Read `03-synthesis/CROSS-SYNTHESIS.md` to extract:

- Decision topics needing resolution
- Supporting evidence from each pillar
- Identified options

### Step 2: Gather Evidence per Decision

For each decision candidate:

- Collect all relevant EV-\* IDs
- Summarize what evidence supports each option
- Note confidence levels

```yaml
decision_candidate:
  topic: target-segment-priority
  options:
    - name: SMB-first
      evidence:
        - EV-users-smb-pain-points (0.80)
        - EV-economics-smb-unit-economics (0.75)
    - name: Enterprise-first
      evidence:
        - EV-market-enterprise-tam (0.85)
        - EV-competitors-enterprise-gap (0.70)
```

### Step 3: Present Trade-offs

For each decision, present:

- Options with evidence support
- What you win with each option
- What you lose with each option
- Risks created by each option

Use **AskUserQuestion** to get user's decision.

### Step 4: Create Decision Entry

Write entries to `04-decisions/DECISIONS.yaml` using
[references/decision-ledger-schema.md](references/decision-ledger-schema.md).
Each decision must use a semantic `DEC-*` ID, cite evidence, list alternatives,
and document both wins and loses.

### Step 5: Identify Created Risks

Each decision may create risks. For each identified risk:

- Create entry in `05-risks/RISKS.yaml`
- Link back to creating decision
- Document triggers and mitigations

See [references/risk-ledger-schema.md](references/risk-ledger-schema.md) for schema.

### Step 6: Generate Ledger Files

Write complete files:

- `04-decisions/DECISIONS.yaml`
- `05-risks/RISKS.yaml`

### Step 7: Validate Quality Gates

**Decision quality gate:**

- Every decision cites ≥2 evidence IDs
- Every decision lists ≥1 alternative considered
- Every decision documents wins AND loses

**Risk quality gate:**

- Every risk links to creating decision
- Every risk has severity and likelihood
- Every risk has ≥1 mitigation

## User Interaction

Use the **AskUserQuestion tool** for every decision:

### Decision prompt

```
Question: "Decision needed: [topic]"
Options:
- "[Option A] - supported by [evidence summary]"
- "[Option B] - supported by [evidence summary]"
- "[Option C] - supported by [evidence summary]"
- "Need more information before deciding"
```

### Trade-off confirmation

```
Question: "You chose [option]. Confirming trade-offs:"
Options:
- "Yes, I accept these trade-offs"
- "Wait, I want to reconsider"
- "Explain the trade-offs more"
```

### Decision status

```
Question: "Should this decision be marked as:"
Options:
- "Accepted (committed)"
- "Provisional (may revisit)"
- "Need more research first"
```

### Risk severity

```
Question: "This decision creates risk: [risk]. How severe?"
Options:
- "High - requires immediate mitigation"
- "Medium - should have mitigation plan"
- "Low - acceptable risk"
```

## Output

After decision-making:

```markdown
## Decisions Complete

**Decisions Made:** [N]
**Status:** [X] accepted, [Y] provisional
**Risks Identified:** [Z]

### Decisions Summary
| ID | Decision | Status | Evidence Count |
|----|----------|--------|----------------|
| DEC-scope-smb-first | Target SMB first | accepted | 4 |
| DEC-pricing-freemium | Use freemium model | provisional | 3 |
| ... | ... | ... | ... |

### Risks Created
| ID | Risk | Severity | Linked Decision |
|----|------|----------|-----------------|
| RISK-market-smb-churn | SMB churn rate | medium | DEC-scope-smb-first |
| ... | ... | ... | ... |

### Quality Gate Status
- Decision gate: ✓ All decisions cite ≥2 evidence
- Risk gate: ✓ All risks have mitigations

### Next Step
Run `/ledger-spec` to generate constrained PRD and architecture.
```

## References

- [references/decision-ledger-schema.md](references/decision-ledger-schema.md) - DECISIONS.yaml schema
- [references/risk-ledger-schema.md](references/risk-ledger-schema.md) - RISKS.yaml schema
- [../collecting-evidence/references/evidence-decision-contract.md](../collecting-evidence/references/evidence-decision-contract.md) - shared chain contract
