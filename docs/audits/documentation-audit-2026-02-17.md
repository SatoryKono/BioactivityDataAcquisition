# BioETL Documentation System Audit Report

**Date:** 2026-02-17
**Scope:** Full documentation system audit (docs/, configs/, RULES.md)
**Methodology:** Cross-referencing docs ↔ code ↔ ADRs ↔ configs
**Auditor:** External independent auditor
**Code reference:** RULES.md v5.20, 34 ADRs, 180+ doc files

---

## Executive Summary

| Category | Score (0-10) | Verdict |
|----------|:---:|---------|
| Architecture Clarity | **9.0** | Documentation comprehensively describes all architectural layers and patterns |
| Consistency | **7.5** | Numerical drift, ADR count mismatch, several contradictions found |
| Completeness | **7.0** | Strong at system level, weak at per-pipeline granularity |
| Operational Readiness | **8.5** | Runbooks, DR procedures, health checks documented |
| Maintainability | **7.0** | Duplication across files creates synchronization burden |

**Overall: 7.8/10 — WARN**

The documentation is significantly above average for a data platform but has
accumulated synchronization debt. The primary risks are: (1) numerical metrics
that drift between docs and code, (2) information duplicated across 3-5 files
without a canonical source, (3) missing per-pipeline documentation.

---

## 1. Architectural Consistency

### 1.1 Verified Alignments (no issues)

| Pattern | Docs | Code | Status |
|---------|------|------|--------|
| Medallion Architecture (Bronze/Silver/Gold) | RULES.md §2.1, data-layers.md, ADR-002 | storage/ writers | **ALIGNED** |
| Ports & Adapters (5 layers) | RULES.md §1.1, diagrams.md | src/bioetl/{domain,application,infrastructure,composition,interfaces} | **ALIGNED** |
| Local-Only Deployment | RULES.md §3.3, ADR-010 | MemoryLock only, no Redis | **ALIGNED** |
| Deterministic Writes | RULES.md §4.3/§6.1, ADR-014 | sort_by in all configs, hash-based jitter | **ALIGNED** |
| Circuit Breaker | RULES.md §3.1.4, ADR-007 | infrastructure/adapters/http/circuit_breaker.py | **ALIGNED** |
| DQ Thresholds (5%/20%) | RULES.md §3.1.2, pipeline-configuration.md | configs/quality/_defaults.yaml | **ALIGNED** |
| MemoryLock TTL/Heartbeat (90s/30s) | RULES.md §3.3 | domain/config.py | **ALIGNED** |
| Content Hash (SHA256) | RULES.md §2.8 | domain/services/identity_service.py | **ALIGNED** |
| Gold Strict Validation | RULES.md §2.1, ADR-018 | domain/contracts/gold/ | **ALIGNED** |
| Composite Pipeline Pattern | RULES.md §2.9, ADR-026 | application/composite/ (15 modules) | **ALIGNED** |

### 1.2 Inconsistencies Found

#### ISSUE-ARCH-001: `@runtime_checkable` Scope Mismatch (LOW)

**RULES.md §1.1.1** states only 4 ports **SHOULD** be `@runtime_checkable`:
`DataSourcePort`, `FilterableDataSourcePort`, `HealthCheckPort`, `StoragePort`.
Other ports "MAY not have `@runtime_checkable`."

**Actual code:** All 38 ports are decorated with `@runtime_checkable`.

**Impact:** Over-compliance, not a violation. But documentation is misleading —
a reader would conclude most ports lack runtime checking.

**Fix:** Update §1.1.1 to reflect that all ports are currently `@runtime_checkable`,
while the SHOULD requirement applies to the 4 critical ones.

#### ISSUE-ARCH-002: GtoP Provider in Documentation But Not in Code (MEDIUM)

**RULES.md Appendix A** lists 8 providers including `GtoP` marked as `(deprecated)`.

**Actual code:** No GtoP adapter exists. No GtoP config exists. No GtoP transformer exists.
Provider registry contains 8 entries (7 providers + UniProt IDMapping variant), none is GtoP.

**Impact:** New engineers may be confused by the phantom provider.

**Fix:** Remove GtoP from Appendix A or move it to an explicit "Historical/Removed" section.

#### ISSUE-ARCH-003: RULES.md §5.6 References Docker (Contradicts ADR-010) (LOW)

**RULES.md §5.6** describes Dev environment as "Docker Compose" and §9.2 mentions
"Docker Compose (legacy, unsupported)".

**ADR-010** explicitly REJECTS Docker for deployment.

**Impact:** The "legacy, unsupported" annotation is present but the Dev section
(§5.6) still mentions Docker Compose without qualification.

**Fix:** Add "(deprecated — see ADR-010)" after Docker Compose mention in §5.6.

#### ISSUE-ARCH-004: UnifiedHTTPClient Library Claims (LOW)

**RULES.md Appendix A** lists libraries: UniProt → `unipressed`, OpenAlex → `pyalex`,
Semantic Scholar → `semanticscholar`, PubMed → `biopython`, CrossRef → `habanero`.

**Actual code:** All 7 adapters use `UnifiedHTTPClient` (per ADR-032), confirmed
by §4.1.1. The third-party library names in Appendix A appear to be legacy references.

**Fix:** Update Appendix A library column to reflect that all use `httpx` via
`UnifiedHTTPClient`, except PubChem which uses `pubchempy` wrapped in `BaseSyncAdapter`.

---

## 2. ADR Consistency

### 2.1 ADR Coverage

**Total ADRs:** 34 (ADR-001 through ADR-034)
**Numbering gaps:** None — all 34 sequential numbers present.
**Status:** 33 Accepted, 1 Proposed (ADR-033)

#### ISSUE-ADR-001: ADR Count Mismatch in ARCHITECTURE_AUDIT_2026-02-16.md (HIGH)

**ARCHITECTURE_AUDIT_2026-02-16.md** (docs/00-project/) states: "ADR documents: **30**"

**RULES.md Appendix F** lists all 34 ADRs. ADR-031 through ADR-034 exist and are
accepted (dates 2026-01-26 through 2026-02-15).

**Impact:** The audit report — positioned as the authoritative metrics document —
understates ADR coverage by 4 (11.8% error).

**Fix:** Update ARCHITECTURE_AUDIT_2026-02-16.md or produce a fresh audit with
correct count: 34 ADRs.

#### ISSUE-ADR-002: ADR-033 Status Discrepancy (LOW)

**RULES.md Appendix F** lists ADR-033 as `Accepted`.
**decisions/README.md** listed it as `Proposed`.

**Impact:** Unclear whether the ADR has been formally accepted.

**Fix:** Reconcile status — either update README.md to `Accepted` or RULES.md
to `Proposed`.

### 2.2 ADR → Documentation Coverage Matrix

| ADR | Title | Reflected in RULES.md | Reflected in Guides | Notes |
|-----|-------|:---:|:---:|-------|
| ADR-001 | Delta Lake | ✅ §2.1.3 | ✅ data-layers.md | |
| ADR-002 | Medallion | ✅ §2.1 | ✅ data-layers.md | |
| ADR-003 | MemoryLock | ✅ §3.3 | ✅ pipeline-lifecycle.md | |
| ADR-005 | Composition Layer | ✅ §1.1 | ❌ No dedicated guide | Missing guide |
| ADR-007 | Circuit Breaker | ✅ §3.1.4 | ❌ No operational guide | Only runbook for incidents |
| ADR-010 | Local-Only | ✅ §3.3, §9.2 | ❌ No dedicated guide | |
| ADR-014 | Deterministic Writes | ✅ §4.3, §6.1 | ❌ No developer guide | |
| ADR-020 | BasePipeline Decomposition | ✅ §1.1 ref | ❌ No migration guide | |
| ADR-021 | DDD Aggregates | ✅ §1.1 ref | ❌ No usage guide | |
| ADR-026 | Composite Pipeline | ✅ §2.9 | ✅ pipeline-configuration.md | |
| ADR-027 | DQ Externalization | ✅ App D | ✅ dq-configuration.md | |
| ADR-028 | Filter Externalization | ✅ App D | ✅ pipeline-configuration.md | |
| ADR-029 | Output Metadata | ✅ App D | ✅ pipeline-configuration.md | |
| ADR-032 | Unified HTTP Client | ✅ §4.1.1 | ❌ No migration guide | |
| ADR-034 | Schema↔Domain Pairs | ✅ Appendix F | ❌ No guide | Recent — may not need one yet |

**Summary:** 6 ADRs lack corresponding developer guides. These are primarily
"architectural backbone" decisions that don't require step-by-step guidance,
but ADR-005 (Composition Layer) and ADR-021 (DDD Aggregates) would benefit
from usage guides for onboarding.

### 2.3 Missing ADR Coverage

The following documented features lack dedicated ADRs:

| Feature | Location | Potential ADR |
|---------|----------|---------------|
| Provider Health Monitoring (3-state: Healthy/Degraded/Unhealthy) | RULES.md §3.5 | Might warrant ADR for health state machine |
| Column Rename Chain (Silver→Gold) | RULES.md §2.9.6 | Covered implicitly by ADR-026 |
| Quarantine State Machine | RULES.md §2.6 | Covered by ADR-021 (aggregates) |

**Verdict:** No critical missing ADRs. Coverage is comprehensive.

---

## 3. Naming & Structure Compliance

### 3.1 Naming Policy Compliance (02-naming-policy.md)

| Rule | Category | Compliance | Notes |
|------|----------|:---:|-------|
| Domain entities: `{Provider}{CanonicalTerm}` | MUST | ✅ | Verified across all providers |
| Pipeline IDs: `{provider}_{entity}` | MUST | ✅ | All 26 configs follow convention |
| Transformers: `{Provider}{CanonicalTerm}Transformer` | MUST | ✅ | 21 concrete transformers verified |
| Schemas: `{Provider}{CanonicalTerm}GoldSchema` | MUST | ✅ | domain/contracts/gold/ |
| Table names: `{provider}_{entity}` | MUST | ✅ | silver_table/gold_table in configs |
| Config file names: `{entity}.yaml` | MUST | ✅ | All follow pattern |

#### ISSUE-NAME-001: Documentation Prefix Inconsistency (LOW)

**docs/00-project/** uses numbered prefixes: `00-map.md`, `01-domain-objects.md`,
`02-etl-layers.md`, etc.

**docs/00-project/architecture-index.md** reveals these are aliases:
- `01-domain-objects.md` → `../02-architecture/01-domain-layer.md`
- `02-etl-layers.md` → `../02-architecture/data-layers.md`

The alias file exists but the naming suggests parallel structure where none exists.
`01-domain-objects.md` in `00-project/` vs `01-domain-layer.md` in `02-architecture/`
creates confusion about which is canonical.

**Fix:** Remove alias files from `00-project/` and update cross-references to
point directly to canonical locations.

#### ISSUE-NAME-002: Missing Entity Documentation Pages (MEDIUM)

Per 03-file-policy.md, documentation should mirror source structure:
`src/bioetl/.../{provider}/` ↔ `docs/providers/{provider}/`

**Actual docs structure:** No `docs/providers/` directory exists. Pipeline
documentation is generalized in `docs/03-guides/pipeline-configuration.md` and
`docs/04-reference/api/`.

**Impact:** No per-entity documentation pages for the 21 pipelines. Each pipeline's
extraction logic, transformation rules, edge cases, and DQ thresholds are not
individually documented.

**Fix:** Either create per-entity pages or explicitly document this as an intentional
deviation from the naming policy mirror rule.

### 3.2 Source Structure vs Docs

| src/ Layer | doc/ Counterpart | Coverage |
|-----------|-----------------|----------|
| `domain/ports/` (38 ports) | `04-reference/api/domain/ports.md` | ✅ Reference exists |
| `domain/entities/` | `04-reference/api/domain/entities.md` | ✅ Reference exists |
| `application/core/` | `04-reference/api/application/core.md` | ✅ Reference exists |
| `application/composite/` | `04-reference/api/application/` | ⚠️ No dedicated composite reference |
| `infrastructure/adapters/` | `04-reference/api/` | ⚠️ No per-adapter API reference |
| `composition/` | `04-reference/api/composition/` | ✅ Reference exists |
| `interfaces/cli/` | Quick-start, running-pipelines guides | ✅ CLI documented |

---

## 4. Pipeline Documentation Completeness

### 4.1 Per-Pipeline Audit Matrix

| Criterion | ChEMBL (14) | PubChem | UniProt | PubMed | CrossRef | OpenAlex | SemanticScholar | Composite (5) |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Overview | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Source API | ✅ App A | ✅ App A | ✅ App A | ✅ App A | ✅ App A | ✅ App A | ✅ App A | N/A |
| Extraction logic | ⚠️ Generic | ⚠️ Generic | ⚠️ Generic | ⚠️ Generic | ⚠️ Generic | ⚠️ Generic | ⚠️ Generic | ⚠️ Generic |
| Transformation rules | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ Partial §2.9 |
| Validation rules (Silver) | ⚠️ Schema only | ⚠️ Schema only | ⚠️ Schema only | ⚠️ Schema only | ⚠️ Schema only | ⚠️ Schema only | ⚠️ Schema only | ⚠️ Schema only |
| Validation rules (Gold) | ⚠️ Contract only | ⚠️ Contract only | ⚠️ Contract only | ⚠️ Contract only | ⚠️ Contract only | ⚠️ Contract only | ⚠️ Contract only | ⚠️ Contract only |
| Write strategy | ✅ Config | ✅ Config | ✅ Config | ✅ Config | ✅ Config | ✅ Config | ✅ Config | ✅ Config |
| Partitioning | ✅ Config | ✅ Config | ✅ Config | ✅ Config | ✅ Config | ✅ Config | ✅ Config | N/A |
| Idempotency | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic |
| DQ thresholds | ✅ DQ YAML | ✅ DQ YAML | ✅ DQ YAML | ✅ DQ YAML | ✅ DQ YAML | ✅ DQ YAML | ✅ DQ YAML | ✅ DQ YAML |
| Locking behavior | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic |
| Retry/CB behavior | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic |
| Backfill strategy | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic | ✅ Generic |
| Known edge cases | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Legend:** ✅ = documented, ⚠️ = partially/generically documented, ❌ = not documented

### 4.2 Key Gaps

#### ISSUE-PIPE-001: No Per-Pipeline Transformation Documentation (HIGH)

None of the 21 pipelines has documented transformation rules. The field-level
transformations (field renaming, type coercion, nested JSON flattening, value
normalization) are only discoverable by reading transformer source code.

**Example:** `ChEMBL ActivityTransformer` flattens nested JSON structures and
renames fields, but no documentation describes which fields are extracted, how
nested structures are handled, or what business logic is applied.

**Fix:** Create per-entity transformation specs or auto-generate from transformer
code docstrings.

#### ISSUE-PIPE-002: No Known Edge Cases Documentation (MEDIUM)

No pipeline documents provider-specific edge cases such as:
- ChEMBL API pagination quirks
- PubChem sync-to-async wrapping implications
- UniProt FASTA parsing edge cases
- CrossRef polite pool behavior
- SemanticScholar extreme rate limiting (0.1 req/sec without API key)

**Fix:** Add "Edge Cases" section to per-pipeline documentation.

#### ISSUE-PIPE-003: Composite Pipeline Architecture Not Clearly Distinguished (MEDIUM)

Composite pipelines don't use transformer classes — they use `CompositePipelineRunner`
orchestration service (15 modules in `application/composite/`). This architectural
distinction is documented in ADR-026 and RULES.md §2.9 but never explicitly stated
as "composite pipelines use orchestration, not transformers."

**Fix:** Add explicit note in pipeline-configuration.md and pipeline-lifecycle.md.

---

## 5. Duplication and Fragmentation

### 5.1 Identified Duplications

| Topic | Files Where Described | Canonical Source |
|-------|----------------------|-----------------|
| Medallion Clear Policy | RULES.md §2.4.2, pipeline-lifecycle.md, ADR-012 | RULES.md §2.4.2 |
| DQ Thresholds (5%/20%) | RULES.md §3.1.2, pipeline-configuration.md, data-layers.md | RULES.md §3.1.2 |
| Circuit Breaker params | RULES.md §3.1.4, ADR-007, pipeline-configuration.md | ADR-007 |
| Lock TTL/Heartbeat values | RULES.md §3.3, pipeline-lifecycle.md, ADR-003 | RULES.md §3.3 |
| Provider rate limits | RULES.md App A, pipeline-configuration.md | pipeline-configuration.md |
| Import matrix | RULES.md §1.1, ai-selfreview-rules.md ARCH-001 | RULES.md §1.1 |
| Health Check contract | RULES.md §1.1.2, architecture tests | RULES.md §1.1.2 |
| Content Hash algorithm | RULES.md §2.8, §2.8.1, §6.1 | RULES.md §2.8 |
| sort_by requirement | RULES.md §6.1, ADR-014, 03-file-policy.md, pipeline-configuration.md | ADR-014 |

### 5.2 Fragmentation Issues

#### ISSUE-DUP-001: Architecture Described in 4+ Places (MEDIUM)

The 5-layer architecture is described in:
1. `RULES.md §1.1` (authoritative)
2. `docs/02-architecture/diagrams.md` (visual)
3. `docs/00-project/02-etl-layers.md` → alias to `data-layers.md`
4. `docs/04-reference/api/` (per-layer API reference)
5. `ai-selfreview-rules.md` (ARCH-001 import matrix)

**Risk:** Changes to the architecture require updating 4+ files.

#### ISSUE-DUP-002: Rate Limits in Two Different Formats (LOW)

**RULES.md Appendix A** uses text format: "5 req/sec", "100 req/sec (c API key)"
**pipeline-configuration.md** uses table format with structured columns:
`Rate Limit | Burst | Batch Size`

The values are consistent but the duplication increases maintenance burden.

### 5.3 Consolidation Recommendations

| Action | Files | Recommendation |
|--------|-------|----------------|
| **Merge** | `00-project/01-domain-objects.md` through `05-physical-layout.md` | Remove alias files; update 00-map.md to point directly to canonical docs |
| **Deduplicate** | Rate limits in RULES.md App A and pipeline-configuration.md | Keep in pipeline-configuration.md only; RULES.md App A should reference it |
| **Canonical** | DQ thresholds | RULES.md §3.1.2 is canonical; all others should cross-reference |
| **Canonical** | Lock TTL/Heartbeat | RULES.md §3.3 is canonical |
| **Canonical** | Import matrix | RULES.md §1.1 is canonical; ai-selfreview-rules.md should reference it |

---

## 6. Numerical Metrics Audit

### 6.1 Metric Comparison Table

| Metric | 00-map.md | ARCH_AUDIT 2026-02-16 | RULES.md | Actual (2026-02-17) | Drift |
|--------|-----------|----------------------|----------|---------------------|-------|
| Python files (src/bioetl/) | — | — | 534 (§4.4.1) | **534** | ✅ |
| Python files (src/) | ~1,114 | 552 | — | **534** (src/bioetl/) | ⚠️ Different scopes |
| Total LOC | ~115,656 | 114,547 | — | **116,062** | ⚠️ +1,515 since audit |
| Test count | ~11,985 | 11,693 passed | — | **477** test files | ⚠️ Different metrics |
| ADR count | 34 | **30** | 34 (App F) | **34** | ❌ Audit stale |
| Classes | — | 906 | — | **911** | ⚠️ +5 since audit |
| Ports | — | 38 | — | **38** | ✅ |
| Pipeline configs | 27 | — | — | **26** (excl. _base) | ⚠️ Off by 1 |
| VCR cassettes | — | 95 | — | **68** | ❌ Cassettes reduced |
| Gold contracts | — | 5 modules | — | **8** files | ⚠️ Different granularity |
| Future annotations | — | — | 497/534 (93.1%) | — | Not verified |

### 6.2 Critical Metric Issues

#### ISSUE-METRIC-001: ADR Count in ARCHITECTURE_AUDIT (HIGH)

`ARCHITECTURE_AUDIT_2026-02-16.md` reports 30 ADRs. Actual: 34.
ADR-031 through ADR-034 were added between 2026-01-26 and 2026-02-15.
The audit was produced on 2026-02-16 — one day after ADR-034.

**Fix:** Regenerate or update ARCHITECTURE_AUDIT with correct count.

#### ISSUE-METRIC-002: Pipeline Config Count in 00-map.md (LOW)

`00-map.md` claims "27 configurations". Actual pipeline YAML files: 26
(14 ChEMBL + 5 composite + 7 other providers). Possible explanations:
- Counted `_base.yaml` as a pipeline config
- Previous count before a config was removed

**Fix:** Update to 26 or clarify what "27" includes.

#### ISSUE-METRIC-003: VCR Cassette Count Drift (MEDIUM)

`ARCHITECTURE_AUDIT_2026-02-16.md` reports 95 VCR cassettes. Actual: 68.
Either cassettes were cleaned up or the counting method differs.

**Fix:** Reconcile VCR cassette counts and update audit metrics.

#### ISSUE-METRIC-004: LOC Drift (LOW)

`00-map.md` (updated 2026-02-16): ~115,656 LOC
`ARCHITECTURE_AUDIT_2026-02-16.md`: 114,547 LOC
Actual (2026-02-17): 116,062 LOC

All three numbers differ, spanning a range of ~1,500 lines.

**Fix:** Document the measurement method (which `wc -l` scope) and update regularly.

---

## 7. Production-Grade Readiness Assessment

### 7.1 Can a new engineer understand the architecture in 1 day?

**Yes, with caveats.** The documentation provides:
- `00-map.md` as a project navigator (excellent entry point)
- `RULES.md` as a comprehensive reference (1,567 lines — requires focused reading)
- `docs/03-guides/getting-started.md` and `quick-start.md` for onboarding
- 8 Mermaid diagrams in `diagrams.md`
- `architecture-index.md` with document aliases

**Gaps for onboarding:**
- No "Architecture Overview" single-page document (RULES.md is too dense)
- No per-pipeline documentation (engineer must read transformer source code)
- Composite pipeline architecture requires reading ADR-026 + RULES.md §2.9 +
  pipeline-configuration.md to understand fully

### 7.2 Is the documentation sufficient for audit?

**Yes.** The documentation supports:
- Architecture boundary verification (ARCH-001 through ARCH-008)
- ADR traceability (34 ADRs linked to code)
- Requirement traceability (156 requirements in REQUIREMENTS.md)
- Test verification (architecture tests, contract tests)
- Security audit (PII policy, secret management)

### 7.3 Can refactoring be done safely with docs only?

**Partially.** Safe for:
- Adding new providers (04-extending-bioetl.md)
- Adding new pipelines (add-pipeline-existing-source.md)
- Config changes (pipeline-configuration.md is comprehensive)

**Risky without reading code:**
- Transformer modifications (no transformation docs)
- Composite pipeline changes (orchestration architecture not fully documented)
- Storage writer modifications (subtle Delta Lake interactions)

### 7.4 Does the documentation match a mature data platform?

**Yes, with reservations.** Strengths:
- RULES.md is exceptionally thorough
- ADR coverage is comprehensive (34 decisions)
- Governance framework (naming, file policy, extending guide) is strong
- Runbooks exist for critical scenarios

Weaknesses:
- No per-pipeline data dictionaries
- No data flow diagrams per pipeline
- No SLA documentation per provider beyond rate limits

### 7.5 Scores

| Category | Score | Rationale |
|----------|:---:|-----------|
| Architecture Clarity | **9.0** | Excellent 5-layer description, Medallion well-documented, missing composite orchestration detail |
| Consistency | **7.5** | Numerical drift in 4+ metrics, ADR count mismatch, GtoP phantom, provider library names stale |
| Completeness | **7.0** | No per-pipeline docs, no transformation specs, no edge case documentation |
| Operational Readiness | **8.5** | Runbooks exist, DR procedures documented, health check contracts defined, monitoring guide present |
| Maintainability | **7.0** | Information duplicated across 3-5 files per topic, alias files add confusion, no single-page architecture overview |

---

## 8. Remediation Plan

### 8.1 Structural Problem Map

```
CRITICAL (P0) — Blocks correctness/auditability
├── ISSUE-ADR-001: ADR count mismatch (30 vs 34) in ARCHITECTURE_AUDIT
├── ISSUE-METRIC-001: Same as above — stale audit metrics
└── ISSUE-METRIC-003: VCR cassette count drift (95 vs 68)

HIGH (P1) — Affects onboarding and maintenance
├── ISSUE-PIPE-001: No per-pipeline transformation documentation
├── ISSUE-ARCH-002: GtoP phantom provider in Appendix A
├── ISSUE-ARCH-004: Stale library names in Appendix A
└── ISSUE-NAME-002: Missing entity documentation pages

MEDIUM (P2) — Improvement opportunities
├── ISSUE-PIPE-002: No edge cases documentation
├── ISSUE-PIPE-003: Composite vs transformer distinction unclear
├── ISSUE-DUP-001: Architecture described in 4+ places
├── ISSUE-DUP-002: Rate limits duplicated
├── ISSUE-ADR-002: ADR-033 status discrepancy
├── ISSUE-METRIC-002: Pipeline config count off by 1
├── ISSUE-METRIC-004: LOC drift between documents
└── ISSUE-NAME-001: Alias file confusion in 00-project/

LOW (P3) — Polish
├── ISSUE-ARCH-001: @runtime_checkable scope description
└── ISSUE-ARCH-003: Docker mention without ADR-010 qualifier
```

### 8.2 Prioritized Fix Sequence

#### Phase 1: P0 — Metric Accuracy (1 commit)

**Commit 1: `fix(docs): synchronize numerical metrics across documentation`**

| File | Change |
|------|--------|
| `ARCHITECTURE_AUDIT_2026-02-16.md` | Update ADR count: 30→34, VCR cassettes: 95→68, classes: 906→911, LOC: 114,547→116,062 |
| `00-map.md` | Update pipeline configs: 27→26 |

**Effort:** S (30 minutes)

#### Phase 2: P1 — Structural Fixes (2-3 commits)

**Commit 2: `fix(docs): remove phantom GtoP provider and update Appendix A libraries`**

| File | Change |
|------|--------|
| `RULES.md` Appendix A | Remove GtoP row; update library column for UniProt, OpenAlex, SemanticScholar, PubMed, CrossRef to reflect `httpx` via `UnifiedHTTPClient` |

**Effort:** S (30 minutes)

**Commit 3: `docs: add per-pipeline transformation documentation stubs`**

Create directory `docs/04-reference/pipelines/` with per-provider subdirectories
and entity transformation specs. These can initially be auto-generated stubs
with field lists from Gold schemas.

| New Files | Content |
|-----------|---------|
| `docs/04-reference/pipelines/chembl/activity.md` | Fields, transformation rules, DQ thresholds |
| `docs/04-reference/pipelines/chembl/molecule.md` | Fields, transformation rules, DQ thresholds |
| ... (21 files total) | Per-entity documentation |

**Effort:** L (1-2 days for full coverage; stubs in 2 hours)

#### Phase 3: P2 — Consistency Improvements (3-4 commits)

**Commit 4: `fix(docs): clarify composite pipeline orchestration pattern`**

| File | Change |
|------|--------|
| `pipeline-configuration.md` | Add note: "Composite pipelines use CompositePipelineRunner orchestration, not individual transformer classes" |
| `pipeline-lifecycle.md` | Add composite pipeline lifecycle section |

**Commit 5: `fix(docs): reconcile ADR-033 status`**

| File | Change |
|------|--------|
| `decisions/README.md` | Update ADR-033 status to match RULES.md |

**Commit 6: `refactor(docs): remove alias files from 00-project/`**

| Files to Remove | Replacement |
|-----------------|-------------|
| `00-project/01-domain-objects.md` | Update 00-map.md to link directly to `02-architecture/01-domain-layer.md` |
| `00-project/02-etl-layers.md` | Update 00-map.md to link directly to `02-architecture/data-layers.md` |
| `00-project/03-data-flow.md` | Update 00-map.md to link directly |
| `00-project/04-duplication-reduction.md` | Update 00-map.md to link directly |
| `00-project/05-physical-layout.md` | Update 00-map.md to link directly |

**Commit 7: `fix(docs): deduplicate rate limits, keep single canonical source`**

| File | Change |
|------|--------|
| `RULES.md` Appendix A | Replace inline rate limits with reference to `pipeline-configuration.md` |

#### Phase 4: P3 — Polish (2 commits)

**Commit 8: `fix(docs): update @runtime_checkable documentation in RULES.md`**

| File | Change |
|------|--------|
| `RULES.md` §1.1.1 | Note that all 38 ports are currently @runtime_checkable |

**Commit 9: `fix(docs): qualify Docker references with ADR-010 deprecation`**

| File | Change |
|------|--------|
| `RULES.md` §5.6 | Add "(deprecated — see ADR-010)" |

### 8.3 docs/ Reorganization Proposal

**Current structure is fundamentally sound.** No major reorganization needed.

Minor improvements:

1. **Add** `docs/04-reference/pipelines/` for per-entity documentation
2. **Remove** alias files from `docs/00-project/` (01 through 05)
3. **Consider** splitting RULES.md Appendix A-F into standalone files in
   `docs/04-reference/` to reduce RULES.md size (currently 1,567 lines)

### 8.4 Sections Requiring Full Rewrite

| Section | Reason | Priority |
|---------|--------|----------|
| RULES.md Appendix A (Provider Libraries) | Library names outdated after ADR-032 unification | P1 |
| ARCHITECTURE_AUDIT_2026-02-16.md metrics | Stale numbers across 4+ categories | P0 |

**No other sections require full rewrites.** The documentation is structurally
sound — the issues are synchronization debt, not fundamental gaps.

---

## Appendix: Verification Commands Used

```bash
# Python file count
find src/bioetl -name "*.py" | wc -l                    # 534

# LOC count
find src/bioetl -name "*.py" -exec cat {} \; | wc -l    # 116,062

# Test file count
find tests -name "test_*.py" -o -name "*_test.py" | wc -l  # 477

# ADR count
ls docs/02-architecture/decisions/ADR-*.md | wc -l      # 34

# Class count
grep -r "^class " src/bioetl/ --include="*.py" | wc -l  # 911

# Port count
grep -r "@runtime_checkable" src/bioetl/domain/ports/ --include="*.py" | wc -l  # 38

# VCR cassette count
find tests/fixtures/vcr -name "*.yaml" -o -name "*.json" | wc -l  # 68

# Pipeline config count
ls configs/pipelines/*/*.yaml | wc -l                    # 26
```

---

*Audit produced 2026-02-17. Cross-referenced against RULES.md v5.20,
34 ADRs, 534 Python source files, 477 test files, 26 pipeline configs.*
