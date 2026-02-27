# Documentation Cascade Audit Report — BioETL

**Date:** 2026-02-27
**Scope:** Full exhaustive audit (550 Python files, ~294 active docs)
**Auditor:** Claude Code — 8 parallel audit agents
**Project Version:** v6.0.0 | RULES.md v5.22

---

## Executive Summary

| Agent | CRITICAL | HIGH | MEDIUM | LOW | INFO | Total |
|-------|----------|------|--------|-----|------|-------|
| LA-DOMAIN | 0 | 4 | 15 | 10 | 0 | 29 |
| LA-APPLICATION | 0 | 0 | 16 | 28 | 11 | 55 |
| LA-INFRASTRUCTURE | 0 | 3 | 10 | 17 | 0 | 30 |
| LA-COMPOSITION | 0 | 12 | 15 | 10 | 0 | 37 |
| LA-INTERFACES | 0 | 0 | 10 | 25 | 0 | 35 |
| ARCH | 0 | 2 | 6 | 4 | 4 | 16 |
| GOV | 0 | 9 | 5 | 5 | 1 | 20 |
| XREF | 2 | 4 | 6 | 3 | 3 | 18 |
| **TOTAL** | **2** | **34** | **83** | **102** | **19** | **240** |

**Overall Score: 7.1/10 — WARN**

---

## CRITICAL Findings (2)

### CDOC-001 | XREF-001 | Extra `../` in Relative Paths from `docs/00-project/`
- **Sources:** `docs/00-project/index.md`, `00-map.md`, `RULES.md`, `docs/03-guides/`
- **Impact:** 17 broken cross-references to ADR-014, ADR-025, add-new-source
- **Fix:** Replace `../../` with `../` in all affected links

### CDOC-002 | XREF-004 | 270 Missing PNG Images in INDEX.md Files
- **Sources:** 5 PNG INDEX.md files in `mmd-diagrams/`
- **Impact:** Every diagram image reference is broken (0 PNGs exist)
- **Fix:** Remove placeholder INDEX.md files (PNGs not yet generated)

---

## HIGH Findings (34) — Top Priority

### Documentation Structure
- **CDOC-003** | ARCH-DOC-001 | ADR-008 status "Superseded" in file but "Accepted" in README
- **CDOC-004** | ARCH-DOC-003 | `00-overview.md` lists 34 ADRs, actual count is 40
- **CDOC-005** | ARCH-DOC-004→006 | Stale ADR ranges in `00-map.md` (39→40), `CLAUDE.md` (38→40), `AGENT.md` (38→40)
- **CDOC-006** | XREF-009 | Missing `subcellular-fraction.md` (referenced in mkdocs.yml nav)
- **CDOC-007** | XREF-002→003 | Wrong relative depth in `mmd-diagrams/docs/` (5 broken links)
- **CDOC-008** | XREF-015 | 27 orphan docs not in nav and not cross-referenced

### Governance
- **CDOC-009** | GOV-001→008 | ~20 prompt/skill files reference old RULES.md versions (v5.14, v5.19)
- **CDOC-010** | GOV-018 | 33.7% mkdocs orphan rate (99/294 docs)
- **CDOC-011** | GOV-020 | `00-map.md` metrics outdated (ADR count, config count, diagram count)

### Composition Layer (12 HIGH findings)
- **CDOC-012** | LA-COMP-007→011 | `GenericPipelineFactory` methods lack Args/Returns
- **CDOC-013** | LA-COMP-019 | `StorageFactory._create_storage_adapter()` (17 params, minimal docstring)
- **CDOC-014** | LA-COMP-023 | `StorageAdapter.__init__()` has NO docstring
- **CDOC-015** | LA-COMP-024→026 | Inconsistent doc depth across provider registration functions
- **CDOC-016** | LA-COMP-028→032 | 6 private assembly helpers in `runner_builder.py` missing docstrings

### Domain Layer (4 HIGH findings)
- **CDOC-017** | LA-DOMAIN-001 | `validate_year_range()` docstring claims wrong defaults
- **CDOC-018** | LA-DOMAIN-002 | `_normalize_partial_month()` vs `format_date_parts()` inconsistency
- **CDOC-019** | LA-DOMAIN-003 | `Bioactivity.from_raw()` (99 LOC) has only one-line docstring
- **CDOC-020** | LA-DOMAIN-004 | 84 lines of Cyrillic in domain docstrings

### Infrastructure Layer (3 HIGH findings)
- **CDOC-021** | LA-INFRA-012 | ChEMBL adapter under-documented
- **CDOC-022** | LA-INFRA-018 | Health-aware batch sizing undocumented
- **CDOC-023** | LA-INFRA-023 | Default retry config values not documented

### Cross-Reference
- **CDOC-024** | XREF-006 | `ADR-0005` should be `ADR-005` (3 files)
- **CDOC-025** | XREF-007 | Wrong ADR filename in `composition/__init__.py`

---

## Fix Plan (This Iteration)

### Batch 1: Critical Link Fixes
- Fix 17 `../../` → `../` broken relative paths
- Remove 5 empty PNG INDEX.md placeholder files

### Batch 2: ADR Status and Count Fixes
- Fix ADR-008 status in decisions/README.md
- Update ADR count in 00-overview.md (34→40), add ADR-035..040
- Update ADR range in 00-map.md (39→40), CLAUDE.md (38→40), AGENT.md (38→40)

### Batch 3: Missing Docs and Reference Fixes
- Create `subcellular-fraction.md` provider doc
- Fix ADR-0005 → ADR-005 in 3 source files
- Fix ADR filename in composition/__init__.py

### Batch 4: Russian→English Translations (Domain + Composition)
- Translate Cyrillic docstrings in domain/ and composition/ layers

### Batch 5: HIGH-priority Docstring Improvements
- Composition layer factory methods
- Domain key methods (Bioactivity.from_raw, validate_year_range)

---

*Report generated: 2026-02-27 by Claude Code (8 parallel agents)*
