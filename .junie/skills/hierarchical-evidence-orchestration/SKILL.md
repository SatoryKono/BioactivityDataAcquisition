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

- Research questions defined for each pillar
- Evidence object schema available
- Task delegation framework established
- Quality gates defined

## Workflow

Use TodoWrite to track these mandatory steps:

<required>
1. Analyze research scope and identify pillars
2. Define task delegation strategy
3. Create task briefs for each stream
4. Orchestrate parallel evidence collection
5. Monitor progress and quality gates
6. Synthesize results across pillars
7. Generate orchestration report
</required>

### Step 1: Analyze Research Scope

Identify research pillars and their dependencies:

**Pillar types:**
- Market (TAM, SAM, SOM, pricing, competition)
- Technology (architecture, scalability, security)
- Operations (team, processes, tools)
- Financial (costs, revenue, projections)

**Dependency analysis:**
- Sequential dependencies (pillar B requires pillar A)
- Parallel streams (independent pillars)
- Conditional dependencies (pillar A starts if pillar B meets criteria)

### Step 2: Define Task Delegation Strategy

Determine delegation approach:

**Delegation options:**
- Single skill for all pillars (simple scope)
- Multiple skills per pillar (complex scope)
- Hierarchical delegation (L1 → L2 → L3 streams)

**Priority assignment:**
- P1: Critical path, blocks other streams
- P2: High priority, important but not blocking
- P3: Medium priority, standard priority
- P4: Low priority, nice to have
- P5: Backlog, can be deferred

### Step 3: Create Task Briefs

Use [references/shard-task-briefs.md](references/shard-task-briefs.md) templates:

**Brief structure:**
```yaml
task_brief:
  stream_id: "stream_name"
  assigned_to: "skill_name"
  priority: 1-5
  estimated_duration: "X hours"
  dependencies:
    - "upstream_stream_id"
  scope:
    pillar: "pillar_name"
    research_questions:
      - "question_1"
      - "question_2"
    sources:
      - "source_type_1"
      - "source_type_2"
  deliverables:
    - "path/to/evidence_object_1.yaml"
    - "path/to/evidence_object_2.yaml"
  acceptance_criteria:
    - "minimum_5_evidence_objects"
    - "all_gates_passed"
    - "quality_standards_met"
```

### Step 4: Orchestrate Parallel Evidence Collection

Execute task delegation:

**Execution modes:**
- Parallel: Independent streams run simultaneously
- Sequential: Dependent streams run in order
- Conditional: Streams start based on gate results

**Monitoring:**
- Track progress per stream
- Monitor quality gate results
- Handle blockers and failures
- Adjust priorities as needed

### Step 5: Monitor Progress and Quality Gates

Track stream progress:

**Progress tracking:**
```yaml
progress_report:
  stream_id: "stream_name"
  status: "in_progress|completed|blocked|failed"
  evidence_collected: 3
  evidence_target: 5
  blockers:
    - "blocker_description"
  time_spent: "1.5 hours"
  estimated_remaining: "0.5 hours"
```

**Quality gate checks:**
- Minimum evidence count met
- All gates passed
- Confidence scores adequate
- No contradictions flagged

### Step 6: Synthesize Results

Combine evidence across pillars:

**Synthesis approach:**
- Identify cross-pillar patterns
- Resolve contradictions
- Aggregate confidence scores
- Generate unified insights

**Output:**
- Synthesis document
- Decision recommendations
- Gap analysis
- Risk assessment

### Step 7: Generate Orchestration Report

Produce final report:

```markdown
## Orchestration Report

**Orchestration Date:** [timestamp]
**Orchestrator:** [agent/skill]
**Total Streams:** [N]
**Completed Streams:** [N]
**Failed Streams:** [N]

### Stream Summary

| Stream | Status | Evidence | Gates | Duration |
| ------ | ------ | -------- | ----- | -------- |
| stream_1 | completed | 5/5 | ✓ | 2.0h |
| stream_2 | completed | 4/5 | ✓ | 1.5h |
| stream_3 | blocked | 2/5 | ✗ | 1.0h |

### Quality Gate Results

| Gate | Status | Notes |
| ---- | ------ | ----- |
| Minimum evidence | ✓ PASS | All streams met minimum |
| All gates passed | ✗ FAIL | stream_3 failed gate |
| Confidence aligned | ✓ PASS | No major conflicts |

### Synthesis Summary

- [Key findings]
- [Cross-pillar patterns]
- [Contradictions resolved]
- [Recommendations]
```

## User Interaction

Use the **AskUserQuestion tool** when:

### Dependency conflict

```
Question: "Stream A depends on Stream B, but Stream B failed quality gate. How to proceed?"
Options:
- "Retry Stream B with different approach"
- "Accept partial evidence from Stream B"
- "Deprioritize Stream A"
- "Escalate to user for decision"
```

### Priority adjustment needed

```
Question: "Stream X is taking longer than expected. Should we adjust priority?"
Options:
- "Increase priority to P1"
- "Keep current priority"
- "Deprioritize to P4"
- "Cancel stream"
```

### Quality gate failure

```
Question: "Stream Y failed quality gate with 3/5 evidence objects. How to proceed?"
Options:
- "Add additional research to meet gate"
- "Accept partial evidence with documentation"
- "Deprioritize pillar if acceptable"
- "Escalate to user for decision"
```

## Output

After orchestration:

```markdown
## Orchestration Complete

**Total Streams:** [N]
**Completed:** [N]
**Failed:** [N]
**Total Duration:** [X hours]

### Summary
- Evidence collected: [N] objects
- Quality gates passed: [N]/[N]
- Contradictions resolved: [N]
- Synthesis generated: [YES/NO]

### Next Steps
- [List any follow-up actions]
- [List any recommendations]
```

## References

- [references/orchestration-contract.md](references/orchestration-contract.md) - orchestration rules and levels
- [references/shard-task-briefs.md](references/shard-task-briefs.md) - task delegation templates
- [../collecting-evidence/SKILL.md](../collecting-evidence/SKILL.md) - evidence collection skill
