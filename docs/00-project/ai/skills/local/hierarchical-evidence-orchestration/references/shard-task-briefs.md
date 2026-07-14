# Shard Task Briefs

## Purpose

This document provides templates and examples for task delegation briefs when orchestrating hierarchical evidence collection across multiple research streams.

## Task Brief Template

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

## Example Briefs

### Market Size Research

```yaml
task_brief:
  stream_id: "market_size"
  assigned_to: "collecting-evidence"
  priority: 1
  estimated_duration: "2 hours"
  dependencies: []
  scope:
    pillar: "market"
    research_questions:
      - "What is the total addressable market (TAM)?"
      - "What is the serviceable addressable market (SAM)?"
      - "What is the serviceable obtainable market (SOM)?"
    sources:
      - "industry_reports"
      - "analyst_research"
      - "government_statistics"
  deliverables:
    - "02-evidence/market/EV-market-tam-b2b-saas.yaml"
    - "02-evidence/market/EV-market-sam-vertical.yaml"
    - "02-evidence/market/EV-market-som-target.yaml"
    - "02-evidence/market/EV-market-growth-rate.yaml"
    - "02-evidence/market/EV-market-segment-size.yaml"
  acceptance_criteria:
    - "minimum_5_evidence_objects"
    - "all_gates_passed"
    - "confidence_scores_0.5_or_higher"
```

### Pricing Research

```yaml
task_brief:
  stream_id: "pricing_research"
  assigned_to: "collecting-evidence"
  priority: 2
  estimated_duration: "3 hours"
  dependencies:
    - "market_size"
  scope:
    pillar: "market"
    research_questions:
      - "What is the willingness-to-pay for target segments?"
      - "What are competitor pricing models?"
      - "What is the optimal pricing strategy?"
    sources:
      - "surveys"
      - "competitor_analysis"
      - "academic_research"
  deliverables:
    - "02-evidence/market/EV-market-pricing-smb-wtp.yaml"
    - "02-evidence/market/EV-market-pricing-competitor.yaml"
    - "02-evidence/market/EV-market-pricing-models.yaml"
    - "02-evidence/market/EV-market-pricing-elasticity.yaml"
    - "02-evidence/market/EV-market-pricing-psychology.yaml"
  acceptance_criteria:
    - "minimum_5_evidence_objects"
    - "all_gates_passed"
    - "contradictions_flagged"
```

### Technology Architecture

```yaml
task_brief:
  stream_id: "technology_architecture"
  assigned_to: "collecting-evidence"
  priority: 1
  estimated_duration: "2.5 hours"
  dependencies: []
  scope:
    pillar: "technology"
    research_questions:
      - "What architecture patterns are industry standard?"
      - "What are scalability requirements?"
      - "What are security requirements?"
    sources:
      - "technical_blogs"
      - "case_studies"
      - "standards_documents"
  deliverables:
    - "02-evidence/technology/EV-tech-architecture-patterns.yaml"
    - "02-evidence/technology/EV-tech-scalability-requirements.yaml"
    - "02-evidence/technology/EV-tech-security-standards.yaml"
    - "02-evidence/technology/EV-tech-tech-stack.yaml"
    - "02-evidence/technology/EV-tech-deployment.yaml"
  acceptance_criteria:
    - "minimum_5_evidence_objects"
    - "all_gates_passed"
    - "technical_feasibility_confirmed"
```

## Priority Levels

| Priority | Description | Use When |
| -------- | ----------- | -------- |
| 1 | Critical path | Blocks other streams or high business impact |
| 2 | High priority | Important but not blocking |
| 3 | Medium priority | Standard priority |
| 4 | Low priority | Nice to have |
| 5 | Backlog | Can be deferred |

## Dependency Types

### Sequential

Stream B must complete before Stream A starts:

```yaml
dependencies:
  - "upstream_stream_id"
```

### Parallel

Streams can run independently:

```yaml
dependencies: []
```

### Conditional

Stream A starts if Stream B meets criteria:

```yaml
dependencies:
  - stream_id: "upstream_stream_id"
    condition: "evidence_gate_passed"
    threshold: 5
```

## Acceptance Criteria Templates

### Evidence Gate

```yaml
acceptance_criteria:
  - "minimum_5_evidence_objects"
  - "all_gates_passed"
  - "confidence_scores_0.5_or_higher"
```

### Quality Standards

```yaml
acceptance_criteria:
  - "all_evidence_falsifiable"
  - "all_sources_traceable"
  - "all_assumptions_documented"
  - "semantic_ids_follow_scheme"
```

### Consistency

```yaml
acceptance_criteria:
  - "no_internal_contradictions"
  - "confidence_aligned"
  - "sources_standardized"
```

## Progress Reporting

Each stream should report:

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

## Error Handling

### Stream Failure

If a stream fails:

1. Document failure reason in progress report
2. Assess impact on dependent streams
3. Propose resolution options:
   - Retry with different approach
   - Accept partial evidence with documentation
   - Deprioritize pillar if acceptable
   - Escalate if critical path

### Quality Gate Failure

If a gate fails:

1. Identify missing evidence
2. Propose additional research
3. Accept partial evidence with gap documentation
4. Deprioritize pillar if acceptable

## Brief Validation

Before assigning a task brief, validate:

- [ ] All required fields present
- [ ] Dependencies are valid stream IDs
- [ ] Deliverable paths follow naming scheme
- [ ] Acceptance criteria are measurable
- [ ] Priority is justified
- [ ] Estimated duration is reasonable
