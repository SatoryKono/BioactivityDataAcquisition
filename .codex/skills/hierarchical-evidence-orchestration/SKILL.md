---
name: "hierarchical-evidence-orchestration"
description: "Use when orchestrating complex evidence collection across multiple pillars or research streams. Coordinates parallel evidence gathering, manages task delegation, and ensures consistent quality standards across hierarchical research workflows."
context: "fork"
agent: "general-purpose"
---

# Hierarchical Evidence Orchestration

## Source Of Truth

- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Orchestration contract: [references/orchestration-contract.md](references/orchestration-contract.md)
This skill coordinates hierarchical evidence collection across multiple research pillars or complex research streams.

## Prerequisites

- Ledger workspace initialized (`/ledger-init` completed)
- Multiple pillar assignments or complex research scope
- Evidence collection capacity assessment

## Workflow

Use TodoWrite to track these mandatory steps:

<required>
1. Analyze research scope and identify hierarchy
2. Create orchestration plan with task delegation
3. Assign evidence collection tasks to appropriate agents
4. Monitor parallel evidence collection progress
5. Consolidate evidence across streams
6. Validate hierarchical consistency
7. Generate unified evidence report
</required>

### Step 1: Analyze Research Scope

Assess the research complexity:

- Number of pillars involved
- Dependencies between research streams
- Evidence collection capacity requirements
- Timeline constraints

**Complexity assessment:**

| Complexity Level | Pillars | Parallel Streams | Orchestration Needed |
| ---------------- | ------- | ---------------- | ---------------------- |
| Low              | 1-2    | 1-2              | Basic coordination      |
| Medium           | 3-5    | 2-3              | Task delegation       |
| High             | 6+     | 4+               | Full orchestration     |

### Step 2: Create Orchestration Plan

Define the orchestration strategy per [references/orchestration-contract.md](references/orchestration-contract.md):

**Plan components:**

```yaml
orchestration_plan:
  pillars:
    - name: market
      priority: 1
      evidence_target: 5
      streams:
        - market_size
        - pricing_research
        - competitive_analysis
    - name: technology
      priority: 2
      evidence_target: 5
      streams:
        - architecture
        - scalability
        - security
  parallel_strategy: "concurrent_independent"
  delegation_rules:
    - "Independent streams run in parallel"
    - "Dependent streams wait for upstream completion"
    - "Cross-pillar dependencies flagged for coordination"
```

### Step 3: Assign Evidence Collection Tasks

For each research stream, delegate to appropriate agents:

**Task delegation template:**

```yaml
stream_tasks:
  - stream: market_size
    assigned_to: "collecting-evidence"
    scope:
      pillar: market
      questions: ["TAM", SAM, SOM"]
      sources: ["industry_reports", "analyst_research"]
    deliverables:
      - "02-evidence/market/EV-market-tam-b2b-saas.yaml"
      - "02-evidence/market/EV-market-sam-vertical.yaml"
    dependencies: []
  - stream: pricing_research
    assigned_to: "collecting-evidence"
    scope:
      pillar: market
      questions: ["willingness_to_pay", "pricing_models"]
      sources: ["surveys", "competitor_analysis"]
    deliverables:
      - "02-evidence/market/EV-market-pricing-smb-wtp.yaml"
    dependencies: ["market_size"]
```

### Step 4: Monitor Parallel Progress

Track progress across streams:

**Progress monitoring:**

```yaml
stream_progress:
  market_size:
    status: "in_progress"
    evidence_collected: 3
    evidence_target: 5
    blockers: []
  pricing_research:
    status: "pending"
    evidence_collected: 0
    evidence_target: 5
    blockers: ["market_size"]
  technology_architecture:
    status: "in_progress"
    evidence_collected: 2
    evidence_target: 5
    blockers: []
```

**Blocker resolution:**

- Identify cross-stream dependencies
- Prioritize critical path streams
- Reallocate resources if needed

### Step 5: Consolidate Evidence

When streams complete, consolidate evidence:

**Consolidation checks:**

- Remove duplicate evidence across streams
- Identify contradictions between streams
- Ensure consistent confidence scoring
- Validate semantic ID uniqueness

**Evidence inventory:**

```yaml
evidence_inventory:
  total_evidence_objects: 15
  by_pillar:
    market: 5
    technology: 5
    business_model: 5
  by_confidence:
    high: 8
    medium: 5
    low: 2
  contradictions: 2
```

### Step 6: Validate Hierarchical Consistency

Ensure consistency across hierarchy:

**Consistency checks:**

| Check Type | Description | Action |
| ---------- | ----------- | ------ |
| Cross-pillar consistency | Same facts should have same evidence | Flag contradictions |
| Confidence alignment | Related claims should have aligned confidence | Investigate outliers |
| ID namespace | Semantic IDs should not collide across pillars | Rename if needed |
| Source attribution | Same sources cited consistently | Standardize references |

### Step 7: Generate Unified Report

Produce hierarchical evidence report:

```markdown
## Hierarchical Evidence Collection Report

**Orchestration Summary:**
- Pillars: [N]
- Research streams: [M]
- Total evidence objects: [X]
- Orchestration time: [Y hours]
- Blockers resolved: [Z]

### Evidence by Pillar

#### Market Pillar
- Evidence objects: 5/5 ✓
- Gate status: PASSED
- Key findings: [...]

#### Technology Pillar
- Evidence objects: 5/5 ✓
- Gate status: PASSED
- Key findings: [...]

### Cross-Pillar Insights

- [Synthesized insights from multiple pillars]
- [Identified contradictions and resolutions]
- [Gap analysis across research scope]

### Orchestration Metrics

- Parallel efficiency: [X% faster than sequential]
- Resource utilization: [Y%]
- Quality consistency: [Z%]
```

## User Interaction

Use the **AskUserQuestion tool** when:

### Orchestration strategy unclear

```
Question: "Research scope involves [N] pillars with [M] potential streams. Orchestration complexity assessment:"
Options:
- "Low complexity - basic coordination needed"
- "Medium complexity - task delegation recommended"
- "High complexity - full orchestration required"
- "Help me assess complexity further"
```

### Task delegation conflicts

```
Question: "Stream [A] and Stream [B] both require [resource]. How to resolve?"
Options:
- "Prioritize Stream A (critical path)"
- "Prioritize Stream B (higher priority pillar)"
- "Split resource between streams"
- "Wait for additional capacity"
```

### Contradiction resolution needed

```
Question: "Evidence contradiction found: [details]. How to resolve?"
Options:
- "Flag for manual review"
- "Prioritize more authoritative source"
- "Create evidence for both with contradiction note"
- "Research additional sources for resolution"
```

### Timeline pressure

```
Question: "Evidence collection behind schedule. [N] streams pending, [M] evidence objects remaining."
Options:
- "Extend timeline for quality"
- "Accept partial evidence (document gaps)"
- "Reallocate resources to critical streams"
- "Deprioritize lower-priority pillars"
```

## Output

After hierarchical orchestration:

```markdown
## Orchestration Complete

**Streams Completed:** [M]/[M]
**Total Evidence Objects:** [X]
**Gate Status:** [ALL PASSED/PARTIAL/FAILED]

### Stream Performance
| Stream | Status | Evidence | Time | Blockers |
| ------ | ------ | -------- | ---- | -------- |
| market_size | ✓ | 5/5 | 2h | None |
| pricing_research | ✓ | 5/5 | 3h | None |
| ... | ... | ... | ... | ... |

### Cross-Pillar Consistency
- Consistency score: [X%]
- Contradictions resolved: [Y]/[Z]
- ID collisions: [0]

### Orchestration Efficiency
- Parallel speedup: [X% faster]
- Resource utilization: [Y%]
- Quality maintained: [Yes/No]
```

## References

- [references/orchestration-contract.md](references/orchestration-contract.md) - orchestration rules
- [references/shard-task-briefs.md](references/shard-task-briefs.md) - task delegation templates
- [collecting-evidence/SKILL.md](../collecting-evidence/SKILL.md) - base evidence collection skill
