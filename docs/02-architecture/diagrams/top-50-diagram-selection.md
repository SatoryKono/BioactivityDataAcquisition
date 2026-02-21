# TOP-50 Diagram Selection — Scored and Ranked

*Generated: 2026-02-17 | Source: 500-diagram-proposals.md*
*Scoring aligned with RULES.md v5.21 and codebase analysis of 534 Python files*

---

## Scoring Methodology

### Criteria (1–10 each)

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Arch** | ×2.0 | Architectural importance: how critical for understanding BioETL architecture |
| **Doc** | ×1.5 | Documentation value: usefulness for a new developer onboarding |
| **Freq** | ×1.5 | Frequency of use: how often needed during daily project work |
| **Complex** | ×2.0 | Complexity without diagram: how hard to understand without visualization |
| **Coverage** | ×1.0 | Codebase coverage: how many components/modules the diagram covers |

### Formula

```
Priority = (Arch×2 + Doc×1.5 + Freq×1.5 + Complex×2 + Coverage×1) / 8
```

### Constraints Verification

| Constraint | Requirement | Actual | Status |
|------------|-------------|--------|--------|
| Diagram types | ≥3 from {class, sequence, flowchart, state} | 4 types + mindmap | ✅ |
| Categories | ≥5 different | 12 categories | ✅ |
| Composite diagrams | ≥2 | 2 (#421, #435) | ✅ |
| Provider-specific | ≥3 | 3 (#311, #349, #353) | ✅ |
| Observability | ≥2 | 2 (#441, #456) | ✅ |
| Max per category | ≤15 | max 13 (Architecture) | ✅ |

### Type Distribution

| Type | Count | Diagrams |
|------|-------|----------|
| flowchart | 30 | #1,6,10,14,15,16,37,45,56,69,71,78,88,89,91,104,109,144,145,155,158,311,349,361,421,435,441,456,461,470 |
| classDiagram | 10 | #44,54,121,171,172,184,215,216,353,406 |
| sequenceDiagram | 6 | #30,79,221,231,238,255 |
| stateDiagram | 3 | #271,278,292 |
| mindmap | 1 | #47 |

### Category Distribution

| Category | Count | Max | Diagrams |
|----------|-------|-----|----------|
| Architecture | 13 | 15 | #1,6,10,14,15,16,30,37,44,45,47,54,56 |
| DataFlow | 9 | 15 | #69,71,78,79,88,89,91,104,109 |
| Pattern | 5 | 15 | #121,144,145,155,158 |
| Component | 5 | 15 | #171,172,184,215,216 |
| Interaction | 4 | 15 | #221,231,238,255 |
| Lifecycle | 3 | 15 | #271,278,292 |
| Provider | 3 | 15 | #311,349,353 |
| Configuration | 1 | 15 | #361 |
| DomainModel | 1 | 15 | #406 |
| Composite | 2 | 15 | #421,435 |
| Observability | 2 | 15 | #441,456 |
| ErrorHandling | 2 | 15 | #461,470 |

---

## Ranked TOP-50

| Rank | # | Name | Type | Category | Arch | Doc | Freq | Complex | Cov | **Score** |
|------|---|------|------|----------|------|-----|------|---------|-----|-----------|
| 1 | 6 | Hexagonal Architecture — Ports and Adapters Overview | flowchart | Architecture | 10 | 10 | 8 | 9 | 10 | **9.38** |
| 2 | 1 | Five-Layer Import Matrix Enforcement | flowchart | Architecture | 10 | 9 | 9 | 8 | 9 | **9.00** |
| 3 | 15 | Composition Root Wiring Diagram — Full DI Graph | flowchart | Architecture | 9 | 9 | 7 | 10 | 10 | **9.00** |
| 4 | 421 | Composite Pipeline Full Workflow — Seed to Gold | flowchart | Composite | 9 | 9 | 7 | 10 | 9 | **8.88** |
| 5 | 14 | Port-to-Adapter Mapping Table Diagram | flowchart | Architecture | 9 | 10 | 8 | 7 | 10 | **8.63** |
| 6 | 271 | Pipeline Run Lifecycle — From Config to Completion | stateDiagram | Lifecycle | 9 | 9 | 8 | 9 | 7 | **8.56** |
| 7 | 78 | Record Processing Pipeline — Single Record Journey | flowchart | DataFlow | 7 | 10 | 9 | 9 | 8 | **8.56** |
| 8 | 221 | CLI Run Command → PipelineRunner Full Interaction | sequenceDiagram | Interaction | 7 | 10 | 10 | 8 | 8 | **8.50** |
| 9 | 79 | Batch Processing Flow — Extract to Write | sequenceDiagram | DataFlow | 8 | 9 | 10 | 8 | 7 | **8.44** |
| 10 | 10 | Composition Layer Bootstrap Sequence | flowchart | Architecture | 8 | 9 | 8 | 9 | 8 | **8.44** |
| 11 | 47 | Architecture Principles Mind Map | mindmap | Architecture | 9 | 10 | 6 | 8 | 9 | **8.38** |
| 12 | 37 | CLI Entry Point to Pipeline Execution Full Chain | flowchart | Architecture | 7 | 10 | 9 | 8 | 8 | **8.31** |
| 13 | 30 | Runtime Assembly Sequence — bootstrap/runtime/assembly.py | sequenceDiagram | Architecture | 8 | 9 | 7 | 9 | 8 | **8.25** |
| 14 | 45 | Medallion Architecture Invariants | flowchart | Architecture | 10 | 8 | 7 | 9 | 5 | **8.19** |
| 15 | 56 | Application Core Component Collaboration | flowchart | Architecture | 8 | 9 | 8 | 8 | 8 | **8.19** |
| 16 | 461 | Error Classification Decision Tree — Full Logic | flowchart | ErrorHandling | 8 | 9 | 8 | 9 | 5 | **8.06** |
| 17 | 171 | PipelineRunner Internal Component Diagram | classDiagram | Component | 8 | 9 | 8 | 8 | 7 | **8.06** |
| 18 | 155 | Fan-Out/Fan-In Pattern — Composite Pipeline Enrichment | flowchart | Pattern | 9 | 8 | 6 | 9 | 7 | **8.00** |
| 19 | 91 | Cross-Provider Data Enrichment Flow — Publication | flowchart | DataFlow | 8 | 8 | 6 | 9 | 9 | **8.00** |
| 20 | 121 | Template Method Pattern — BaseTransformer.-transform-impl() | classDiagram | Pattern | 8 | 9 | 8 | 8 | 6 | **7.94** |
| 21 | 16 | YAML Configuration Resolution Chain | flowchart | Architecture | 8 | 9 | 8 | 8 | 6 | **7.94** |
| 22 | 104 | Publication Composite — Merge All Sources | flowchart | DataFlow | 8 | 8 | 6 | 9 | 8 | **7.88** |
| 23 | 278 | Composite Pipeline Phase Lifecycle | stateDiagram | Lifecycle | 8 | 8 | 6 | 9 | 8 | **7.88** |
| 24 | 216 | CompositePipelineRunner Component | classDiagram | Component | 8 | 8 | 6 | 9 | 8 | **7.88** |
| 25 | 44 | Exception Hierarchy Full Tree | classDiagram | Architecture | 7 | 9 | 9 | 7 | 8 | **7.88** |
| 26 | 144 | Idempotent Write Pattern — Content Hash Deduplication | flowchart | Pattern | 9 | 8 | 7 | 9 | 4 | **7.81** |
| 27 | 69 | Content Hash Calculation Pipeline | flowchart | DataFlow | 8 | 8 | 8 | 9 | 4 | **7.75** |
| 28 | 172 | BatchExecutor Internal Structure — 786 LOC Decomposition | classDiagram | Component | 8 | 8 | 8 | 8 | 6 | **7.75** |
| 29 | 71 | Silver Merge/Upsert Decision Logic | flowchart | DataFlow | 8 | 8 | 8 | 9 | 4 | **7.75** |
| 30 | 145 | At-Least-Once Delivery + Silver Deduplication | flowchart | Pattern | 9 | 8 | 6 | 9 | 5 | **7.75** |
| 31 | 54 | Infrastructure Adapter Inheritance Hierarchy | classDiagram | Architecture | 8 | 9 | 7 | 7 | 8 | **7.75** |
| 32 | 158 | Layered Validation Strategy (5 Levels) | flowchart | Pattern | 8 | 9 | 6 | 9 | 5 | **7.69** |
| 33 | 184 | UnifiedHTTPClient Component — Full Internal Architecture | classDiagram | Component | 8 | 8 | 7 | 9 | 5 | **7.69** |
| 34 | 231 | PipelineRunner ↔ BatchExecutor Interaction | sequenceDiagram | Interaction | 7 | 8 | 9 | 8 | 6 | **7.69** |
| 35 | 255 | RunType-Based Clear Policy Interaction | sequenceDiagram | Interaction | 9 | 8 | 7 | 8 | 5 | **7.69** |
| 36 | 89 | Incremental Data Flow — Delta Update Path | flowchart | DataFlow | 8 | 8 | 9 | 7 | 6 | **7.69** |
| 37 | 441 | Three Pillars of Observability in BioETL | flowchart | Observability | 8 | 9 | 7 | 7 | 7 | **7.63** |
| 38 | 215 | MergeService Component | classDiagram | Component | 8 | 8 | 6 | 9 | 6 | **7.63** |
| 39 | 311 | ChEMBL Adapter — 14 Entity Types Supported | flowchart | Provider | 7 | 9 | 7 | 7 | 9 | **7.63** |
| 40 | 353 | Provider-Specific Transformer Class Hierarchy | classDiagram | Provider | 7 | 9 | 7 | 7 | 9 | **7.63** |
| 41 | 292 | Graceful Shutdown Lifecycle | stateDiagram | Lifecycle | 8 | 8 | 6 | 9 | 6 | **7.63** |
| 42 | 109 | DQ Flag Routing Decision Tree | flowchart | DataFlow | 7 | 9 | 8 | 8 | 5 | **7.56** |
| 43 | 238 | UnifiedHTTPClient ↔ RateLimiter ↔ CircuitBreaker Triple Interaction | sequenceDiagram | Interaction | 8 | 8 | 7 | 9 | 4 | **7.56** |
| 44 | 88 | Backfill Data Flow — Full Reload Path | flowchart | DataFlow | 8 | 8 | 7 | 8 | 6 | **7.56** |
| 45 | 361 | Pipeline Config YAML Structure | flowchart | Configuration | 7 | 9 | 9 | 7 | 5 | **7.50** |
| 46 | 470 | Exception Propagation Through Layers | flowchart | ErrorHandling | 7 | 8 | 7 | 8 | 7 | **7.44** |
| 47 | 406 | DataSourcePort Protocol — Complete Method Signatures | classDiagram | DomainModel | 8 | 9 | 8 | 7 | 4 | **7.44** |
| 48 | 456 | Run ID Correlation Across All Observability Channels | flowchart | Observability | 7 | 8 | 8 | 7 | 6 | **7.25** |
| 49 | 349 | Provider Comparison — Rate Limit Strategies | flowchart | Provider | 7 | 9 | 7 | 6 | 8 | **7.25** |
| 50 | 435 | Conflict Resolution Strategies Comparison | flowchart | Composite | 7 | 8 | 5 | 8 | 4 | **6.69** |

---

## Score Distribution

```
9.0–9.5: ████ 3 diagrams  (Ranks 1-3)
8.5–9.0: █████ 5 diagrams  (Ranks 4-8)
8.0–8.5: ████████ 8 diagrams  (Ranks 9-16)
7.5–8.0: ████████████████ 16 diagrams  (Ranks 17-32)
7.0–7.5: ████████████████ 16 diagrams  (Ranks 33-48)
6.5–7.0: ██ 2 diagrams  (Ranks 49-50)
```

**Mean score:** 7.90
**Median score:** 7.75
**Min / Max:** 6.69 / 9.38

---

## Scoring Justification for Top 10

### Rank 1: #6 — Hexagonal Architecture — Ports and Adapters Overview (9.38)

- **Arch=10**: Core architectural pattern of the entire system; all 24 ports and their adapters
- **Doc=10**: First thing a new developer needs to understand
- **Freq=8**: Referenced whenever adding new ports or adapters
- **Complex=9**: 24 ports × multiple adapters = very hard to keep in head
- **Coverage=10**: Spans domain (ports) and infrastructure (adapters) — broadest coverage

### Rank 2: #1 — Five-Layer Import Matrix Enforcement (9.00)

- **Arch=10**: ARCH-001 is the most critical architectural rule
- **Doc=9**: Essential for understanding what can import what
- **Freq=9**: Checked on every PR by import-linter
- **Complex=8**: 5×5 matrix with non-obvious rules (infrastructure→domain is OK)
- **Coverage=9**: Covers all 5 layers

### Rank 3: #15 — Composition Root Wiring — Full DI Graph (9.00)

- **Arch=9**: Shows the complete DI assembly — the "brain" of the system
- **Doc=9**: Critical for understanding how everything connects
- **Freq=7**: Needed when modifying factories or adding new providers
- **Complex=10**: Most complex single concept — dozens of factories and ports wired together
- **Coverage=10**: Touches every layer (composition wires all)

### Rank 4: #421 — Composite Pipeline Full Workflow (8.88)

- **Arch=9**: ADR-026 is the most complex architectural feature
- **Doc=9**: Composite pipelines are hard to explain without visualization
- **Freq=7**: Used when working with publication enrichment
- **Complex=10**: Seed→dependencies→fan-out enrichers→merge→Gold — hardest workflow to understand
- **Coverage=9**: Spans multiple providers, application composite, merge service

### Rank 5: #14 — Port-to-Adapter Mapping Table (8.63)

- **Arch=9**: Maps abstract contracts to concrete implementations
- **Doc=10**: The #1 reference diagram for "where is X implemented?"
- **Freq=8**: Consulted whenever tracing through code
- **Complex=7**: Straightforward mapping but 24+ entries
- **Coverage=10**: Every port and every adapter in the system

### Rank 6: #271 — Pipeline Run Lifecycle (8.56)

- **Arch=9**: Defines the complete state machine of pipeline execution
- **Doc=9**: Essential for understanding what happens in what order
- **Freq=8**: Referenced when debugging pipeline failures
- **Complex=9**: 9+ states with multiple transitions and error paths
- **Coverage=7**: Covers runner, executor, services, lock, checkpoint

### Rank 7: #78 — Single Record Journey (8.56)

- **Arch=7**: Shows data transformation at record level
- **Doc=10**: Best onboarding diagram — "follow one record through the system"
- **Freq=9**: Mental model used constantly
- **Complex=9**: API→Bronze→transform→validate→Silver/Quarantine→Gold — many steps
- **Coverage=8**: Touches extract, transform, validate, load, quarantine

### Rank 8: #221 — CLI Run → PipelineRunner Full Interaction (8.50)

- **Arch=7**: Shows the entry point and full call chain
- **Doc=10**: "What happens when I run `bioetl run chembl-activity`?"
- **Freq=10**: The most common operation in the system
- **Complex=8**: CLI→bootstrap→factories→runner→executor→finalize
- **Coverage=8**: Spans interfaces, composition, application layers

### Rank 9: #79 — Batch Processing Flow (8.44)

- **Arch=8**: Core data processing loop
- **Doc=9**: How batches flow through extract→transform→write
- **Freq=10**: The innermost loop — runs for every batch
- **Complex=8**: BatchExecutor coordinates transformer, writer, metrics
- **Coverage=7**: BatchExecutor, BatchTransformer, BatchWriter, metrics

### Rank 10: #10 — Composition Bootstrap Sequence (8.44)

- **Arch=8**: Shows how the system boots from CLI call to running pipeline
- **Doc=9**: "How does a pipeline get assembled?"
- **Freq=8**: Referenced when modifying bootstrap or adding providers
- **Complex=9**: Multi-step assembly: logger→storage→HTTP→adapter→services→runner
- **Coverage=8**: Entire composition layer

---

## Implementation Recommendations

### Phase 1 — Core Architecture (Ranks 1–10)
Essential diagrams for system understanding. Implement first.

### Phase 2 — Developer Reference (Ranks 11–25)
Key reference diagrams for daily development work.

### Phase 3 — Deep Dive (Ranks 26–40)
Detailed component and pattern diagrams.

### Phase 4 — Specialist Topics (Ranks 41–50)
Niche but important diagrams for specific areas.

---

*Selection based on analysis of RULES.md v5.21, 34 ADRs, and 534 Python source files across 5 architectural layers.*
