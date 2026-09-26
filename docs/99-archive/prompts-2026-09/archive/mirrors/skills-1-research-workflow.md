---
status: archived
class: mirror
note: Runtime snapshot only — not paste SSOT. Prefer .codex/** / .junie/** / .devin/**. Epic #8513 / #8517.
---

# Research Workflow

## Evaluation Metadata
- **Category:** Skills
- **Weighted Score:** 8.36 / 10
- **Overall Rating:** High
- **Path:** .codex/skills/research-workflow/SKILL.md

## Evaluation Breakdown
- Clarity: 8/10 (weight: 0.15)
- Completeness: 9/10 (weight: 0.15)
- Specificity: 8/10 (weight: 0.12)
- Context: 9/10 (weight: 10)
- Guardrails: 8/10 (weight: 0.10)
- Maintainability: 8/10 (weight: 0.08)
- Reusability: 8/10 (weight: 0.08)
- Error Handling: 7/10 (weight: 0.08)
- Validation: 8/10 (weight: 0.07)
- Documentation: 9/10 (weight: 0.07)

## Original Content (Summary)

---
name: research-workflow
description: "Use for structured research, deep investigation, traceable evidence, and multi-stream synthesis with explicit decisions and constrained specifications."
context: fork
agent: general-purpose
---

# Research Workflow

## Source Of Truth
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`

This skill provides the single workflow for structured research, deep
investigation, traceable evidence, and multi-stream synthesis. It replaces the
retired `deep-research`, `collecting-evidence`, and
`hierarchical-evidence-orchestration` routes. Use `mode=single` by default and
`mode=multi-stream` only when the task genuinely benefits from independent
evidence streams.

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
2. Generate PRD from decision ledger
3. Generate architecture document from decision ledger
4. Validate every section traces to a DEC-* reference
5. Validate spec quality gates
</required>

### Spec Quality Gates

- Every requirement cites a DEC-* ID
- Every architecture choice cites a DEC-* ID
- No orphan requirements (requirements without decision backing)
- No orphan architecture choices (choices without decision backing)

### Output

```markdown
## Specs Complete

**PRD Generated:** [path/to/PRD.md]
**Architecture Generated:** [path/to/ARCHITECTURE.md]
**Decision Coverage:** 100%
```

## Multi-Stream Mode

Use `mode=multi-stream` only when the task genuinely benefits from independent evidence streams. This mode runs multiple evidence collection streams in parallel and merges them in synthesis.

## Memory Integration

Follow `docs/00-project/ai/agents/guides/MEMORY_USAGE.md` and use the canonical memory workflow from `src/memory/DAILY_WORKFLOW.md`.

## Post-Change Validation

After any edits to this skill:
1. Re-scan impacted code/config/doc/runtime surfaces
2. Use repo search plus memory/evidence anchors to find related tests, docs, contracts, configs, and workflows
3. Edit runtime source first, then sync docs mirrors when behavior or contributor guidance changed
4. Run the shared wrapper contract validation
5. Report checks run, skipped checks, and mirror-sync status
