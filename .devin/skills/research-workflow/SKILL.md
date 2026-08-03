---
name: research-workflow
description: "Use when conducting structured research projects that require traceable evidence, explicit decisions, and constrained specifications. Covers the full workflow from initialization through evidence collection, synthesis, decision-making, and spec generation."
context: fork
agent: general-purpose
---

# Research Workflow

## Source Of Truth
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`

This skill provides a unified workflow for structured research projects that require traceable evidence and explicit decisions. It combines evidence collection, synthesis, decision-making, and spec generation into a coherent process.

## Workflow Phases

The research workflow consists of 5 sequential phases:

1. **Initialize** - Create workspace structure from project brief
2. **Evidence** - Collect traceable evidence objects for research pillars
3. **Synthesis** - Transform evidence into structured insights
4. **Decisions** - Make explicit decisions with documented trade-offs
5. **Specs** - Generate constrained PRD and architecture documents

## Phase 1: Initialize

### When to Use
- Starting a new product development project
- Beginning a research initiative that needs traceable evidence
- Creating a workspace for explicit decision-making

### Prerequisites
- User must provide a project brief (text description of what they're building)
- Optionally: custom path for ledger workspace (default: `./ledger/`)

### Workflow Steps

<required>
1. Parse the brief into structured components
2. Validate brief completeness (goals, constraints identifiable)
3. Create directory structure
4. Generate BRIEF.md
5. Generate PILLARS.md with default configuration
6. Confirm initialization complete
</required>

### Brief Validation

Extract from the user's input:

| Component        | Description                         | Required    |
| ---------------- | ----------------------------------- | ----------- |
| **Core idea**    | What is being built (1-2 sentences) | Yes         |
| **Target users** | Who will use this                   | Yes         |
| **Key goals**    | What success looks like             | Yes         |
| **Constraints**  | What's explicitly out of scope      | Recommended |
| **Context**      | Any domain-specific information     | Optional    |

### Directory Structure

```bash
mkdir -p ledger/{00-brief,01-pillars}
mkdir -p ledger/02-evidence/{market,users,tech,competitors,design,legal,ops,economics}
mkdir -p ledger/{03-synthesis,04-decisions,05-risks,06-prd,07-architecture,08-plan,09-brand,10-gtm-ops}
```

### Output

```markdown
## Ledger Initialized

**Path:** ./ledger/
**Brief:** [2-3 sentence summary]

**Pillar Priorities:**
1. [High priority pillars]
2. [Medium priority pillars]
3. [Lower priority pillars]

**Next step:** Run research workflow with --phase evidence
```

## Phase 2: Evidence

### When to Use
- Researching a specific pillar and need to create traceable evidence objects
- Building evidence base for decision-making
- Conducting structured research with confidence scoring

### Prerequisites
- Ledger workspace initialized (Phase 1 complete)
- Pillar assignment (which pillar to research)
- Research scope from `01-pillars/PILLARS.md`

### Workflow Steps

<required>
1. Load pillar scope and research questions
2. Identify evidence sources
3. Collect raw evidence
4. Create Evidence Objects with semantic IDs
5. Validate evidence quality
6. Check evidence gate (minimum 5 per pillar)
</required>

### Evidence Sources

| Source Type    | Examples                        | Typical Confidence |
| -------------- | ------------------------------- | ------------------ |
| `url`          | Research reports, documentation | 60-90              |
| `pdf`          | Academic papers, whitepapers    | 70-95              |
| `interview`    | User interviews, expert calls   | 50-80              |
| `internal-doc` | Company data, prior research    | 60-85              |
| `experiment`   | A/B tests, prototypes           | 70-95              |
| `dataset`      | Analytics, survey results       | 65-90              |

### Evidence Object Schema

```yaml
id: EV-market-pricing-smb-wtp
pillar: market
source:
  type: url
  ref: "https://example.com/pricing-research"
  retrieved_at: 2026-01-21
claim: "SMB segment willingness-to-pay peaks at $29/mo for productivity tools."
quote: "Our survey of 500 SMBs found median WTP of $29/month..."
confidence: 0.75
assumptions:
  - "Survey sample representative of target market"
  - "WTP for 'productivity tools' applies to our specific category"
notes: "Sample skewed toward US companies. May need regional validation."
tags:
  - pricing
  - smb
  - wtp
```

### Quality Gates

Each Evidence Object must pass:

| Check               | Requirement               |
| ------------------- | ------------------------- |
| Falsifiable claim   | Claim can be proven wrong |
| Confidence assigned | 0.0-1.0 value present     |
| Assumptions listed  | At least 1 assumption     |
| Source traceable    | Can revisit the source    |
| ID is semantic      | Follows ID scheme         |

**Evidence Gate:** Minimum 5 Evidence Objects per pillar before proceeding to synthesis.

### Output

```markdown
## Evidence Collection Complete: [pillar]

**Evidence Objects Created:** [N]
**Gate Status:** [PASSED/FAILED]

### Evidence Summary
| ID | Claim Summary | Confidence |
|----|---------------|------------|
| EV-market-tam-b2b-saas | TAM is $X billion | 0.80 |
| EV-market-pricing-smb-wtp | SMB WTP peaks at $29/mo | 0.75 |
```

## Phase 3: Synthesis

### When to Use
- Evidence collection is complete for a pillar
- Need to extract actionable insights from raw evidence
- Transforming evidence into structured synthesis

### Prerequisites
- Evidence gate passed (≥5 evidence objects for this pillar)
- Evidence objects in `02-evidence/<pillar>/`

### Workflow Steps

<required>
1. Load all evidence objects for the pillar
2. Identify patterns and themes
3. Resolve or document contradictions
4. Extract key insights
5. Generate synthesis document
6. Link insights to evidence IDs
</required>

### Pattern Identification

Group evidence by theme:
- What claims cluster together?
- What topics have multiple evidence points?
- What themes emerge across sources?

### Insight Structure

```yaml
insight: "SMB segment has price sensitivity ceiling at $30/mo"
observation: "Multiple sources confirm $29-30 WTP peak"
implication: "Pricing above $30 requires enterprise features"
confidence: 0.75
evidence:
  - EV-market-pricing-smb-wtp
  - EV-competitors-pricing-benchmark
```

### Contradiction Handling

For contradictory evidence:
1. Note the contradiction explicitly
2. Assess confidence delta - Higher confidence wins if large gap
3. Check recency - More recent may supersede older
4. Check authority - More authoritative source wins
5. If unresolved - Document both, flag for decision-making

### Output

```markdown
## Synthesis Complete: [pillar]

**Evidence Analyzed:** [N] objects
**Key Insights:** [M]
**Contradictions:** [X] ([Y] resolved, [Z] pending)

### Top Insights
1. [Insight with evidence citation]
2. [Insight with evidence citation]
3. [Insight with evidence citation]

### Decisions Needed
- [Topic requiring DEC-*]
```

## Phase 4: Decisions

### When to Use
- Transforming synthesis insights into explicit decisions
- Making documented trade-offs between options
- Creating decision ledger with risk identification

### Prerequisites
- Synthesis complete (Phase 3)
- `03-synthesis/CROSS-SYNTHESIS.md` exists with decision candidates
- Per-pillar syntheses in `03-synthesis/SYN-*.md`

### Workflow Steps

<required>
1. Load decision candidates from cross-synthesis
2. For each candidate, gather evidence and options
3. Present trade-offs for user decision
4. Create decision entry with semantic ID
5. Identify risks created by each decision
6. Generate DECISIONS.yaml and RISKS.yaml
7. Validate decision quality gates
</required>

### Decision Entry Schema

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

### Quality Gates

**Decision quality gate:**
- Every decision cites ≥2 evidence IDs
- Every decision lists ≥1 alternative considered
- Every decision documents wins AND loses

**Risk quality gate:**
- Every risk links to creating decision
- Every risk has severity and likelihood
- Every risk has ≥1 mitigation

### Output

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

## Phase 5: Specs

### When to Use
- Generating PRD and architecture documents
- Ensuring all spec content traces back to explicit decisions
- Creating constrained specifications with decision citations

### Prerequisites
- Decisions complete (Phase 4)
- `04-decisions/DECISIONS.yaml` exists
- `05-risks/RISKS.yaml` exists

### Core Principle

**No spec section without a DEC-* reference.**

Every requirement, every architecture choice, must trace back to an explicit decision.

### Workflow Steps

<required>
1. Load decisions and risks
2. Generate PRD with decision citations
3. Validate PRD constraint gate
4. Generate architecture with decision citations
5. Validate architecture constraint gate
6. Cross-reference risks in both documents
</required>

### Citation Format

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

### Constraint Gates

Check every PRD section:
- [ ] Section heading has DEC-* reference
- [ ] Requirements cite supporting decisions
- [ ] Risks are cross-referenced where relevant

Check every architecture section:
- [ ] Section heading has DEC-* reference
- [ ] Technical choices cite supporting decisions
- [ ] Risks are cross-referenced where relevant

### Output

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