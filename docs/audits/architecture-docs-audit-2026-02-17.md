# Architecture & Documentation Audit Report

**Project:** BioETL (BioactivityDataAcquisition)
**Date:** 2026-02-17
**Auditor:** External independent auditor
**Scope:** Full documentation system audit (docs/, configs/, src/ cross-reference)
**RULES.md version:** v5.19 (claimed) / v5.20 (actual header)
**README version:** 5.14.0

---

## Executive Summary

The BioETL documentation system is **mature and comprehensive** for a local-first data platform.
534 Python source files, 273 markdown docs, 34 ADRs, 156 formal requirements, and 121 YAML configs
form a well-structured governance framework. However, this audit identifies **6 critical issues**,
**11 high-severity issues**, and **14 medium-severity issues** across seven evaluation categories.

**Overall Score: 7.4 / 10 (WARN)**

| Category | Score (0-10) |
|---|---|
| Architecture clarity | 8.5 |
| Consistency | 6.5 |
| Completeness | 7.0 |
| Operational readiness | 8.0 |
| Maintainability | 6.5 |

---

## 1. Architectural Consistency

### 1.1 Medallion Architecture (Bronze/Silver/Gold)

**Status: CONSISTENT with minor drift**

The Medallion pattern is correctly and consistently described across:
- RULES.md §2 (canonical)
- ADR-001 (Delta Lake choice)
- ADR-002 (Medallion pattern)
- REQUIREMENTS.md REQ-DATA-001..012
- `data-layers.md`, `data-flow.md`

| Aspect | RULES.md | ADR | Code | Verdict |
|---|---|---|---|---|
| Bronze: JSONL+zstd | §2.1 | ADR-002 | `bronze-writer.py` | CONSISTENT |
| Silver: Delta Lake | §2.1 | ADR-001 | `silver-writer.py` | CONSISTENT |
| Gold: Strict validation | §2.7 | ADR-018 | `gold-writer.py` | CONSISTENT |
| Clear policy | §2.4.2 | ADR-012 | `medallion-lifecycle.py` | CONSISTENT |
| Partitioning | §2.4.3 | - | configs | CONSISTENT |

**Issue MEDAL-001 (MEDIUM):** Medallion Architecture is explained in **53 separate files** across
docs/. While no contradictions were found, the concept is fragmented. Readers encounter partial
descriptions in rules-summary.md, glossary.md, overview.md, data-layers.md, data-flow.md, and
multiple ADRs without a single canonical "Medallion Architecture Guide" that ties everything together.

### 1.2 Ports & Adapters (Hexagonal Architecture)

**Status: CONSISTENT**

Layer documentation (`01-domain-layer.md` through `05-composition-layer.md`) accurately reflects
the actual `src/bioetl/` directory structure. Import matrix (ARCH-001) is correctly documented
in RULES.md, ai-selfreview-rules.md, and architecture tests.

| Layer | Doc accurate | Module paths correct | Port count verified |
|---|---|---|---|
| Domain | YES | YES | 25 ports verified |
| Application | YES (1 path issue) | 1 error found | 23 transformers verified |
| Infrastructure | YES | YES | 7 adapters verified |
| Composition | YES | YES | 12 factories verified |
| Interfaces | YES | YES | 17 CLI commands verified |

**Issue ARCH-001 (HIGH):** `02-application-layer.md` line 144 incorrectly places
`MedallionLifecycleService` under `application/core/` — actual location is
`application/services/medallion-lifecycle.py`.

### 1.3 Local-Only Deployment (ADR-010)

**Status: CONSISTENT**

ADR-010 is correctly enforced:
- MemoryLock (not Redis) in `infrastructure/locking/memory-lock.py`
- Filesystem storage, no external services
- CLI execution model, no orchestrator dependency
- Confirmed in RULES.md, REQUIREMENTS.md, glossary.md

No contradictions found.

### 1.4 Deterministic Writes (ADR-014)

**Status: CONSISTENT**

`sort-by` requirement in configs, hash-based deterministic jitter, single timestamp source —
all documented in ADR-014 and enforced via `03-file-policy.md` mandatory config fields.

### 1.5 Circuit Breaker & Retry

**Status: CONSISTENT but FRAGMENTED**

**Issue CB-001 (MEDIUM):** Circuit Breaker parameters (threshold=5, recovery=300s) are defined
in ADR-007 but referenced without values in 7 other files. No consolidated
"Circuit Breaker Configuration Reference" exists in docs/03-guides/.

### 1.6 DQ & Quarantine Policy

**Status: CONSISTENT but DUPLICATED**

DQ thresholds (soft=5%, hard=20%) are copy-pasted identically across 7 files:
dq-configuration.md, pipeline-configuration.md, CONFIG-GUIDE.md, metrics-monitoring.md,
ADR-026, ADR-033, ADR-016.

**Issue DQ-001 (MEDIUM):** No single canonical DQ reference. Changes to thresholds would
require updating 7 files.

### 1.7 Locking Model (MemoryLock)

**Status: CONSISTENT**

ADR-003 is the canonical source (TTL=90s, heartbeat=30s, max-duration=4h).
42 files reference MemoryLock but references are complementary (operational vs. architectural).

### 1.8 Composite Pipeline Pattern (ADR-026)

**Status: CONSISTENT but INCOMPLETE documentation**

Composite pipeline architecture (seed -> enrich -> merge) is well-documented in ADR-026
and `05-composition-layer.md`. However:

**Issue COMP-001 (HIGH):** Composite pipeline specs exist only for 3 of 5 configured composites.
Missing: `composite/activity-spec.md` and `composite/assay-spec.md`.

### 1.9 Naming Policy (02-naming-policy.md)

**Status: CONSISTENT**

Naming policy correctly implements ADR-024 (Entity Naming Unification):
- `{Provider}{CanonicalTerm}` class naming
- `{provider}-{entity}` pipeline IDs
- `{Provider}{CanonicalTerm}GoldSchema` for Pandera schemas
- Exception registry in `configs/naming-exceptions.yaml`

---

## 2. ADR Consistency

### 2.1 ADR Coverage Matrix

| ADR | Status | Reflected in Docs | Reflected in Code | Notes |
|---|---|---|---|---|
| ADR-001 | Accepted | YES | YES | Delta Lake |
| ADR-002 | Accepted | YES | YES | Medallion |
| ADR-003 | Accepted | YES | YES | MemoryLock |
| ADR-004 | Accepted | YES | YES | Pydantic choice |
| ADR-005 | Accepted | YES | YES | Composition layer |
| ADR-006 | Accepted | YES | YES | Logger/Metrics ports |
| ADR-007 | Accepted | YES | YES | Circuit Breaker |
| ADR-008 | Accepted | YES | YES | Graceful shutdown |
| ADR-009 | Accepted | YES | YES | Paginated fetcher |
| ADR-010 | Accepted | YES | YES | Local-only |
| ADR-011 | Accepted | YES | YES | Watermark removed |
| ADR-012 | Accepted | YES | YES | Storage clear |
| ADR-013 | Accepted | YES | YES | Async cleanup |
| ADR-014 | Accepted | YES | YES | Deterministic writes |
| ADR-015 | Accepted | YES | YES | Services lifecycle |
| ADR-016 | Accepted | YES | YES | Error handling |
| ADR-017 | Accepted | YES | YES | Observability |
| ADR-018 | Accepted | YES | YES | Gold validation |
| ADR-019 | Accepted | YES | YES | Obs port enforcement |
| ADR-020 | Accepted | YES | YES | BasePipeline decomp |
| ADR-021 | Accepted | YES | YES | DDD aggregates |
| ADR-022 | Accepted | YES | YES | Tracing NoOp |
| ADR-023 | Accepted | YES | YES | Entity type patterns |
| ADR-024 | Accepted | YES | YES | Naming unification |
| ADR-025 | Accepted | YES | YES | Config unification |
| ADR-026 | Accepted | PARTIAL | YES | Composite pipeline (2 specs missing) |
| ADR-027 | Accepted | YES | YES | DQ externalization |
| ADR-028 | Accepted | YES | YES | Filter externalization |
| ADR-029 | Accepted | YES | YES | Output metadata |
| ADR-030 | Accepted | YES | YES | Pub pagination |
| ADR-031 | Accepted | YES | YES | Loading strategy |
| ADR-032 | Accepted | YES | YES | Unified HTTP client |
| ADR-033 | **Proposed** | YES | PARTIAL | Pub validation (status anomaly) |
| ADR-034 | Accepted | YES | YES | Schema-domain pairs |

### 2.2 Issues Found

**Issue ADR-001 (HIGH): ADR-033 status anomaly**
ADR-033 (Publication Validation Strategy) remains in "Proposed" status despite containing
detailed implementation references to existing code paths. If validation infrastructure is
production-ready, status should be updated to "Accepted". If not implemented, documentation
should clarify what remains to be done.

**Issue ADR-002 (MEDIUM): 00-map.md ADR range mismatch**
Line 60: `decisions/ # ADRs (ADR-001..032)` — should be `ADR-001..034`.
Two ADRs (033, 034) are not reflected in the directory tree comment.

**Issue ADR-003 (MEDIUM): Archived ADR confusion**
`docs/99-archive/decisions/` contains 5 ADR files including multiple versions of ADR-030
and ADR-031. No clear indication which is the canonical version vs. which is superseded.
Files in archive:
- `ADR-030-api-offset-stability.md`
- `ADR-030-openalex-offset-stability.md`
- `ADR-030-publication-field-unification-SUPERSEDED.md`
- `ADR-030-publication-field-unification.md`
- `ADR-031-full-scan-loading.md`

### 2.3 Missing ADR Coverage

No missing ADR coverage detected. All 34 ADRs are present in:
- `docs/02-architecture/decisions/` (filesystem)
- `docs/02-architecture/decisions/README.md` (index)
- RULES.md Appendix F (registry)

### 2.4 Conflicting ADR References

No conflicting references found. Cross-references between ADRs are valid.

### 2.5 Obsolete ADR Mentions

Watermark mechanism (ADR-011 removed) — confirmed correctly documented as removed.
No active references to watermark-based loading found.

---

## 3. Naming & Structure Compliance

### 3.1 src/ to docs/ Structure Mapping

| src/ Directory | docs/ Coverage | Status |
|---|---|---|
| domain/ | 01-domain-layer.md | COMPLETE |
| application/ | 02-application-layer.md | COMPLETE (1 path error) |
| infrastructure/ | 03-infrastructure-layer.md | COMPLETE |
| composition/ | 05-composition-layer.md | COMPLETE |
| interfaces/ | 04-interfaces-layer.md | COMPLETE |

### 3.2 Provider/Entity Naming

All 7 providers follow naming policy:
- chembl: 14 entity configs (snake-case)
- pubchem: 1 (compound)
- uniprot: 2 (protein, idmapping)
- pubmed: 1 (publication)
- crossref: 1 (publication)
- openalex: 1 (publication)
- semanticscholar: 1 (publication)

### 3.3 Config Naming

Pipeline configs follow `configs/pipelines/{provider}/{entity}.yaml` convention.
DQ configs follow `configs/quality/entities/{provider}/{entity}.yaml` convention.
Filter configs follow `configs/filters/entities/{provider}/{entity}.yaml` convention.

### 3.4 Documentation Prefix Compliance

| Directory | Expected Prefix | Actual | Status |
|---|---|---|---|
| 00-project | NN-* | YES | COMPLIANT |
| 01-requirements | - | YES | COMPLIANT |
| 02-architecture | NN-* layers | YES | COMPLIANT |
| 03-guides | descriptive | YES | COMPLIANT |
| 04-reference | NN-* per provider | YES | COMPLIANT |
| 05-operations | descriptive | YES | COMPLIANT |
| 99-archive | - | YES | COMPLIANT |

### 3.5 MUST-Rule Violations

**Issue NAME-001 (HIGH): Missing tissue pipeline documentation**
`chembl-tissue` has a config at `configs/pipelines/chembl/tissue.yaml` but:
- No spec in `docs/04-reference/pipelines/chembl/`
- No provider doc in `docs/04-reference/providers/chembl/tissue.md`
Per 04-extending-bioetl.md, all pipelines MUST have documentation.

### 3.6 SHOULD-Rule Violations

**Issue NAME-002 (MEDIUM): Duplicate numbering in chembl pipeline specs**
`docs/04-reference/pipelines/chembl/` contains duplicate-numbered files:
- 01-protein-class AND 15-protein-class
- 10-target-component AND 16-target-component
- 12-publication-similarity AND 17-publication-similarity
- 11-publication-term AND 18-publication-term

This creates navigation confusion. One set should be canonical, the other removed.

---

## 4. Pipeline Documentation Completeness

### 4.1 Pipeline Coverage Matrix

| Pipeline | Config | Spec Doc | Provider Doc | Transformer | Schema | Status |
|---|---|---|---|---|---|---|
| chembl-activity | YES | YES | YES | YES | YES | COMPLETE |
| chembl-assay | YES | YES | YES | YES | YES | COMPLETE |
| chembl-molecule | YES | YES | YES | YES | YES | COMPLETE |
| chembl-target | YES | YES | YES | YES | YES | COMPLETE |
| chembl-cell-line | YES | YES | YES | YES | YES | COMPLETE |
| chembl-protein-class | YES | YES | YES | YES | YES | COMPLETE |
| chembl-publication | YES | YES | YES | YES | YES | COMPLETE |
| chembl-assay-parameters | YES | YES | YES | YES | YES | COMPLETE |
| chembl-compound-record | YES | YES | YES | YES | YES | COMPLETE |
| chembl-target-component | YES | YES | YES | YES | YES | COMPLETE |
| chembl-publication-term | YES | YES | YES | YES | YES | COMPLETE |
| chembl-publication-similarity | YES | YES | YES | YES | YES | COMPLETE |
| chembl-subcellular-fraction | YES | YES | YES | YES | YES | COMPLETE |
| **chembl-tissue** | YES | **NO** | **NO** | YES | YES | **INCOMPLETE** |
| pubchem-compound | YES | YES | YES | YES | YES | COMPLETE |
| uniprot-protein | YES | YES | YES | YES | YES | COMPLETE |
| uniprot-idmapping | YES | YES | YES | YES | YES | COMPLETE |
| pubmed-publication | YES | YES | YES | YES | YES | COMPLETE |
| crossref-publication | YES | YES | YES | YES | YES | COMPLETE |
| openalex-publication | YES | YES | YES | YES | YES | COMPLETE |
| semanticscholar-publication | YES | YES | YES | YES | YES | COMPLETE |
| **composite-publication** | YES | YES | - | YES | YES | COMPLETE |
| **composite-molecule** | YES | YES | - | YES | YES | COMPLETE |
| **composite-target** | YES | YES | - | YES | YES | COMPLETE |
| **composite-activity** | YES | **NO** | - | YES | YES | **INCOMPLETE** |
| **composite-assay** | YES | **NO** | - | YES | YES | **INCOMPLETE** |

### 4.2 Documentation Section Coverage

Based on the pipeline spec template (chembl-activity as reference), each spec SHOULD contain:

| Section | Required | Coverage across documented pipelines |
|---|---|---|
| Overview table | MUST | 100% |
| Description | MUST | 100% |
| Data Schema (Silver) | MUST | ~90% |
| Data Quality Rules | MUST | ~85% |
| Storage Layers | MUST | 100% |
| CLI Usage | SHOULD | ~80% |
| Related Files | SHOULD | ~90% |
| Write Strategy | SHOULD | ~60% |
| Partitioning Strategy | SHOULD | ~40% |
| Idempotency Guarantees | SHOULD | ~30% |
| Retry/CB Behavior | MAY | ~20% |
| Backfill Strategy | MAY | ~30% |
| Known Edge Cases | MAY | ~10% |

**Issue PIPE-001 (HIGH):** Idempotency guarantees, retry behavior, and known edge cases are
documented in fewer than 30% of pipeline specs. These sections are important for operational
understanding.

### 4.3 Undocumented Pipelines

1. `chembl-tissue` — config exists, no spec doc, no provider doc
2. `composite-activity` — config exists, no spec doc
3. `composite-assay` — config exists, no spec doc

### 4.4 Partially Documented Pipelines

All documented pipelines have at minimum: Overview, Description, Schema, and Storage sections.
Most lack: Idempotency, Retry/CB, Edge Cases sections.

---

## 5. Duplication and Fragmentation

### 5.1 Duplicate Content Hotspots

| Concept | Files Describing It | Canonical Source | Recommendation |
|---|---|---|---|
| Medallion Architecture | 53 | ADR-002 | Add cross-ref hub |
| DQ Thresholds (5%/20%) | 7 | dq-configuration.md | Consolidate to 1 ref |
| Circuit Breaker params | 8 | ADR-007 | Add config ref guide |
| MemoryLock details | 42 | ADR-003 | OK (complementary refs) |
| Import Matrix | 4 | RULES.md §1.1 | OK (governance + tests) |

### 5.2 Directory Fragmentation

**Issue FRAG-001 (CRITICAL): Dual audit directories**
- `docs/audits/` (10 files)
- `docs/audit/` (2 files)
- Both contain reports for 2026-02-17
- `docs/audits/architecture-audit-2026-02-17.md` (10,895 bytes)
- `docs/audit/etl-architecture-audit-2026-02-17.md` (8,424 bytes)
- These are separate reports for the same date in different directories

**Recommendation:** Consolidate `docs/audit/` into `docs/audits/`. One canonical audit directory.

**Issue FRAG-002 (MEDIUM): docs/03-data-model/ vs docs/analysis/**
- `docs/03-data-model/` — 6 files (field-level refactoring plans)
- `docs/analysis/` — 8 files (validation matrices)
- Weak separation, both contain "-matrix" and "-plan" files
- Neither directory is referenced in `00-map.md` directory tree

**Recommendation:** Merge into a single `docs/03-data-model/` with subdirectories.

**Issue FRAG-003 (HIGH): Archive bloat**
`docs/99-archive/` contains 29 files including:
- 6 merged source code dumps (total ~184K lines): `documentation-merged.md` (73K lines),
  `domain-merged.md` (34K lines), `infrastructure-merged.md` (31K lines),
  `application-merged.md` (30K lines), `composition-merged.md` (10K lines),
  `configs-merged.md` (6K lines)
- These are NOT documentation — they are full source code dumps in markdown
- 5 superseded ADR versions without clear canonical indicators

**Recommendation:** Remove merged*.md files. Add SUPERSEDED headers to archived ADRs.

### 5.3 Canonical Source of Truth Recommendations

| Topic | Current Canonical | Recommended Action |
|---|---|---|
| Architecture rules | RULES.md | Keep (verified canonical) |
| ADR decisions | docs/02-architecture/decisions/ | Keep (verified complete) |
| Pipeline configs | configs/pipelines/ | Keep (verified canonical) |
| DQ thresholds | Scattered across 7 files | Make dq-configuration.md the single source |
| Naming policy | 02-naming-policy.md | Keep (verified canonical) |
| File policy | 03-file-policy.md | Keep (verified canonical) |
| Glossary | glossary.md | Keep (verified comprehensive) |

---

## 6. Numerical Metrics Accuracy

### 6.1 Metrics Cross-Reference

| Metric | Claimed (00-map.md) | Actual (measured) | Delta | Status |
|---|---|---|---|---|
| Python files | ~1,114 | 534 (src/bioetl) + 586 (tests) = 1,120 | +6 | APPROXIMATE OK |
| LOC | ~115,656 | 116,120 (src) + 183,799 (tests) = ~300K total; src-only = 116,120 | +464 src | APPROXIMATE OK |
| Tests | ~11,985 | 586 test files | Unclear metric (files vs functions) | **AMBIGUOUS** |
| ADR count | 34 | 34 | 0 | EXACT MATCH |
| Pipeline configs | 26 (21+5) | 26 (21+5) | 0 | EXACT MATCH |
| Requirements | 156 | 156 (REQUIREMENTS.md) | 0 | EXACT MATCH |

### 6.2 Issues Found

**Issue METRIC-001 (CRITICAL): Coverage threshold mismatch**
- `rules-summary.md` lines 108, 128: states "Coverage >= 80%"
- RULES.md §4.2: states ">= 85%"
- ai-selfreview-rules.md TEST-001: states ">= 85%"
- REQUIREMENTS.md REQ-TEST-001: states ">= 85%"
- **The canonical value is 85%.** rules-summary.md is wrong.

**Issue METRIC-002 (HIGH): TOOLS.md sync version stale**
- TOOLS.md header: "Synced with RULES.md v5.19 (2026-01-07)"
- Current RULES.md: v5.20 (2026-02-17)
- Drift: 40+ days

**Issue METRIC-003 (MEDIUM): Test count metric ambiguous**
00-map.md claims "~11,985 tests" but doesn't specify if this means test functions,
test files (586), or assertions. The metric is unverifiable without clarification.

**Issue METRIC-004 (MEDIUM): RULES.md version inconsistency**
- 00-map.md line 3: "Synced with RULES.md v5.19"
- 00-map.md line 47: "RULES.md # Canonical rules document (v5.19)"
- RULES.md actual header: v5.20 (2026-02-17)
- ai-selfreview-rules.md: "Synced with RULES.md v5.20 (2026-02-17)"
- **00-map.md references v5.19 while actual is v5.20**

**Issue METRIC-005 (MEDIUM): BatchExecutor LOC drift**
- `02-application-layer.md` line 143: "786 LOC"
- Actual `batch-executor.py`: 774 lines
- Minor drift from refactoring

**Issue METRIC-006 (LOW): Diagram count stale**
- 00-map.md Document Status table: "34 diagrams Mermaid"
- Actual in `docs/02-architecture/diagrams/`: 50+ files
- Significant undercount

---

## 7. Production-Grade Readiness

### 7.1 Can a new engineer understand the architecture in 1 day?

**YES, with caveats.**

Strengths:
- 00-map.md provides excellent navigation
- Glossary defines all key terms
- Layer docs (01-05) accurately describe the architecture
- ADR decisions explain "why" behind each choice

Weaknesses:
- 273 markdown files is overwhelming without guided reading order
- Medallion architecture explained in 53 files without a single unified guide
- No "Architecture Quick Start" document exists (00-overview.md is detailed, not quick)
- Language mix (Russian/English) may slow non-Russian speakers

**Score: 7/10**

### 7.2 Is documentation sufficient for audit?

**YES.**

The documentation system supports audit:
- 156 formal testable requirements (REQ-*)
- 34 ADRs with status tracking
- Import matrix with detection scripts
- Self-review rules (ai-selfreview-rules.md) with scoring
- Architecture tests (tests/architecture/)

**Score: 9/10**

### 7.3 Can refactoring be done safely using only docs?

**MOSTLY YES.**

- Import matrix clearly defines allowed dependencies
- ADR-020 documents the BasePipeline decomposition pattern
- 04-extending-bioetl.md provides pipeline scaffolding guide
- Config schema validation via JSON Schema

Gaps:
- Some modules in src/ not covered in architecture docs (internal implementation details)
- Edge cases in pipeline specs documented in <30% of pipelines
- No "Refactoring Safety Guide" exists

**Score: 7/10**

### 7.4 Does documentation match a mature data platform?

**YES, above average for the category.**

The documentation exceeds typical data platform standards:
- Formal requirements with RFC 2119 severity levels
- ADR-based decision tracking
- Operational runbooks (16 active)
- Data contract versioning with deprecation policy
- DR procedures (RPO/RTO defined)
- Self-review automation rules

**Score: 8/10**

### 7.5 Summary Scores

| Category | Score | Rationale |
|---|---|---|
| Architecture clarity | 8.5 | Hexagonal+Medallion well-documented; layer docs accurate |
| Consistency | 6.5 | Coverage % mismatch; version drift; DQ threshold duplication |
| Completeness | 7.0 | 3 pipelines undocumented; edge cases sparse; composite gaps |
| Operational readiness | 8.0 | 16 runbooks; DR defined; monitoring guide exists |
| Maintainability | 6.5 | 53-file Medallion fragmentation; dual audit dirs; archive bloat |
| **Overall** | **7.4** | **WARN — actionable issues but no blockers** |

---

## 8. Remediation Plan

### 8.1 Structural Problem Map

```
CRITICAL (6 issues)
├── METRIC-001: rules-summary.md coverage 80% vs canonical 85%
├── FRAG-001: Dual audit directories (docs/audit/ + docs/audits/)
├── FRAG-003: Archive contains 184K lines of source code dumps
├── ADR-001 (§2.2): ADR-033 "Proposed" status anomaly
├── NAME-001: chembl-tissue pipeline undocumented
└── COMP-001: composite-activity + composite-assay specs missing

HIGH (11 issues)
├── ARCH-001: MedallionLifecycleService path error in 02-application-layer.md
├── METRIC-002: TOOLS.md sync version 40 days stale
├── METRIC-004: 00-map.md references RULES.md v5.19, actual is v5.20
├── PIPE-001: <30% of pipeline specs document idempotency/retry/edge cases
├── NAME-002: Duplicate numbering in chembl pipeline specs
├── FRAG-002: docs/03-data-model/ vs docs/analysis/ weak separation
├── 00-map.md Python file count scope unclear (src vs src+tests)
├── 00-map.md LOC claim drifted (+464 lines)
├── 00-map.md diagram count stale (34 claimed, 50+ actual)
├── ADR-002 (§2.2): 00-map.md ADR range says "001..032", should be "001..034"
└── Missing "Architecture Quick Start" for onboarding

MEDIUM (14 issues)
├── MEDAL-001: Medallion concept fragmented across 53 files
├── CB-001: Circuit Breaker params fragmented across 8 files
├── DQ-001: DQ thresholds duplicated across 7 files
├── METRIC-003: Test count metric "~11,985" unverifiable
├── METRIC-005: BatchExecutor LOC drift (786 → 774)
├── METRIC-006: Diagram count undercount (34 → 50+)
├── ADR-003 (§2.2): Archived ADRs lack clear supersession markers
├── docs/analysis/ not referenced in 00-map.md
├── docs/03-data-model/ not referenced in 00-map.md
├── No anti-patterns guide (god object mentioned in 3 files, not glossary-indexed)
├── pipeline-configuration.md and CONFIG-GUIDE.md overlap
├── Composite spec numbering inconsistent with actual composite count
├── Document Status table in 00-map.md outdated (multiple dates stale)
└── Language policy not enforced (some Russian in guides/, some English in governance/)
```

### 8.2 Priority Remediation Plan

#### P0 — Must Fix Immediately (before next release)

| # | Issue | File | Action | Effort |
|---|---|---|---|---|
| 1 | Coverage threshold | rules-summary.md:108,128 | Change "80%" to "85%" | 5 min |
| 2 | RULES.md version ref | 00-map.md:3,47,60 | Update v5.19 → v5.20; ADR range 032→034 | 5 min |
| 3 | TOOLS.md sync | TOOLS.md:3 | Update sync version to v5.20 | 5 min |
| 4 | ADR-033 status | ADR-033 header | Resolve: Accept or document remaining work | 15 min |
| 5 | MedallionLifecycleService path | 02-application-layer.md:144 | Fix path reference | 5 min |
| 6 | BatchExecutor LOC | 02-application-layer.md:143 | Update 786 → 774 | 5 min |

#### P1 — Should Fix Within 1 Sprint

| # | Issue | Action | Effort |
|---|---|---|---|
| 7 | chembl-tissue docs | Create spec + provider doc from template | 2 hrs |
| 8 | composite-activity spec | Create spec from existing config | 1 hr |
| 9 | composite-assay spec | Create spec from existing config | 1 hr |
| 10 | Audit dir consolidation | Move docs/audit/* → docs/audits/; delete docs/audit/ | 30 min |
| 11 | Archive cleanup | Remove 6 merged*.md files (184K lines); mark archived ADRs | 30 min |
| 12 | Duplicate chembl specs | Remove duplicate 15-18 numbering; keep 01-14 | 30 min |
| 13 | 00-map.md metrics refresh | Update file counts, LOC, diagram count, test count | 30 min |
| 14 | Document Status table | Update all dates in 00-map.md status table | 15 min |

#### P2 — Should Fix Within 1 Month

| # | Issue | Action | Effort |
|---|---|---|---|
| 15 | DQ threshold consolidation | Make dq-configuration.md canonical; other files cross-ref | 2 hrs |
| 16 | CB config reference | Create docs/03-guides/circuit-breaker-config.md | 1 hr |
| 17 | Pipeline edge cases | Add idempotency/retry/edge case sections to all specs | 4 hrs |
| 18 | Architecture Quick Start | Create 1-page onboarding doc | 2 hrs |
| 19 | data-model/analysis merge | Merge docs/analysis/ into docs/03-data-model/ | 1 hr |
| 20 | Anti-patterns guide | Create docs/03-guides/anti-patterns.md; add to glossary | 1 hr |
| 21 | Medallion unified guide | Create single "Medallion Architecture Guide" in 03-guides/ | 3 hrs |

### 8.3 Proposed Commit Sequence

```
1. fix(docs): correct coverage threshold in rules-summary.md (80% → 85%)
2. fix(docs): update RULES.md version references in 00-map.md and TOOLS.md
3. fix(docs): correct MedallionLifecycleService path in application layer docs
4. fix(docs): resolve ADR-033 status (Proposed → Accepted or add implementation note)
5. docs(pipeline): add chembl-tissue pipeline spec and provider doc
6. docs(composite): add composite-activity and composite-assay specs
7. refactor(docs): consolidate audit directories (audit/ → audits/)
8. refactor(docs): remove merged source dumps from 99-archive/
9. refactor(docs): remove duplicate chembl pipeline spec numbering
10. fix(docs): refresh numerical metrics in 00-map.md
11. docs(guides): add DQ threshold canonical reference
12. docs(guides): add circuit breaker configuration reference
13. docs(guides): add architecture quick start for onboarding
14. docs(guides): add anti-patterns reference guide
```

### 8.4 Proposed docs/ Reorganization

Current structure is sound. No major reorganization required. Specific changes:

```
docs/
├── audit/          → DELETE (merge into audits/)
├── audits/         → KEEP (canonical audit directory)
├── analysis/       → MERGE into 03-data-model/analysis/
├── plans/          → MOVE to 99-archive/plans/
├── providers/      → MOVE to 04-reference/providers/ (if not already there)
├── reference/      → MERGE into 04-reference/
├── testing/        → MOVE to 03-guides/testing/
└── 99-archive/
    ├── *-merged.md → DELETE (source code dumps, not documentation)
    └── decisions/  → ADD SUPERSEDED markers to all files
```

### 8.5 Sections Requiring Full Rewrite

None. No sections require full rewrite. All issues are correctable through targeted edits,
additions, and consolidation. The documentation foundation is solid.

---

## Appendix A: Verification Methodology

1. **Filesystem analysis**: `find`, `wc -l`, `grep` across src/, docs/, configs/, tests/
2. **Cross-reference validation**: ADR index vs. filesystem; RULES.md appendix vs. README
3. **Path verification**: All module paths in layer docs checked against actual src/ structure
4. **Metric validation**: LOC counted via `find -name "*.py" -exec cat {} + | wc -l`
5. **Naming compliance**: Config files checked against 02-naming-policy.md conventions
6. **Template coverage**: Pipeline specs checked against chembl-activity template structure
7. **Duplication analysis**: Key concepts grep-searched across all 273 markdown files

## Appendix B: Files Analyzed

- docs/00-project/: 00-map.md, RULES.md, TOOLS.md, rules-summary.md, glossary.md, architecture-index.md
- docs/00-project/governance/: 02-naming-policy.md, 03-file-policy.md, 04-extending-bioetl.md
- docs/01-requirements/: REQUIREMENTS.md
- docs/02-architecture/: 00-overview.md, 01-05 layer docs, data-layers.md, data-flow.md
- docs/02-architecture/decisions/: All 34 ADRs + README.md
- docs/03-guides/: pipeline-configuration.md, pipeline-lifecycle.md, dq-configuration.md
- docs/04-reference/pipelines/: All provider subdirectories
- docs/04-reference/providers/: All provider subdirectories
- configs/: pipelines/, quality/, filters/, schemas/, sources/
- src/bioetl/: Full directory structure verification
- .claude/rules/: ai-selfreview-rules.md

---

*End of audit report.*
