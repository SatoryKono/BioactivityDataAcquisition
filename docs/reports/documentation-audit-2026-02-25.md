# Documentation Audit Report — BioETL

**Date:** 2026-02-25
**Scope:** Full exhaustive audit (366 markdown files, 546 Python source files)
**Auditor:** Claude Code (6 parallel exploration agents)
**Project Version:** v6.0.0 | RULES.md v5.23 (resolved)

---

## Executive Summary

BioETL documentation is **mature and comprehensive** with strong governance foundations (RULES.md, 39 ADRs, governance policies). However, the audit reveals **critical synchronization issues**, a **74% orphan rate** in mkdocs navigation, significant **duplication across agent docs**, and gaps in developer-facing reference documentation.

| Area | Score | Status |
|------|-------|--------|
| Core Docs (README, RULES, map) | 8.2/10 | PASS |
| Architecture & ADRs | 8.2/10 | PASS |
| Guides & Operations | 7.5/10 | WARN |
| Reference Docs (04-reference) | 8.0/10 | PASS |
| Code Docstrings | 8.5/10 | PASS |
| Governance & Agent Docs | 6.5/10 | WARN |
| mkdocs.yml Navigation | 4.0/10 | FAIL |
| **OVERALL** | **7.3/10** | **WARN** |

---

## Inventory

| Metric | Count |
|--------|-------|
| Total markdown files | 366 |
| Docs in `docs/` (excl. archive) | 260 |
| Docs in mkdocs.yml nav | 67 |
| Orphan docs (not in nav) | **193 (74%)** |
| ADRs | 39 (ADR-001..039) |
| Pipeline specs | 26 (100% coverage) |
| Gold contract JSONs | 26 (100% coverage) |
| Python source files | 546 |
| Public classes with docstrings | 920/920 (99.9%) |
| Public functions with docstrings | 1262/1528 (82.6%) |
| Docs with no date | 121 |
| Docs with stale dates (<2026) | 21 |

---

## Findings by Severity

### CRITICAL (7 issues)

**C-01. RULES.md version conflict (v5.21 vs v5.23)**
- `PROJECT-CONTEXT.md` и `agent-memory.md` ссылаются на v5.23 (2026-02-24)
- `RULES.md`, `README.md`, `TOOLS.md`, `rules-summary.md` — все на v5.21 (2026-02-21)
- Нет единого источника истины по актуальной версии
- **Impact:** Агенты и docs могут конфликтовать по правилам

**C-02. 193 orphan docs not in mkdocs.yml (74% orphan rate)**
- Только 67 из 260 активных docs включены в navigation
- ALL 39 ADR files — orphans (nav ссылается только на README)
- ALL 20 provider docs — orphans
- ALL pipeline specs (26) — orphans
- ALL schema docs — orphans
- **Impact:** Docs не индексируются MkDocs, не попадают в поиск сайта

**C-03. ORCHESTRATION.md — два конфликтующих файла**
- `.claude/agents/ORCHESTRATION.md` — v3.0 (2026-02-08, canonical)
- `docs/00-project/ai/agents/orchestration/ORCHESTRATION.md` — v3.1 Adapted
- Различия: naming (kebab vs PascalCase), ADR count (33 vs 39), artifact names
- **Impact:** Субагенты могут получить конфликтующие инструкции

**C-04. 00-map.md ADR count stale (34 вместо 39)**
- Line 8: "34 ADRs (ADR-001 through ADR-034)"
- Реальность: 39 ADRs (ADR-001 through ADR-039)
- ADR-035..039 не упоминаются в навигаторе
- **Impact:** 5 новейших ADR невидимы через Project Navigator

**C-05. Deployment guide contradicts ADR-010 (Local-Only)**
- `docs/05-operations/deployment/DEPLOYMENT-GUIDE.md` — K8s/EKS/GKE deployment
- ADR-010 — Local-Only deployment philosophy
- Neo4j memory docs present but Neo4j not in architecture
- **Impact:** Новые пользователи могут выбрать неправильную стратегию развёртывания

**C-06. CONFIG-GUIDE.md дублирует pipeline-configuration.md**
- `CONFIG-GUIDE.md` — legacy, deprecated terminology, JSON examples
- `pipeline-configuration.md` — current, v6.0.0, YAML examples
- Оба описывают ту же конфигурационную схему
- **Impact:** Два conflicting источника конфигурационной документации

**C-07. ADR-003 status inconsistency**
- ADR-003 header: "Accepted (Revised 2025-12-23)"
- README relationship graph line 184: "ADR-003 (Superseded)"
- ADR-010 supersedes Redis aspect but not MemoryLock
- **Impact:** Неясный статус решения, путаница при code review

### HIGH (12 issues)

**H-01. Glossary staleness** — v2.5 (2026-02-06), 19 дней отставание от RULES.md
**H-02. ADR-030 naming collision** — 2 разных ADR-030 (Pagination vs Field Unification) + 4 archived variants
**H-03. ADR-033 status unclear** — "Added" status, не "Accepted"; implementation roadmap отсутствует
**H-04. Subagent specs duplication** — `.claude/agents/py-*.md` + `.claude/agents/subagents/*/SUBAGENT.md` + `docs/00-project/ai/agents/orchestration/subagents/`
**H-05. Memory file version skew** — `agent-memory.md` claims v5.23, actual RULES is v5.21
**H-06. Troubleshooting underdeveloped** — 5.6 KB, covers only 5 scenarios (should be 15+)
**H-07. migration-5.14-to-6.0.md minimal** — only 32 lines for a major version jump
**H-08. migration-schema-artifacts.md** — empty stub with no content
**H-09. add-new-source.md / add-pipeline-existing-source.md** — `--init--` syntax errors in code samples
**H-10. Composition layer docstrings weakest** — 74.4% function coverage (43 undocumented factory methods)
**H-11. Domain schema docs** — only 4/28+ documented (14% coverage)
**H-12. Internal API module docs** — only 14/28 modules documented (50%)

### MEDIUM (15 issues)

**M-01.** 121 docs without any dates — impossible to assess freshness
**M-02.** AGENTS.md has no version/sync date
**M-03.** README.md contains Russian sections (mixed language in public-facing doc)
**M-04.** Copilot-instructions.md minimal (35 lines, basic headings only)
**M-05.** PR template minimal (17 lines, no breaking changes / related issues)
**M-06.** SECURITY.md missing vulnerability disclosure SLA
**M-07.** Root-level loose docs (`audit-bolt-branches-merge-plan.md`, `codex-setup.md`) not organized
**M-08.** docs/plans/ and docs/reports/ lack README with status
**M-09.** Duplicate report: `codex-branches-summary-2026-02-24T13.md`
**M-10.** `.docx` file in archive (binary, not version-control friendly)
**M-11.** Legacy dashboard docs not fully archived (BIOETL-DATA-EXTRACTION-AND-DASHBOARDS.md in main) <!-- doc-lint: allow-legacy -->
**M-12.** MONITORING-INDEX.md empty stub
**M-13.** Data model docs (docs/03-data-model/) — unclear if completed work or WIP
**M-14.** .claude/prompts/ lacks README explaining purpose/status
**M-15.** Docstring style inconsistency (Google 57%, Mixed 30%, Sphinx 10%)

### LOW (8 issues)

**L-01.** architecture-index.md minimal (17 lines, purpose unclear)
**L-02.** 06-diagram-polisy.md typo in filename ("polisy" → "policy")
**L-03.** No ADR versioning policy for revised decisions
**L-04.** Diagram rendering timestamp missing from mmd-diagrams/README.md
**L-05.** No automated documentation sync mechanism documented
**L-06.** Provider entity count discrepancy in index.md vs README.md
**L-07.** 6 `--init--.py` files missing `--all--` exports
**L-08.** CONTRIBUTING.md broken link to `../AGENTS.md`

---

## Proposed Improvement Plan (Prioritized)

### Phase 1: Critical Fixes (P0, 1-2 days)

| # | Action | Files | Effort |
|---|--------|-------|--------|
| 1.1 | Resolve RULES.md version (determine v5.21 or v5.23, sync all dependent docs) | RULES.md, PROJECT-CONTEXT.md, agent-memory.md, TOOLS.md, rules-summary.md, 00-map.md | 1h |
| 1.2 | Update 00-map.md ADR count to 39, add ADR-035..039 references | 00-map.md | 30m |
| 1.3 | Deprecate `docs/.../orchestration/ORCHESTRATION.md` with pointer to `.claude/agents/` | ORCHESTRATION.md (docs/) | 15m |
| 1.4 | Archive CONFIG-GUIDE.md to 99-archive/, update internal links | CONFIG-GUIDE.md, mkdocs.yml | 30m |
| 1.5 | Add deployment disclaimer re: ADR-010 Local-Only as primary | DEPLOYMENT-GUIDE.md | 15m |
| 1.6 | Fix ADR-003 status (align header with README relationship graph) | ADR-003, decisions/README.md | 15m |
| 1.7 | Fix ADR-030 archive (add explicit supersession headers) | 99-archive/decisions/ADR-030-*.md | 30m |

### Phase 2: mkdocs.yml Navigation Overhaul (P1, 2-3 days)

| # | Action | Scope | Effort |
|---|--------|-------|--------|
| 2.1 | Add ALL 39 ADRs to mkdocs nav under Architecture → Decisions | mkdocs.yml | 1h |
| 2.2 | Add all provider entity docs to nav under Providers section | mkdocs.yml | 1h |
| 2.3 | Add all pipeline specs to nav under Pipelines section | mkdocs.yml | 1h |
| 2.4 | Add layer docs (01-domain through 05-composition) to Architecture | mkdocs.yml | 30m |
| 2.5 | Add runbooks to Operations nav section | mkdocs.yml | 30m |
| 2.6 | Add glossary, naming-policy, github-policy to nav | mkdocs.yml | 15m |
| 2.7 | Add schema docs to Reference section | mkdocs.yml | 15m |
| 2.8 | Review remaining orphans — archive or add to nav | 193 files | 3h |

### Phase 3: Content Fixes (P1, 2-3 days)

| # | Action | Files | Effort |
|---|--------|-------|--------|
| 3.1 | Update glossary.md to reflect ADR-039 and recent changes | glossary.md | 1h |
| 3.2 | Expand troubleshooting.md (15+ scenarios with decision trees) | troubleshooting.md | 3h |
| 3.3 | Expand migration-5.14-to-6.0.md (all breaking changes) | migration-5.14-to-6.0.md | 2h |
| 3.4 | Fix `--init--` syntax in add-new-source.md and add-pipeline-existing-source.md | 2 files | 30m |
| 3.5 | Complete or remove migration-schema-artifacts.md stub | 1 file | 15m |
| 3.6 | Add dates/versions to 121 undated documents | bulk | 4h |
| 3.7 | Move BIOETL-DATA-EXTRACTION-AND-DASHBOARDS.md to legacy | 1 file | 15m | <!-- doc-lint: allow-legacy -->
| 3.8 | Create MONITORING-INDEX.md content | 1 file | 1h |

### Phase 4: Agent Docs Consolidation (P2, 1-2 days)

| # | Action | Scope | Effort |
|---|--------|-------|--------|
| 4.1 | Establish `.claude/agents/` as SSOT for agent specs; deprecate docs/ copies | agent docs | 1h |
| 4.2 | Remove duplicate subagent specs from `docs/00-project/ai/agents/orchestration/subagents/` | 2 files | 15m |
| 4.3 | Standardize naming convention (kebab-case for files, PascalCase in prompts) | all agent docs | 1h |
| 4.4 | Sync agent-memory.md version to actual RULES.md version | agent-memory.md | 15m |
| 4.5 | Add README to .claude/prompts/ explaining purpose/status | 1 file | 30m |

### Phase 5: Developer Documentation Enhancement (P2, 3-5 days)

| # | Action | Scope | Effort |
|---|--------|-------|--------|
| 5.1 | Add docstrings to 43 Composition layer factory methods | composition/ | 2h |
| 5.2 | Add docstrings to 62 Infrastructure adapter methods | infrastructure/ | 3h |
| 5.3 | Document missing API modules (domain/config, application/composite, infrastructure/checkpoint, infrastructure/locking) | 4 new .md files | 4h |
| 5.4 | Document non-ChEMBL domain schemas (6 providers) | 6 new .md files | 4h |
| 5.5 | Standardize docstring style to Google exclusively | linting config | 1h |

### Phase 6: Housekeeping (P3, 1 day)

| # | Action | Scope | Effort |
|---|--------|-------|--------|
| 6.1 | Move root-level loose docs to proper sections | 2 files | 15m |
| 6.2 | Add README to docs/plans/ and docs/reports/ | 2 files | 30m |
| 6.3 | Remove duplicate report (codex-branches-summary-2026-02-24T13.md) | 1 file | 5m |
| 6.4 | Remove .docx from archive | 1 file | 5m |
| 6.5 | Fix filename typo: 06-diagram-polisy.md → 06-diagram-policy.md | 1 file + refs | 15m |
| 6.6 | Expand PR template (breaking changes, related issues, test coverage) | 1 file | 30m |
| 6.7 | Expand copilot-instructions.md (anti-patterns, hallucination prevention) | 1 file | 1h |
| 6.8 | Fix broken link in CONTRIBUTING.md (../AGENTS.md) | 1 file | 5m |

---

## Required Decisions

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| D-01 | Текущая версия RULES.md — v5.21 или v5.23? | (a) v5.21 + откатить PROJECT-CONTEXT; (b) v5.23 + обновить все docs | Определить и синхронизировать |
| D-02 | Kubernetes deployment — поддерживается или deprecated? | (a) Пометить deprecated с ADR-010; (b) Документировать как optional advanced | (a) Deprecated + disclaimer |
| D-03 | ADR-003 — Accepted (Revised) или Superseded by ADR-010? | (a) Revised in-place; (b) Superseded | (a) Accepted (Revised) + clear note |
| D-04 | Data model docs (03-data-model/) — WIP или completed? | (a) Archive completed; (b) Keep as living docs | Уточнить статус каждого файла |
| D-05 | Aggressive mkdocs nav expansion или selective? | (a) Add all 193 orphans; (b) Curated selection (~100) | (b) Curated + archive остальные |

---

## Verification Checklist

- [ ] RULES.md version consistent across all docs
- [ ] ADR count correct in 00-map.md (39)
- [ ] mkdocs.yml nav coverage > 80% of active docs
- [ ] All ADRs accessible through mkdocs
- [ ] No duplicate ORCHESTRATION.md (single SSOT)
- [ ] All code samples compile (no `--init--` syntax)
- [ ] Glossary updated within 7 days of RULES.md
- [ ] All runbooks accessible through mkdocs
- [ ] All pipeline specs accessible through mkdocs
- [ ] Zero broken nav links in mkdocs.yml

---

## Appendix: Strengths Worth Preserving

1. **RULES.md** — Excellent canonical governance doc (1,715 lines, RFC 2119, detection commands)
2. **39 ADRs** — Mature decision history, consistent template, code references verified
3. **Pipeline specs** — 100% coverage (26/26) with uniform structure
4. **Gold contracts** — 100% coverage (26 JSON exports) with synchronization rules
5. **Code docstrings** — 99.9% class coverage, 82.6% function coverage
6. **Governance policies** — 4 policies fully consistent with RULES.md
7. **Observability contract** — 40+ Prometheus metrics defined and categorized
8. **93 Mermaid diagrams** — Source-first approach with rendering policy

---

*Report generated: 2026-02-25 by Claude Code (6 parallel Explore agents)*
*Total analysis: ~366 markdown files + 546 Python files*
