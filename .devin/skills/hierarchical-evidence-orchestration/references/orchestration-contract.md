# Orchestration Contract

## Purpose

This contract defines the rules and responsibilities for hierarchical evidence orchestration across multiple research pillars or complex research streams.

## Core Principles

1. **Parallel Independence**: Independent research streams should run in parallel to maximize efficiency
2. **Dependency Awareness**: Dependent streams must wait for upstream completion
3. **Consistency Maintenance**: Evidence quality standards must be consistent across all streams
4. **Cross-Pillar Coordination**: Contradictions and dependencies across pillars must be identified and resolved

## Orchestration Levels

### Level 1: Basic Coordination

**Use when:**
- 1-2 pillars
- 1-2 parallel streams
- Simple dependencies

**Responsibilities:**
- Track stream completion status
- Ensure evidence gate compliance
- Basic progress reporting

### Level 2: Task Delegation

**Use when:**
- 3-5 pillars
- 2-3 parallel streams
- Moderate dependencies

**Responsibilities:**
- All Level 1 responsibilities
- Delegate tasks to appropriate agents
- Monitor resource allocation
- Resolve simple conflicts

### Level 3: Full Orchestration

**Use when:**
- 6+ pillars
- 4+ parallel streams
- Complex dependencies

**Responsibilities:**
- All Level 2 responsibilities
- Complex dependency management
- Cross-pillar consistency validation
- Resource optimization
- Timeline management

## Task Delegation Rules

### Assignment Criteria

| Task Type | Preferred Agent | Rationale |
| --------- | --------------- | --------- |
| Evidence collection | collecting-evidence | Specialized in evidence object creation |
| Synthesis | synthesizing-pillars | Specialized in evidence synthesis |
| Decision making | making-decisions | Specialized in decision ledger management |
| Documentation | documentation-audit | Ensures documentation standards |

### Dependency Management

**Dependency types:**

1. **Sequential**: Stream B must complete before Stream A starts
2. **Parallel**: Streams can run independently
3. **Conditional**: Stream A starts if Stream B meets criteria

**Dependency resolution:**

- Critical path prioritization
- Resource reallocation when blocked
- Timeline adjustment for dependencies

## Quality Standards

### Evidence Quality Gates

All streams must pass the same quality gates:

- Minimum 5 evidence objects per pillar
- Confidence scores 0.0-1.0
- At least 1 assumption per evidence object
- Falsifiable claims only
- Traceable sources

### Consistency Requirements

**Cross-stream consistency:**

- Same facts should have consistent evidence
- Confidence scores should be aligned for related claims
- Semantic IDs should not collide across pillars
- Source attribution should be standardized

## Progress Monitoring

### Required Metrics

| Metric | Description | Target |
| ------ | ----------- | ------ |
| Stream completion | % of streams completed | 100% |
| Evidence gate pass rate | % of pillars passing gate | 100% |
| Contradiction resolution | % of contradictions resolved | 100% |
| Timeline adherence | % of streams on schedule | ≥80% |

### Blocker Categories

| Category | Severity | Resolution Time |
| ---------- | -------- | --------------- |
| Resource conflict | High | Immediate |
| Dependency deadlock | High | Immediate |
| Quality gate failure | Medium | Within stream |
| Contradiction | Medium | Before synthesis |
| Timeline pressure | Low | At discretion |

## Reporting Requirements

### Stream-Level Reports

Each stream must report:

- Evidence objects created
- Gate status
- Blockers encountered
- Time spent

### Hierarchical Reports

Orchestrator must produce:

- Cross-pillar consistency summary
- Contradiction inventory
- Resource utilization metrics
- Efficiency analysis

## Error Handling

### Stream Failure

If a stream fails:

1. Document failure reason
2. Assess impact on dependent streams
3. Propose resolution options
4. Escalate if critical path

### Quality Gate Failure

If a gate fails:

1. Identify missing evidence
2. Propose additional research
3. Accept partial evidence with documentation
4. Deprioritize pillar if acceptable

## Success Criteria

Orchestration is successful when:

- All required streams complete
- All evidence gates pass (or gaps documented)
- Cross-pillar consistency validated
- Contradictions resolved or documented
- Timeline within acceptable variance
