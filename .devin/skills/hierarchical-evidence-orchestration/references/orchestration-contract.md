# Orchestration Contract

## Purpose

This document defines the contract for hierarchical evidence orchestration across multiple research pillars or streams.

## Core Principles

1. **Parallel Execution**: Independent streams should run in parallel when possible
2. **Quality Gates**: All streams must meet quality gate criteria before synthesis
3. **Consistent Standards**: All streams use the same evidence object schema
4. **Traceability**: All evidence must be traceable to source and assumptions
5. **Determinism**: Orchestration must be deterministic and replayable

## Orchestration Levels

### Level 1: Single Skill Orchestration

**Use when:**
- Simple research scope (1-3 pillars)
- Single skill can handle all evidence collection
- No complex dependencies

**Approach:**
- Single orchestrator delegates to one skill
- Skill handles all pillars sequentially or in parallel
- Minimal coordination overhead

### Level 2: Multi-Skill Orchestration

**Use when:**
- Medium complexity (3-6 pillars)
- Different skills for different pillar types
- Some dependencies between pillars

**Approach:**
- Orchestrator delegates to multiple skills
- Each skill handles specific pillar types
- Orchestrator manages dependencies and synchronization

### Level 3: Hierarchical Orchestration

**Use when:**
- High complexity (6+ pillars)
- Nested research streams
- Complex dependency graphs

**Approach:**
- L1 orchestrator manages top-level streams
- L2 orchestrators manage sub-streams
- L3 orchestrators manage leaf tasks
- Hierarchical progress reporting and error handling

## Quality Gates

### Gate 1: Minimum Evidence Count

**Requirement:**
- Each stream must collect minimum N evidence objects
- N is defined in task brief (default: 5)

**Failure handling:**
- Retry with additional research
- Accept partial evidence with documentation
- Deprioritize pillar if acceptable

### Gate 2: All Gates Passed

**Requirement:**
- All evidence objects must pass validation gates
- No schema violations
- No missing required fields

**Failure handling:**
- Fix validation errors
- Remove invalid evidence
- Document gaps

### Gate 3: Confidence Alignment

**Requirement:**
- Confidence scores must be consistent across evidence
- No major contradictions (confidence delta > 0.5)
- At least 50% of evidence has confidence ≥ 0.5

**Failure handling:**
- Investigate contradictions
- Add additional research
- Document conflicts

## Dependency Management

### Sequential Dependencies

**Pattern:**
```yaml
dependencies:
  - "upstream_stream_id"
```

**Behavior:**
- Downstream stream waits for upstream completion
- Upstream failure blocks downstream
- Orchestrator manages retry logic

### Parallel Dependencies

**Pattern:**
```yaml
dependencies: []
```

**Behavior:**
- Streams run independently
- No blocking between streams
- Orchestrator monitors all streams

### Conditional Dependencies

**Pattern:**
```yaml
dependencies:
  - stream_id: "upstream_stream_id"
    condition: "evidence_gate_passed"
    threshold: 5
```

**Behavior:**
- Downstream starts if upstream meets condition
- Condition can be gate status, evidence count, confidence score
- Orchestrator evaluates condition before starting downstream

## Error Handling

### Stream Failure

**When a stream fails:**
1. Document failure reason in progress report
2. Assess impact on dependent streams
3. Propose resolution options:
   - Retry with different approach
   - Accept partial evidence with documentation
   - Deprioritize pillar if acceptable
   - Escalate if critical path

### Quality Gate Failure

**When a gate fails:**
1. Identify missing evidence
2. Propose additional research
3. Accept partial evidence with gap documentation
4. Deprioritize pillar if acceptable

### Orchestrator Failure

**When orchestrator fails:**
1. Document failure state
2. Save all collected evidence
3. Provide recovery checkpoint
4. Escalate to user

## Progress Reporting

### Progress Update Frequency

- Real-time: For critical path streams
- Every 30 minutes: For high priority streams
- Every hour: For standard priority streams
- On completion: For all streams

### Progress Report Structure

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
  quality_gates:
    - gate: "minimum_evidence"
      status: "passed|failed|pending"
      score: 3/5
```

## Synthesis Rules

### Cross-Pillar Pattern Identification

- Look for consistent themes across pillars
- Identify supporting or contradictory evidence
- Aggregate confidence scores for patterns

### Contradiction Resolution

- Identify contradictions (confidence delta > 0.5)
- Investigate source reliability
- Add additional research if needed
- Document resolution rationale

### Confidence Aggregation

- Use weighted average for pattern confidence
- Weights based on evidence count and source reliability
- Minimum confidence threshold for synthesis: 0.5

## Orchestration Constraints

### Time Budgets

- Maximum orchestration duration: 24 hours
- Per-stream timeout: 4 hours
- Orchestrator checkpoint interval: 1 hour

### Resource Limits

- Maximum parallel streams: 10
- Maximum evidence objects per stream: 50
- Maximum total evidence objects: 200

### Quality Thresholds

- Minimum evidence per stream: 5
- Minimum confidence for synthesis: 0.5
- Maximum contradiction delta: 0.5

## References

- `docs/00-project/ai/skills/local/collecting-evidence/SKILL.md` - evidence collection
- `docs/00-project/ai/skills/local/making-decisions/SKILL.md` - decision making
- `docs/00-project/ai/skills/local/synthesizing-pillars/SKILL.md` - pillar synthesis
