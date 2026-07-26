# GitHub Issues for Documentation Update

Generated issues for documentation improvement initiative.

---

## Issue 1: [Docs] CLI Commands Cheatsheet for Quick Start

**Title:** [Docs] CLI Commands Cheatsheet for Quick Start

**Labels:** documentation, good first issue, enhancement

**Status:** ✅ COMPLETED (2026-07-24)

**Body:**
```markdown
## Summary
Create a comprehensive CLI commands cheatsheet for quick start and daily operations.

## Description
Develop a single-page CLI commands reference cheatsheet covering:

### Core Commands
- Installation and setup (`make install`, `make test-deps`)
- Testing (`make test`, `pytest` variants)
- Linting (`make lint`, mypy, ruff)
- Architecture checks (`make test-architecture`)
- Local execution (`make run-local`)

### Unified Script Entry Points
- `scripts.engineering.qa` — naming, C901, terminology
- `scripts.engineering.ci` — quality gates, test runner
- `scripts.schema` — config validation, generation
- `scripts.docs` — links, drift, docstrings
- `scripts.diagrams` — lint, check, render
- `scripts.ops.data` — checksums, delta, data dir
- `scripts.engineering.repo` — inventory, catalog, versions

### OS-Specific Wrappers
- Windows PowerShell: `setup_env_windows.ps1`, `run_pytest.ps1`, `run_mypy.ps1`
- WSL/Linux: `setup_env_wsl.sh`, `run_pytest.sh`, `run_mypy.sh`

### Memory Workflow Commands
- `python -m memory.tooling.workflow pre-task ...`
- `python -m memory.tooling.workflow post-task ...`
- `python -m memory.tooling.workflow review-curated`

## Acceptance Criteria
- [x] Cheatsheet created in `docs/03-guides/cheatsheets/cli-commands.md`
- [x] Commands organized by category (Core, Scripts, OS-specific, Memory)
- [x] Each command includes brief description and common use cases
- [x] Cross-references to detailed documentation where applicable
- [x] Table of contents for quick navigation
- [x] Verified against current Makefile and script entry points

## Implementation Details
- Created comprehensive CLI cheatsheet covering BioETL application commands, Makefile build/test commands, and development scripts
- Organized into three main sections: BioETL Application CLI, Build & Test CLI, Development Scripts
- Added table of contents for quick navigation
- Included cross-references to detailed documentation
- Updated guides index to include cheatsheet reference
- Created cheatsheets README with usage guidelines

## References
- `src/memory/DAILY_WORKFLOW.md`
- `AGENTS.md`
- `docs/00-project/RULES.md`
- Makefile and `scripts/` directory structure
```

---

## Issue 2: [Docs] Pipeline Configuration Cheatsheet

**Title:** [Docs] Pipeline Configuration Cheatsheet

**Labels:** documentation, config, enhancement

**Body:**
```markdown
## Summary
Create a pipeline configuration cheatsheet for quick reference when creating or modifying pipeline configs.

## Description
Develop a comprehensive cheatsheet covering:

### Config Hierarchy
- `configs/base/pipeline.yaml` — global defaults
- `configs/providers/{provider}.yaml` — provider-level settings
- `configs/entities/{provider}/{entity}.yaml` — entity-specific config
- `configs/composites/{entity}.yaml` — composite pipeline config

### Required Fields (ADR-025)
- Pipeline identification (pipeline_name, provider, entity_type)
- Business primary keys
- Silver sink configuration (sort_by mandatory per ADR-014)
- Gold sink configuration
- Schema column groups
- Quality section (version, provider, entity, thresholds)
- Filters section (version, provider, entity)
- Contracts (primary_key)

### ADR Compliance Checklist
- [ ] ADR-014: sort_by present in Silver sink
- [ ] ADR-025: Pipeline Config Unification required fields
- [ ] ADR-026: Composite structure (seed, enrichers, merge)
- [ ] ADR-027: DQ hierarchy unified sections
- [ ] ADR-028: Filter hierarchy unified sections
- [ ] ADR-029: Convention-based Config (no legacy path overrides)

### Common Patterns
- Standard pipeline config template
- Provider-level quality defaults
- Filter defaults hierarchy
- Composite pipeline configuration
- Join key rules and column naming (ADR-026 v2)

## Acceptance Criteria
- [ ] Cheatsheet created in `docs/03-guides/cheatsheets/pipeline-config.md`
- [ ] Config hierarchy clearly visualized
- [ ] Required fields marked with ADR references
- [ ] ADR compliance checklist included
- [ ] Common configuration patterns with examples
- [ ] Validation commands included

## References
- `docs/02-architecture/decisions/ADR-025-pipeline-config-unification.md`
- `docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md`
- `docs/02-architecture/decisions/ADR-027-dq-rules-externalization.md`
- `docs/02-architecture/decisions/ADR-028-filter-rules-externalization.md`
- `docs/02-architecture/decisions/ADR-029-convention-based-config.md`
- `docs/00-project/ai/memory/memory-py-config-bot.md`
```

---

## Issue 3: [Docs] Data Quality Rules Reference

**Title:** [Docs] Data Quality Rules Reference

**Labels:** documentation, data-quality, enhancement

**Body:**
```markdown
## Summary
Create a comprehensive data quality rules reference for pipeline configuration and troubleshooting.

## Description
Develop a DQ rules reference covering:

### DQ Hierarchy (ADR-027)
- Base quality defaults (`configs/base/quality.yaml`)
- Provider-level quality overrides (`configs/providers/{provider}.yaml#quality`)
- Entity-level quality configuration (`configs/entities/{provider}/{entity}.yaml#quality`)

### Quality Thresholds
- soft_fail threshold (default: 0.05)
- hard_fail threshold (default: 0.20)
- Provider-specific overrides
- Entity-specific customizations

### DQ Rule Categories
- Completeness rules (null checks, required fields)
- Validity rules (regex patterns, value ranges)
- Uniqueness rules (primary key constraints)
- Consistency rules (cross-field validation)
- Timeliness rules (date ranges, freshness)

### Common DQ Patterns
- Standard field validation
- Custom regex patterns
- Enum validation (ADR-038)
- Business rule validation
- Cross-reference validation

### DQ Investigation Procedures
- How to check DQ failures in logs
- How to identify failing records
- How to adjust thresholds appropriately
- How to add custom DQ rules

## Acceptance Criteria
- [ ] Reference created in `docs/03-guides/cheatsheets/data-quality-rules.md`
- [ ] DQ hierarchy clearly explained with examples
- [ ] Threshold configuration documented
- [ ] Common DQ patterns with code examples
- [ ] Investigation procedures step-by-step
- [ ] Cross-references to ADR-027 and related decisions

## References
- `docs/02-architecture/decisions/ADR-027-dq-rules-externalization.md`
- `docs/02-architecture/decisions/ADR-038-enum-externalization-to-yaml.md`
- `configs/base/quality.yaml`
- `docs/00-project/ai/memory/memory-py-config-bot.md`
```

---

## Issue 4: [Docs] ADR Decision Matrix

**Title:** [Docs] ADR Decision Matrix

**Labels:** documentation, architecture, enhancement

**Body:**
```markdown
## Summary
Create an ADR decision matrix for quick reference to architectural decisions and their implications.

## Description
Develop a comprehensive ADR reference matrix covering:

### ADR Categorization
- **Deployment & Operations**: ADR-010 (Local-Only), ADR-017 (Observability)
- **Data Architecture**: ADR-002 (Medallion), ADR-014 (Deterministic Writes), ADR-018 (Gold SCD)
- **Pipeline Architecture**: ADR-026 (Composite), ADR-031 (Load Strategy)
- **Configuration**: ADR-025 (Unification), ADR-027 (DQ), ADR-028 (Filters), ADR-029 (Convention-based)
- **Schema & Contracts**: ADR-037 (Schema Source), ADR-038 (Enums), ADR-039 (Entity Config)
- **Quality & Governance**: ADR-040 (Diagrams), ADR-045 (DQ Contracts)
- **HTTP & Integration**: ADR-032 (Unified HTTP Client)

### Decision Impact Matrix
For each ADR:
- **Scope**: What areas of the system does it affect?
- **Constraints**: What limitations does it impose?
- **Migration**: How to migrate existing code?
- **Testing**: What test coverage is required?
- **Monitoring**: What observability is needed?

### ADR Interdependencies
- Which ADRs depend on others?
- Conflicts and resolutions
- Superseded ADRs (e.g., ADR-008)

### Quick Reference Table
| ADR | Topic | Status | Key Constraint | Migration Path |
|-----|-------|--------|----------------|---------------|
| ADR-010 | Local-Only | Accepted | No Docker/Redis required | N/A |
| ADR-014 | Deterministic Writes | Accepted | sort_by mandatory in Silver | Add sort_by to configs |
| ... | ... | ... | ... | ... |

## Acceptance Criteria
- [ ] Decision matrix created in `docs/03-guides/cheatsheets/adr-matrix.md`
- [ ] ADRs categorized by domain
- [ ] Impact matrix for each ADR
- [ ] Interdependency graph documented
- [ ] Quick reference table with key information
- [ ] Cross-references to full ADR documents

## References
- `docs/02-architecture/decisions/` (full ADR directory)
- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/RULES.md`
```

---

## Issue 5: [Docs] Tutorial: Create New Pipeline in 15 Minutes

**Title:** [Docs] Tutorial: Create New Pipeline in 15 Minutes

**Labels:** documentation, tutorial, enhancement

**Body:**
```markdown
## Summary
Create a hands-on tutorial for creating a new BioETL pipeline from scratch in 15 minutes.

## Description
Develop a step-by-step tutorial covering:

### Prerequisites
- Local environment setup
- Required dependencies
- Understanding of Medallion architecture
- Target provider API documentation

### Step-by-Step Guide
1. **Domain Entity Creation** (3 min)
   - Create domain model in `src/bioetl/domain/{provider}/`
   - Define schema with Pandera
   - Create Port/Protocol interfaces

2. **Transformer Implementation** (4 min)
   - Create transformer in `src/bioetl/infrastructure/adapters/{provider}/`
   - Implement field mapping with FieldGroup/FieldSpec
   - Handle data normalization and validation

3. **Pipeline Configuration** (3 min)
   - Create `configs/entities/{provider}/{entity}.yaml`
   - Configure pipeline identification
   - Set up Silver/Gold sinks with sort_by
   - Define quality rules and filters

4. **Schema Registration** (2 min)
   - Register transformer in factory
   - Update schema generation
   - Validate configuration

5. **Testing** (3 min)
   - Create unit tests
   - Add VCR cassettes for HTTP tests
   - Run local test execution

### Common Pitfalls
- Missing sort_by in Silver sink (ADR-014)
- Incorrect field mapping
- Missing quality thresholds
- Incomplete test coverage

### Verification Checklist
- [ ] Config validation passes
- [ ] Unit tests pass
- [ ] Integration tests with VCR pass
- [ ] Architecture tests pass
- [ ] Manual local execution succeeds

## Acceptance Criteria
- [ ] Tutorial created in `docs/03-guides/tutorials/create-new-pipeline.md`
- [ ] Step-by-step instructions with time estimates
- [ ] Code examples for each step
- [ ] Common pitfalls and solutions
- [ ] Verification checklist
- [ ] Links to related ADRs and documentation

## References
- `docs/02-architecture/decisions/ADR-025-pipeline-config-unification.md`
- `docs/02-architecture/decisions/ADR-014-deterministic-writes.md`
- `docs/00-project/ai/memory/memory-py-config-bot.md`
- `.devin/skills/new-pipeline/SKILL.md`
```

---

## Issue 6: [Docs] Tutorial: Debug Data in Bronze/Silver/Gold Layers

**Title:** [Docs] Tutorial: Debug Data in Bronze/Silver/Gold Layers

**Labels:** documentation, tutorial, debugging

**Body:**
```markdown
## Summary
Create a hands-on tutorial for debugging data issues across Medallion layers.

## Description
Develop a comprehensive debugging tutorial covering:

### Layer-Specific Debugging

#### Bronze Layer Debugging
- Raw data inspection techniques
- JSONL parsing issues
- API response validation
- Encoding problems
- Append-only verification

#### Silver Layer Debugging
- Merge/upsert failure investigation
- Content hash validation
- Sort order verification (ADR-014)
- Delta Lake ACID violations
- DQ threshold failures

#### Gold Layer Debugging
- SCD Type 2 issues
- Schema validation failures
- Strict validation mode (ADR-018)
- Business rule violations
- Downstream consumer issues

### Debugging Tools
- Delta Lake inspection commands
- Pandera schema validation
- Data quality rule testing
- Content hash computation
- Metadata inspection

### Common Error Patterns
- Encoding mismatches
- Null handling inconsistencies
- Date format issues
- Identifier collisions
- Schema drift

### Investigation Workflow
1. Identify affected layer
2. Inspect raw data
3. Validate schema compliance
4. Check DQ rules
5. Verify transformation logic
6. Test with sample data

## Acceptance Criteria
- [ ] Tutorial created in `docs/03-guides/tutorials/debug-medallion-layers.md`
- [ ] Layer-specific debugging sections
- [ ] Tool commands and examples
- [ ] Common error patterns with solutions
- [ ] Step-by-step investigation workflow
- [ ] Cross-references to ADR-002, ADR-014, ADR-018

## References
- `docs/02-architecture/decisions/ADR-002-medallion-architecture.md`
- `docs/02-architecture/decisions/ADR-014-deterministic-writes.md`
- `docs/02-architecture/decisions/ADR-018-gold-scd-type-2.md`
- `docs/00-project/ai/memory/memory-py-debug-bot.md`
```

---

## Issue 7: [Docs] Tutorial: Monitoring and Alerts Setup

**Title:** [Docs] Tutorial: Monitoring and Alerts Setup

**Labels:** documentation, tutorial, monitoring

**Body:**
```markdown
## Summary
Create a hands-on tutorial for setting up monitoring and alerts for BioETL pipelines.

## Description
Develop a comprehensive monitoring tutorial covering:

### Monitoring Stack Overview
- Local-only monitoring (ADR-010)
- Optional Grafana integration
- Prometheus metrics export
- Structured logging (ADR-017, ADR-019)

### Metrics Setup
- Pipeline execution metrics
- Data quality metrics
- HTTP client metrics (ADR-032)
- Custom business metrics
- Resource utilization metrics

### Alert Configuration
- DQ threshold alerts
- Pipeline failure alerts
- Performance degradation alerts
- Data freshness alerts
- Resource exhaustion alerts

### Grafana Dashboard Setup
- Dashboard installation
- Panel configuration
- Query building
- Variable setup
- Annotation management

### Logging Configuration
- Structured logging setup
- Log level configuration
- Sensitive data filtering
- Log aggregation
- Log retention policies

### Verification Procedures
- Metrics collection verification
- Alert testing procedures
- Dashboard validation
- Log inspection techniques

## Acceptance Criteria
- [ ] Tutorial created in `docs/03-guides/tutorials/monitoring-alerts-setup.md`
- [ ] Monitoring stack overview
- [ ] Metrics setup instructions
- [ ] Alert configuration examples
- [ ] Grafana dashboard setup guide
- [ ] Logging configuration procedures
- [ ] Verification checklist

## References
- `docs/02-architecture/decisions/ADR-010-local-only-deployment.md`
- `docs/02-architecture/decisions/ADR-017-observability.md`
- `docs/02-architecture/decisions/ADR-019-structured-logging.md`
- `docs/02-architecture/decisions/ADR-032-unified-http-client.md`
- `docs/03-guides/dashboards/dashboard-extension-llm.md`
```

---

## Issue 8: [Docs] Tutorial: Working with Quarantine System

**Title:** [Docs] Tutorial: Working with Quarantine System

**Labels:** documentation, tutorial, data-quality

**Body:**
```markdown
## Summary
Create a hands-on tutorial for working with the BioETL quarantine system for failed records.

## Description
Develop a comprehensive quarantine tutorial covering:

### Quarantine System Overview
- Purpose and design principles
- Quarantine triggers (DQ failures, validation errors)
- Quarantine data structure
- Integration with Medallion layers

### Quarantine Workflow
1. Record identification
2. Quarantine classification
3. Root cause analysis
4. Remediation procedures
5. Re-processing workflows

### Quarantine Investigation
- Quarantine record inspection
- Failure reason analysis
- Pattern detection
- Batch vs individual failures
- Source system issues

### Remediation Strategies
- Configuration fixes (thresholds, rules)
- Data source corrections
- Transformer updates
- Schema adjustments
- Exception handling improvements

### Re-processing Procedures
- Quarantine record extraction
- Fix validation
- Re-processing execution
- Success verification
- Quarantine cleanup

### Monitoring and Alerting
- Quarantine rate metrics
- Quarantine backlog alerts
- Pattern change detection
- Remediation success tracking

## Acceptance Criteria
- [ ] Tutorial created in `docs/03-guides/tutorials/quarantine-system.md`
- [ ] Quarantine system overview
- [ ] Step-by-step workflow documentation
- [ ] Investigation procedures
- [ ] Remediation strategies with examples
- [ ] Re-processing procedures
- [ ] Monitoring and alerting setup

## References
- `docs/00-project/RULES.md` (DQ and quarantine sections)
- `docs/02-architecture/decisions/ADR-027-dq-rules-externalization.md`
- `docs/00-project/ai/memory/memory-py-debug-bot.md`
```

---

## Issue 9: [Docs] Architecture Diagrams Update (ADR-040 Compliance)

**Title:** [Docs] Architecture Diagrams Update (ADR-040 Compliance)

**Labels:** documentation, architecture, diagrams, adr-040

**Body:**
```markdown
## Summary
Update and create architecture diagrams following ADR-040 compliance using technical-designer-mermaid skill.

## Description
Update the architecture diagrams to comply with ADR-040 standards:

### Required Diagrams

#### 1. System Architecture Diagram
- Hexagonal architecture layers
- Ports & Adapters pattern
- Component relationships
- Data flow between layers

#### 2. Medallion Architecture Diagram
- Bronze → Silver → Gold flow
- Delta Lake integration
- Quarantine system integration
- Checkpoint system

#### 3. Pipeline Orchestration Diagram
- Pipeline execution flow
- Composite pipeline pattern (ADR-026)
- Error handling and retry
- Control plane components

#### 4. Provider Integration Diagrams
- Individual provider data flows
- HTTP client integration (ADR-032)
- VCR testing integration
- Rate limiting and circuit breakers

### ADR-040 Compliance Requirements
- [ ] Diagrams use Mermaid syntax
- [ ] Diagrams are in `docs/02-architecture/diagrams/`
- [ ] Each diagram has metadata (version, author, status)
- [ ] Diagrams are linted with `python -m scripts.diagrams lint`
- [ ] Diagrams pass quality gates
- [ ] Rendered outputs available (PDF/SVG)
- [ ] Diagrams are documented in diagram registry

### Sequence Diagrams
- Pipeline execution sequence
- HTTP request/response flow
- DQ validation sequence
- Quarantine handling sequence

### State Machine Diagrams
- Pipeline state transitions
- Retry logic state machine
- Lock acquisition/release flow
- Error recovery states

## Acceptance Criteria
- [ ] All required diagrams created/updated
- [ ] ADR-040 compliance verified
- [ ] Diagrams lint and pass quality gates
- [ ] Rendered outputs generated
- [ ] Diagram registry updated
- [ ] Documentation references diagrams

## References
- `docs/02-architecture/decisions/ADR-040-diagram-governance.md`
- `.devin/skills/technical-designer-mermaid/SKILL.md`
- `docs/02-architecture/diagrams/`
- `python -m scripts.diagrams lint`
- `python -m scripts.diagrams check quality-gates`
```

---

## Issue 10: [Docs] Sequence Diagrams for Pipelines

**Title:** [Docs] Sequence Diagrams for Pipelines

**Labels:** documentation, diagrams, mermaid

**Body:**
```markdown
## Summary
Create sequence diagrams for key pipeline workflows using Mermaid syntax.

## Description
Develop sequence diagrams for the following workflows:

### Pipeline Execution Sequence
- CLI invocation
- Bootstrap and DI composition
- Pipeline instantiation
- Data extraction
- Transformation
- Silver/Gold writes
- Cleanup and shutdown

### Composite Pipeline Sequence (ADR-026)
- Seed pipeline execution
- Enricher pipeline coordination
- Merge operation
- Conflict resolution
- Final output generation

### HTTP Request/Response Flow (ADR-032)
- UnifiedHTTPClient usage
- Rate limiting
- Circuit breaker activation
- Retry logic
- Error handling

### DQ Validation Sequence
- Schema validation
- DQ rule application
- Threshold evaluation
- Quarantine routing
- Success/failure handling

### Quarantine Handling Sequence
- Failure detection
- Quarantine record creation
- Root cause logging
- Alert generation
- Remediation workflow

## ADR-040 Compliance
- [ ] Mermaid syntax used
- [ ] Diagrams in `docs/02-architecture/diagrams/sequence/`
- [ ] Metadata included (version, status, author)
- [ ] Linted with `python -m scripts.diagrams lint`
- [ ] Quality gates passed
- [ ] Rendered outputs available

## Acceptance Criteria
- [ ] All sequence diagrams created
- [ ] ADR-040 compliant
- [ ] Cross-referenced in relevant documentation
- [ ] Included in diagram registry

## References
- `docs/02-architecture/decisions/ADR-040-diagram-governance.md`
- `docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md`
- `docs/02-architecture/decisions/ADR-032-unified-http-client.md`
- `.devin/skills/technical-designer-mermaid/SKILL.md`
```

---

## Issue 11: [Docs] Data Flow Diagrams for Each Provider

**Title:** [Docs] Data Flow Diagrams for Each Provider

**Labels:** documentation, diagrams, mermaid, providers

**Body:**
```markdown
## Summary
Create data flow diagrams for each BioETL provider (ChEMBL, PubChem, UniProt, PubMed, CrossRef, OpenAlex, SemanticScholar).

## Description
Develop provider-specific data flow diagrams:

### Required Diagrams per Provider
1. **API Integration Flow**
   - Authentication
   - Request construction
   - Pagination handling
   - Rate limiting
   - Response parsing

2. **Data Transformation Flow**
   - Raw API response
   - Field mapping
   - Data normalization
   - Validation
   - Domain entity creation

3. **Medallion Layer Flow**
   - Bronze write (JSONL)
   - Silver transformation
   - Gold enrichment
   - Quarantine routing

4. **Error Handling Flow**
   - API errors
   - Validation failures
   - DQ threshold breaches
   - Retry logic
   - Circuit breaker activation

### Provider-Specific Considerations
- **ChEMBL**: Activity data normalization, target mapping
- **PubChem**: Compound bioassay integration
- **UniProt**: Protein data processing
- **PubMed**: Publication metadata handling
- **CrossRef**: DOI resolution and enrichment
- **OpenAlex**: Work data processing
- **SemanticScholar**: Paper metadata integration

## ADR-040 Compliance
- [ ] Mermaid syntax used
- [ ] Diagrams in `docs/02-architecture/diagrams/providers/{provider}/`
- [ ] Metadata included
- [ ] Linted and quality gates passed
- [ ] Rendered outputs available

## Acceptance Criteria
- [ ] Data flow diagrams for all 7 providers
- [ ] ADR-040 compliant
- [ ] Provider-specific considerations documented
- [ ] Cross-referenced in provider documentation
- [ ] Included in diagram registry

## References
- `docs/02-architecture/decisions/ADR-040-diagram-governance.md`
- `docs/04-reference/providers/`
- `.devin/skills/technical-designer-mermaid/SKILL.md`
```

---

## Issue 12: [Docs] State Machine Diagrams for Workflow Control Plane

**Title:** [Docs] State Machine Diagrams for Workflow Control Plane

**Labels:** documentation, diagrams, mermaid, workflow

**Body:**
```markdown
## Summary
Create state machine diagrams for workflow control plane components.

## Description
Develop state machine diagrams for the following workflows:

### Pipeline State Machine
- Initial → Running → Success/Failure
- Retry states
- Circuit breaker states
- Cleanup states

### Lock Acquisition State Machine
- Lock request → Pending → Acquired/Failed
- Lock renewal
- Lock release
- Lock timeout handling

### Checkpoint State Machine
- Checkpoint creation
- Checkpoint validation
- Checkpoint recovery
- Checkpoint cleanup

### Error Recovery State Machine
- Error detection
- Classification (transient/permanent)
- Retry decision
- Escalation
- Manual intervention

### DQ Validation State Machine
- Validation start
- Rule evaluation
- Threshold check
- Quarantine routing
- Success/failure paths

## ADR-040 Compliance
- [ ] Mermaid syntax used
- [ ] Diagrams in `docs/02-architecture/diagrams/state-machines/`
- [ ] Metadata included
- [ ] Linted and quality gates passed
- [ ] Rendered outputs available

## Acceptance Criteria
- [ ] All state machine diagrams created
- [ ] ADR-040 compliant
- [ ] State transitions clearly documented
- [ ] Error conditions handled
- [ ] Cross-referenced in workflow documentation
- [ ] Included in diagram registry

## References
- `docs/02-architecture/decisions/ADR-040-diagram-governance.md`
- `docs/02-architecture/decisions/ADR-044-control-plane-replay.md`
- `docs/02-architecture/decisions/ADR-046-checkpoint-based-incremental-processing.md`
- `.devin/skills/technical-designer-mermaid/SKILL.md`
```

---

## Issue 13: [Docs] Troubleshooting Guide - Common Error Patterns

**Title:** [Docs] Troubleshooting Guide - Common Error Patterns

**Labels:** documentation, troubleshooting, enhancement

**Body:**
```markdown
## Summary
Create a comprehensive troubleshooting guide for common error patterns in BioETL.

## Description
Develop a troubleshooting guide covering:

### Import/Module Errors
- ModuleNotFoundError
- ImportError
- Circular import detection
- Layer boundary violations
- Resolution strategies

### Type Errors
- TypeError in transformations
- AttributeError
- mypy errors
- Protocol compliance issues
- Type annotation fixes

### Data/Validation Errors
- Pandera validation failures
- Schema drift
- DQ threshold breaches
- Null handling issues
- Enum validation errors

### State Errors
- AssertionError in tests
- Operation order issues
- Side effect problems
- State consistency
- Debugging techniques

### Infrastructure Errors
- ConnectionError
- TimeoutError
- VCR cassette issues
- Mock setup problems
- Fixture mismatches

### Pipeline Errors
- Pipeline configuration errors
- Transformer failures
- Silver/Gold write failures
- Merge conflicts
- Quarantine routing issues

### Performance Issues
- Slow pipeline execution
- Memory exhaustion
- CPU bottlenecks
- I/O contention
- Optimization strategies

## Error Resolution Template
For each error pattern:
- **Symptoms**: What you see
- **Root Causes**: Common reasons
- **Diagnosis Steps**: How to investigate
- **Resolution**: How to fix
- **Prevention**: How to prevent recurrence

## Acceptance Criteria
- [ ] Troubleshooting guide created in `docs/05-operations/troubleshooting/common-errors.md`
- [ ] Error patterns categorized
- [ ] Resolution template followed
- [ ] Cross-references to relevant ADRs
- [ ] Commands and examples included
- [ ] Prevention strategies documented

## References
- `docs/00-project/ai/memory/memory-py-debug-bot.md`
- `docs/00-project/RULES.md`
- `docs/02-architecture/decisions/`
```

---

## Issue 14: [Docs] Performance Tuning Guide

**Title:** [Docs] Performance Tuning Guide

**Labels:** documentation, performance, enhancement

**Body:**
```markdown
## Summary
Create a comprehensive performance tuning guide for BioETL pipelines.

## Description
Develop a performance tuning guide covering:

### Pipeline Performance
- Transformer optimization
- Batch sizing strategies
- Parallel processing configuration
- Memory management
- I/O optimization

### HTTP Client Performance (ADR-032)
- Connection pooling
- Rate limiting optimization
- Retry strategy tuning
- Timeout configuration
- Circuit breaker thresholds

### Data Processing Performance
- Pandas optimization techniques
- Delta Lake query optimization
- Index usage strategies
- Partitioning strategies
- Caching strategies

### Resource Utilization
- CPU profiling
- Memory profiling
- I/O profiling
- Network profiling
- Resource bottleneck identification

### Medallion Layer Optimization
- Bronze write optimization
- Silver merge optimization
- Gold query optimization
- Quarantine processing optimization
- Checkpoint optimization

### Testing Performance
- Test suite optimization
- VCR cassette optimization
- Parallel test execution
- Test selection strategies
- Coverage optimization

## Performance Profiling Tools
- Python profilers (cProfile, line_profiler)
- Memory profilers (memory_profiler)
- Delta Lake query profiling
- Custom metrics collection
- Performance benchmarking

## Acceptance Criteria
- [ ] Performance guide created in `docs/05-operations/performance-tuning.md`
- [ ] Performance categories covered
- [ ] Optimization strategies documented
- [ ] Profiling tools explained
- [ ] Case studies included
- [ ] Cross-references to ADR-032

## References
- `docs/02-architecture/decisions/ADR-032-unified-http-client.md`
- `docs/00-project/ai/memory/memory-py-debug-bot.md`
- `docs/02-architecture/decisions/ADR-002-medallion-architecture.md`
```

---

## Issue 15: [Docs] Data Quality Investigation Procedures

**Title:** [Docs] Data Quality Investigation Procedures

**Labels:** documentation, data-quality, troubleshooting

**Body:**
```markdown
## Summary
Create comprehensive data quality investigation procedures for troubleshooting DQ issues.

## Description
Develop DQ investigation procedures covering:

### DQ Failure Investigation Workflow
1. **Failure Identification**
   - DQ threshold breach detection
   - Affected records identification
   - Failure classification (completeness, validity, etc.)

2. **Root Cause Analysis**
   - Pattern detection
   - Source system issues
   - Configuration problems
   - Transformer bugs
   - Schema drift

3. **Impact Assessment**
   - Affected pipeline scope
   - Downstream consumer impact
   - Data quality degradation
   - Business impact evaluation

4. **Remediation Planning**
   - Configuration fixes
   - Data source corrections
   - Code changes
   - Schema updates
   - Exception handling improvements

### Investigation Tools
- DQ rule inspection
- Quarantine record analysis
- Data sampling techniques
- Statistical analysis
- Pattern recognition

### Common DQ Issues
- Null value handling
- Regex pattern failures
- Enum validation errors
- Range violations
- Consistency rule failures
- Uniqueness constraint violations

### DQ Threshold Tuning
- When to adjust thresholds
- Threshold calibration procedures
- Provider-specific thresholds
- Entity-specific thresholds
- Threshold validation

## Acceptance Criteria
- [ ] Investigation procedures created in `docs/05-operations/data-quality-investigation.md`
- [ ] Step-by-step workflow documented
- [ ] Investigation tools explained
- [ ] Common issues with solutions
- [ ] Threshold tuning guidelines
- [ ] Cross-references to ADR-027

## References
- `docs/02-architecture/decisions/ADR-027-dq-rules-externalization.md`
- `docs/00-project/ai/memory/memory-py-debug-bot.md`
- `docs/00-project/RULES.md` (DQ sections)
```

---

## Issue 16: [Docs] Lock Contention Resolution

**Title:** [Docs] Lock Contention Resolution

**Labels:** documentation, troubleshooting, operations

**Body:**
```markdown
## Summary
Create a comprehensive guide for resolving lock contention issues in BioETL.

## Description
Develop lock contention resolution procedures covering:

### Lock System Overview
- Memory-based locking (ADR-010)
- Lock acquisition semantics
- Lock timeout handling
- Lock renewal mechanisms
- Lock release procedures

### Lock Contention Detection
- Symptoms of lock contention
- Monitoring lock wait times
- Identifying deadlock scenarios
- Lock holder identification
- Contention metrics

### Common Contention Scenarios
- Concurrent pipeline execution
- Long-running transactions
- Failed lock releases
- Resource exhaustion
- Configuration issues

### Resolution Strategies
1. **Immediate Resolution**
   - Manual lock release procedures
   - Pipeline cancellation
   - Resource cleanup
   - Emergency procedures

2. **Configuration Fixes**
   - Lock timeout adjustment
   - Retry strategy tuning
   - Pipeline scheduling changes
   - Resource allocation

3. **Code Fixes**
   - Lock scope reduction
   - Transaction optimization
   - Error handling improvements
   - Cleanup procedure fixes

### Prevention Strategies
- Pipeline scheduling optimization
- Lock usage best practices
- Resource allocation planning
- Monitoring and alerting
- Testing procedures

## Acceptance Criteria
- [ ] Lock contention guide created in `docs/05-operations/lock-contention-resolution.md`
- [ ] Lock system overview included
- [ ] Detection procedures documented
- [ ] Resolution strategies explained
- [ ] Prevention strategies covered
- [ ] Cross-references to ADR-010

## References
- `docs/02-architecture/decisions/ADR-010-local-only-deployment.md`
- `docs/02-architecture/decisions/ADR-046-checkpoint-based-incremental-processing.md`
- `docs/00-project/ai/memory/memory-py-debug-bot.md`
```

---

## Issue 17: [Docs] MCP Integration Guide

**Title:** [Docs] MCP Integration Guide

**Labels:** documentation, integration, mcp

**Body:**
```markdown
## Summary
Create a comprehensive guide for MCP (Model Context Protocol) integration with external systems.

## Description
Develop an MCP integration guide covering:

### MCP Overview
- MCP architecture and purpose
- BioETL MCP server configuration
- Available MCP tools and resources
- Integration patterns

### MCP Server Configuration
- Server setup and configuration
- Tool registration
- Resource definitions
- Authentication and security
- Performance considerations

### Available MCP Tools
- Memory query tools
- Graph operations
- Timeline queries
- RAG retrieval
- Custom tool development

### Integration Patterns
1. **Memory Integration**
   - Pre-task workflow integration
   - Post-task workflow integration
   - Memory query patterns
   - Context retrieval strategies

2. **External System Integration**
   - Database connectivity
   - API integration
   - File system access
   - Custom protocol implementation

### Security Considerations
- Authentication mechanisms
- Authorization patterns
- Secret management
- Access control
- Audit logging

### Testing and Validation
- MCP server testing
- Tool validation
- Integration testing
- Performance testing
- Error handling

## Acceptance Criteria
- [ ] MCP integration guide created in `docs/05-operations/mcp-integration.md`
- [ ] MCP overview included
- [ ] Configuration procedures documented
- [ ] Available tools documented
- [ ] Integration patterns explained
- [ ] Security considerations covered
- [ ] Testing procedures included

## References
- `docs/00-project/ai/memory/mcp-memory.json`
- `docs/00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md`
- `src/memory/DAILY_WORKFLOW.md`
```

---

## Issue 18: [Docs] Grafana Dashboard Configuration Guide

**Title:** [Docs] Grafana Dashboard Configuration Guide

**Labels:** documentation, monitoring, grafana

**Body:**
```markdown
## Summary
Create a comprehensive guide for configuring and customizing Grafana dashboards for BioETL.

## Description
Develop a Grafana dashboard configuration guide covering:

### Dashboard Setup
- Grafana installation (optional, ADR-010)
- Dashboard installation procedures
- Data source configuration
- Dashboard import/export
- Dashboard versioning

### Dashboard Components
- Panel configuration
- Query building
- Variable setup
- Annotation management
- Alert configuration

### BioETL-Specific Dashboards
1. **Pipeline Overview Dashboard**
   - Pipeline execution metrics
   - Data quality metrics
   - Resource utilization
   - Error rates

2. **Provider Health Dashboard**
   - Provider-specific metrics
   - API call rates
   - Error rates by provider
   - Data freshness

3. **Data Quality Dashboard**
   - DQ threshold breaches
   - Quarantine rates
   - Validation failures
   - Trend analysis

### Panel Types and Queries
- Time series panels
- Stat panels
- Table panels
- Heatmap panels
- Gauge panels

### Dashboard Customization
- Panel customization
- Query optimization
- Variable configuration
- Template variables
- Dashboard links

### Dashboard Extension (LLM)
- Using dashboard-extension-llm guide
- Panel query modification
- Dashboard navigation updates
- Loki/Tempo drilldown configuration

## Acceptance Criteria
- [ ] Dashboard guide created in `docs/05-operations/grafana-dashboard-configuration.md`
- [ ] Setup procedures documented
- [ ] Component configuration explained
- [ ] BioETL-specific dashboards covered
- [ ] Customization procedures included
- [ ] Cross-references to dashboard-extension-llm guide

## References
- `docs/03-guides/dashboards/dashboard-extension-llm.md`
- `docs/02-architecture/decisions/ADR-010-local-only-deployment.md`
- `docs/02-architecture/decisions/ADR-017-observability.md`
- `grafana/dashboards/`
```

---

## Issue 19: [Docs] Prometheus Metrics Export Guide

**Title:** [Docs] Prometheus Metrics Export Guide

**Labels:** documentation, monitoring, prometheus

**Body:**
```markdown
## Summary
Create a comprehensive guide for Prometheus metrics export configuration for BioETL.

## Description
Develop a Prometheus metrics export guide covering:

### Metrics Overview
- Prometheus integration architecture
- Metric types (counter, gauge, histogram, summary)
- Metric naming conventions
- Label best practices
- Cardinality considerations

### BioETL Metrics
1. **Pipeline Metrics**
   - Pipeline execution duration
   - Records processed
   - Error rates
   - DQ pass/fail rates

2. **HTTP Client Metrics** (ADR-032)
   - Request duration
   - Request count
   - Error count
   - Retry count
   - Circuit breaker state

3. **Data Quality Metrics**
   - DQ rule evaluations
   - Threshold breaches
   - Quarantine rates
   - Validation failures

4. **Resource Metrics**
   - Memory usage
   - CPU usage
   - I/O operations
   - Lock contention

### Metrics Configuration
- Metrics registration
- Label configuration
- Metric initialization
- Metrics collection
- Metrics export

### Prometheus Setup
- Prometheus server configuration
- Scrape configuration
- Retention policies
- Storage configuration
- Query optimization

### Alerting Rules
- Alert rule definition
- Alert evaluation
- Alert routing
- Alert notification
- Alert testing

### Query Examples
- Common PromQL queries
- Rate calculations
- Aggregation patterns
- Time range selection
- Label filtering

## Acceptance Criteria
- [ ] Metrics export guide created in `docs/05-operations/prometheus-metrics-export.md`
- [ ] Metrics overview included
- [ ] BioETL metrics documented
- [ ] Configuration procedures explained
- [ ] Prometheus setup covered
- [ ] Alerting rules documented
- [ ] Query examples included

## References
- `docs/02-architecture/decisions/ADR-017-observability.md`
- `docs/02-architecture/decisions/ADR-032-unified-http-client.md`
- `prometheus/` (if exists)
```

---

## Issue 20: [Docs] CI/CD Pipeline Integration Guide

**Title:** [Docs] CI/CD Pipeline Integration Guide

**Labels:** documentation, ci-cd, integration

**Body:**
```markdown
## Summary
Create a comprehensive guide for CI/CD pipeline integration with BioETL.

## Description
Develop a CI/CD integration guide covering:

### CI Pipeline Overview
- GitHub Actions configuration
- Pipeline stages and jobs
- Artifact management
- Caching strategies
- Parallel execution

### Quality Gates
- Linting gates (ruff, mypy)
- Architecture tests
- Contract tests
- Coverage thresholds
- Security scanning

### Testing in CI
- Unit test execution
- Integration test execution
- Architecture test execution
- E2E test execution (optional)
- Test result reporting

### Build and Release
- Package building
- Version management
- Release tagging
- Changelog generation
- Release notes

### Environment Management
- Development environment
- Staging environment
- Production environment
- Environment variables
- Secret management

### Deployment Procedures
- Deployment strategies
- Rollback procedures
- Database migrations
- Configuration updates
- Health checks

### Monitoring and Alerting
- CI pipeline monitoring
- Deployment monitoring
- Runtime monitoring
- Alert configuration
- Incident response

## Acceptance Criteria
- [ ] CI/CD guide created in `docs/05-operations/ci-cd-integration.md`
- [ ] CI pipeline overview included
- [ ] Quality gates documented
- [ ] Testing procedures explained
- [ ] Build/release procedures covered
- [ ] Deployment procedures documented
- [ ] Monitoring/Alerting included

## References
- `.github/workflows/`
- `docs/00-project/RULES.md` (testing sections)
- `docs/02-architecture/decisions/ADR-042-testing-strategy.md`
```

---

## Issue 21: [Docs] Full Documentation Audit

**Title:** [Docs] Full Documentation Audit

**Labels:** documentation, audit, quality

**Body:**
```markdown
## Summary
Perform a full audit of BioETL documentation for accuracy, completeness, and consistency.

## Description
Execute a comprehensive documentation audit using the documentation-audit skill:

### Audit Scope
1. **Architecture Documentation**
   - ADR accuracy and completeness
   - Architecture diagram currency
   - Design document consistency
   - Cross-reference validation

2. **Provider Documentation**
   - Provider-specific accuracy
   - API documentation currency
   - Integration guide completeness
   - Example validity

3. **Operations Documentation**
   - Runbook accuracy
   - Troubleshooting guide completeness
   - Monitoring guide currency
   - Deployment guide validity

4. **Developer Documentation**
   - Setup guide accuracy
   - Testing guide completeness
   - Contributing guide currency
   - Code examples validity

### Audit Procedures
- Use documentation-audit skill
- Check for stale documentation
- Validate cross-references
- Verify code examples
- Check for consistency with RULES.md
- Validate ADR references

### Audit Deliverables
- Audit report with findings
- Categorization (critical, high, medium, low)
- Remediation recommendations
- Priority ranking
- Owner assignment

### Remediation Tracking
- Issue creation for each finding
- Progress tracking
- Validation procedures
- Sign-off criteria

## Acceptance Criteria
- [ ] Documentation audit executed
- [ ] Audit report generated
- [ ] Findings categorized and prioritized
- [ ] Remediation issues created
- [ ] Progress tracking established
- [ ] Sign-off procedures defined

## References
- `.devin/skills/documentation-audit/SKILL.md`
- `docs/00-project/RULES.md`
- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/02-architecture/decisions/`
```

---

## Issue 22: [Docs] Sync RULES.md and REQUIREMENTS.md

**Title:** [Docs] Sync RULES.md and REQUIREMENTS.md

**Labels:** documentation, governance, sync

**Body:**
```markdown
## Summary
Synchronize RULES.md and REQUIREMENTS.md to ensure consistency and eliminate contradictions.

## Description
Perform synchronization between normative documents:

### Current State Analysis
- Compare RULES.md v6.1.5 with REQUIREMENTS.md v1.12
- Identify contradictions
- Find overlapping content
- Detect gaps in coverage
- Validate cross-references

### Synchronization Tasks
1. **Contradiction Resolution**
   - Identify conflicting requirements
   - Determine source of truth
   - Resolve contradictions
   - Document resolution decisions

2. **Content Consolidation**
   - Remove duplicate content
   - Consolidate overlapping sections
   - Improve cross-referencing
   - Enhance clarity

3. **Gap Analysis**
   - Identify missing requirements
   - Find undocumented rules
   - Validate completeness
   - Update as needed

4. **Cross-Reference Validation**
   - Validate ADR references
   - Check code references
   - Verify diagram references
   - Update broken links

### Version Management
- Update version numbers
- Document changes
- Update change history
- Communicate changes

## Acceptance Criteria
- [ ] RULES.md and REQUIREMENTS.md synchronized
- [ ] Contradictions resolved
- [ ] Duplicate content removed
- [ ] Gaps filled
- [ ] Cross-references validated
- [ ] Versions updated
- [ ] Changes documented

## References
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/02-architecture/decisions/`
```

---

## Issue 23: [Docs] Update Architecture Documents After Changes

**Title:** [Docs] Update Architecture Documents After Changes

**Labels:** documentation, architecture, update

**Body:**
```markdown
## Summary
Update architecture documents to reflect recent code changes and architectural decisions.

## Description
Review and update architecture documents for currency:

### Document Review List
1. **Architecture Decisions (ADRs)**
   - Review all ADRs for currency
   - Update status if needed
   - Add new ADRs for recent decisions
   - Supersede outdated ADRs

2. **Architecture Diagrams**
   - Update diagrams per ADR-040
   - Add new diagrams for new components
   - Remove obsolete diagrams
   - Validate diagram accuracy

3. **Architecture Policies**
   - Update policy documents
   - Reflect current practices
   - Remove outdated policies
   - Add new policies as needed

4. **Architecture Inventory**
   - Update current-state inventory
   - Reflect new components
   - Remove obsolete components
   - Validate layer boundaries

### Change Categories
- **New Components**: Add documentation
- **Modified Components**: Update documentation
- **Removed Components**: Archive/remove documentation
- **New Patterns**: Document patterns
- **Deprecated Patterns**: Mark as deprecated

### Validation Procedures
- Cross-reference validation
- Code comparison
- Diagram accuracy checks
- Policy compliance validation

## Acceptance Criteria
- [ ] Architecture documents reviewed
- [ ] ADRs updated for currency
- [ ] Diagrams updated per ADR-040
- [ ] Policies updated
- [ ] Inventory updated
- [ ] Validation procedures executed
- [ ] Changes documented

## References
- `docs/02-architecture/decisions/`
- `docs/02-architecture/diagrams/`
- `docs/02-architecture/current-state-inventory.md`
- `docs/02-architecture/decisions/ADR-040-diagram-governance.md`
```

---

## Issue 24: [Docs] Verify ADR Compliance with Current Code

**Title:** [Docs] Verify ADR Compliance with Current Code

**Labels:** documentation, architecture, compliance

**Body:**
```markdown
## Summary
Verify that current codebase complies with accepted ADRs and identify violations.

## Description
Perform comprehensive ADR compliance verification:

### ADR Compliance Categories
1. **Architecture ADRs**
   - ADR-005: Layer boundaries
   - ADR-010: Local-only deployment
   - ADR-040: Diagram governance

2. **Data Architecture ADRs**
   - ADR-002: Medallion architecture
   - ADR-014: Deterministic writes
   - ADR-018: Gold SCD Type 2

3. **Pipeline ADRs**
   - ADR-025: Pipeline config unification
   - ADR-026: Composite pipeline pattern
   - ADR-031: Load strategy

4. **Configuration ADRs**
   - ADR-027: DQ rules externalization
   - ADR-028: Filter rules externalization
   - ADR-029: Convention-based config
   - ADR-038: Enum externalization

5. **Integration ADRs**
   - ADR-032: Unified HTTP client
   - ADR-037: Schema source

### Verification Procedures
- Code inspection
- Architecture tests
- Configuration validation
- Diagram compliance checks
- Cross-reference validation

### Violation Categories
- **Critical**: Breaking architectural invariants
- **High**: Significant deviations
- **Medium**: Minor violations
- **Low**: Documentation gaps

### Remediation Planning
- Prioritize violations
- Create remediation issues
- Assign owners
- Define timelines
- Track progress

## Acceptance Criteria
- [ ] All ADRs reviewed for compliance
- [ ] Violations identified and categorized
- [ ] Remediation issues created
- [ ] Prioritization established
- [ ] Owners assigned
- [ ] Progress tracking defined

## References
- `docs/02-architecture/decisions/`
- `docs/00-project/RULES.md`
- `tests/architecture/`
- `docs/00-project/ai/memory/memory-py-audit-bot.md`
```

---

## Issue 25: [Docs] ChEMBL Normalization Deep Dive

**Title:** [Docs] ChEMBL Normalization Deep Dive

**Labels:** documentation, provider, chembl

**Body:**
```markdown
## Summary
Create a comprehensive deep dive guide for ChEMBL data normalization in BioETL.

## Description
Develop a ChEMBL-specific normalization guide:

### ChEMBL Data Overview
- ChEMBL API structure
- Available entity types (activity, molecule, target, mechanism, assay)
- Data characteristics
- Common data quality issues

### Normalization Procedures
1. **Activity Data Normalization**
   - Activity value standardization
   - Unit conversion
   - Assay type normalization
   - Target mapping
   - Relationship resolution

2. **Molecule Data Normalization**
   - Structure standardization
   - Identifier normalization
   - Property calculation
   - Name resolution
   - Synonym handling

3. **Target Data Normalization**
   - Protein identifier mapping
   - Gene name resolution
   - Organism normalization
   - Target classification
   - Cross-reference resolution

### Field Mapping Details
- API field to domain field mapping
- Transformation logic
- Validation rules
- Error handling
- Quarantine triggers

### Common Issues and Solutions
- Missing data handling
- Inconsistent identifiers
- Duplicate records
- Reference resolution failures
- Data type mismatches

### Testing Procedures
- Unit test patterns
- VCR cassette management
- Integration test scenarios
- Regression testing
- Data validation

## Acceptance Criteria
- [ ] ChEMBL normalization guide created in `docs/04-reference/providers/chembl/normalization-deep-dive.md`
- [ ] Data overview included
- [ ] Normalization procedures documented
- [ ] Field mapping detailed
- [ ] Common issues addressed
- [ ] Testing procedures explained

## References
- `src/bioetl/infrastructure/adapters/chembl/`
- `configs/entities/chembl/`
- `docs/04-reference/providers/chembl/`
- ChEMBL API documentation
```

---

## Issue 26: [Docs] Publication Processing Workflows

**Title:** [Docs] Publication Processing Workflows

**Labels:** documentation, provider, publication

**Body:**
```markdown
## Summary
Create comprehensive documentation for publication processing workflows across providers.

## Description
Develop publication processing workflow documentation:

### Publication Providers
- PubMed
- CrossRef
- OpenAlex
- SemanticScholar

### Publication Data Model
- Core publication fields
- Identifier systems (PMID, PMCID, DOI)
- Author metadata
- Journal/conference metadata
- Citation relationships

### Processing Workflow
1. **Data Acquisition**
   - API query construction
   - Pagination handling
   - Rate limiting
   - Error handling

2. **Data Normalization**
   - Identifier resolution
   - Author name normalization
   - Journal name standardization
   - Date format normalization
   - Citation processing

3. **Data Enrichment**
   - Cross-reference resolution
   - Citation graph construction
   - Subject classification
   - Affiliation normalization
   - Funding information extraction

4. **Quality Validation**
   - Required field validation
   - Identifier format validation
   - Date range validation
   - Citation consistency checks
   - Duplicate detection

### Composite Workflows
- Multi-provider merging
- Citation graph construction
- Author disambiguation
- Institution resolution
- Funding source tracking

### Common Issues
- Identifier collisions
- Author name ambiguity
- Journal name variations
- Citation inconsistencies
- Date format mismatches

## Acceptance Criteria
- [ ] Publication workflow guide created in `docs/04-reference/providers/publication/processing-workflows.md`
- [ ] All providers covered
- [ ] Data model documented
- [ ] Processing workflow detailed
- [ ] Composite workflows explained
- [ ] Common issues addressed

## References
- `src/bioetl/infrastructure/adapters/{pubmed,crossref,openalex,semanticscholar}/`
- `configs/entities/{provider}/publication.yaml`
- `docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md`
```

---

## Issue 27: [Docs] Ontology Governance Procedures

**Title:** [Docs] Ontology Governance Procedures

**Labels:** documentation, ontology, governance

**Body:**
```markdown
## Summary
Create comprehensive ontology governance procedures for BioETL.

## Description
Develop ontology governance documentation:

### Ontology Overview
- Used ontologies in BioETL
- Ontology sources and versions
- Ontology mapping strategies
- Ontology maintenance procedures

### Ontology Integration
1. **ChEMBL Target Classification**
   - Target family hierarchy
   - Protein classification
   - Organism taxonomy
   - Go term mapping

2. **Publication Classification**
   - Subject categories
   - MeSH terms
   - Field of study codes
   - Custom classification schemes

3. **Disease Ontology**
   - Disease classification
   - ICD mapping
   - MeSH disease terms
   - Custom disease categories

### Governance Procedures
- Ontology version management
- Ontology update procedures
- Impact assessment
- Migration procedures
- Rollback strategies

### Mapping Rules
- Identifier mapping rules
- Name normalization rules
- Hierarchy resolution rules
- Cross-ontology mapping
- Conflict resolution

### Quality Assurance
- Ontology validation
- Mapping consistency checks
- Coverage validation
- Error handling
- Quarantine procedures

### Documentation Requirements
- Ontology source documentation
- Mapping rule documentation
- Version change documentation
- Impact analysis documentation

## Acceptance Criteria
- [ ] Ontology governance guide created in `docs/04-reference/ontology/governance-procedures.md`
- [ ] Ontology overview included
- [ ] Integration procedures documented
- [ ] Governance procedures defined
- [ ] Mapping rules specified
- [ ] Quality assurance explained
- [ ] Documentation requirements listed

## References
- `src/bioetl/domain/ontology/` (if exists)
- ChEMBL target classification docs
- MeSH documentation
- Go term documentation
```

---

## Issue 28: [Docs] Identifier Family Policies

**Title:** [Docs] Identifier Family Policies

**Labels:** documentation, identifiers, governance

**Body:**
```markdown
## Summary
Create comprehensive identifier family policies for BioETL.

## Description
Develop identifier family policy documentation:

### Identifier Families
1. **Chemical Identifiers**
   - ChEMBL ID
   - PubChem CID
   - InChI / InChIKey
   - SMILES
   - CAS number

2. **Protein Identifiers**
   - UniProt accession
   - Gene name
   - RefSeq ID
   - Ensembl ID
   - PDB ID

3. **Publication Identifiers**
   - PMID
   - PMCID
   - DOI
   - OpenAlex ID
   - SemanticScholar ID

4. **Target Identifiers**
   - ChEMBL target ID
   - UniProt accession
   - Gene symbol
   - Organism-specific IDs

### Identifier Policies
- **Primary Identifier Selection**
  - Criteria for primary identifier
  - Fallback hierarchy
  - Conflict resolution
  - Version handling

- **Identifier Validation**
  - Format validation rules
  - Checksum validation
  - Authority validation
  - Deprecated identifier handling

- **Identifier Mapping**
  - Cross-reference mapping
  - Mapping confidence levels
  - Mapping provenance
  - Mapping maintenance

- **Identifier Normalization**
  - Case normalization
  - Whitespace handling
  - Prefix/suffix handling
  - Version stripping

### Implementation Guidelines
- Identifier storage format
- Identifier indexing strategy
- Identifier query patterns
- Identifier display format
- Identifier export format

### Common Issues
- Identifier collisions
- Deprecated identifiers
- Missing identifiers
- Inconsistent formats
- Mapping failures

## Acceptance Criteria
- [ ] Identifier family policies created in `docs/04-reference/identifiers/identifier-family-policies.md`
- [ ] All identifier families documented
- [ ] Policies defined for each family
- [ ] Implementation guidelines included
- [ ] Common issues addressed
- [ ] Cross-references to provider docs

## References
- `docs/04-reference/providers/`
- ChEMBL identifier docs
- UniProt identifier docs
- PubMed identifier docs
- DOI handbook
```

---

## Summary

Total issues created: 28

### Categories:
1. **Interactive Learning Materials (Cheatsheets)**: 4 issues
2. **Practical Guides (Tutorials)**: 4 issues
3. **Diagrams and Visualization**: 4 issues
4. **Troubleshooting and Operations**: 4 issues
5. **Integration Guides**: 4 issues
6. **Audit and Quality**: 4 issues
7. **Domain-Specific Guides**: 4 issues

### Usage Instructions

To create these issues in GitHub, use the following command for each issue:

```bash
gh issue create --title "Issue Title" --body "Issue Body" --label "label1,label2,label3"
```

Or create them manually using the GitHub web interface with the content provided above.
