# Comprehensive Refactoring Plan: Diagram Documentation and Scripts

**Date:** 2026-02-28
**Based on:** Consolidated audit of 5 parallel analyses (82 findings total)
**Overall Score:** 6.5/10 (WARN) — requires remediation to reach PASS (>=8.0)

---

## 1. Problem Statement

The BioETL diagram ecosystem has grown organically to 278 diagram source files, 14 Python scripts, 3 shell scripts, 9+ documentation/policy files, 2 CI workflows, and 12 Makefile targets. This growth has produced a sprawling system plagued by documentation fragmentation, code duplication, incomplete migration from a legacy directory structure, contradictory governance directives, functional script bugs, and CI integration gaps. Five concurrent audits identified 82 distinct issues across documentation duplication, script quality, coverage completeness, CI/CD integration, and ADR-040 compliance. The highest-severity issues include a contradictory colour palette across 6 documents, two critical bugs in diagram processing scripts (one of which silently skips an entire node type during size normalization), full script duplication between legacy and current orphan detection tools, 12 diverged legacy diagram files co-existing with their canonical replacements, and a CI trigger gap that allows script changes to bypass workflow execution entirely.

The refactoring plan below is organized into six phases, ordered by impact and dependency. Each phase addresses a coherent cluster of related findings and is designed to be independently committable. The plan prioritizes functional correctness first (script bugs that produce wrong results), then eliminates divergent authoritative sources (documentation contradictions and duplicates), then completes the incomplete legacy-to-current migration, then consolidates script code into a shared module, then strengthens CI/CD integration, and finally expands quality gate coverage. The total estimated scope is approximately 40-50 discrete file changes across docs, scripts, workflows, Makefile, and skill definitions.

---

## 2. Phase 1: Fix Critical Script Bugs (P0 — Functional Correctness)

**Goal:** Eliminate all script bugs that produce incorrect results or risk data loss.
**Finding IDs:** E-015, E-016, E-017, E-018

### 2.1 Fix Regex in `uniform_diagram_sizes.py` (E-015)

The `_FLOWCHART_NODE_RE` pattern at line 96 has a duplicate `"\)\]` entry instead of a correct `"\]\)` entry for rounded nodes `ID(["Label"])`. This means that any diagram containing rounded-bracket nodes (a common Mermaid pattern) will have those nodes silently skipped during size normalization. The fix requires swapping the second `"\)\]` to `"\]\)` in the closing-bracket alternation group. After fixing, add a unit test that explicitly matches a rounded node to prevent regression.

### 2.2 Fix `has_edge_syntax()` in `check_diagram_quality_gates.py` (E-016)

The function at line 130 defines `FORBIDDEN_EDGE_TOKENS` that include `<--` and `x--`, but the detection logic only checks for `-->`, `-.->`​, `==>`, `---`, and `--x`. Add `"<--"` and `"x--"` to the detection conditions, or refactor so detection is derived directly from the `FORBIDDEN_EDGE_TOKENS` tuple and the `ALLOWED_EDGE_MARKERS` set, eliminating the possibility of future drift between the constant and the check.

### 2.3 Refactor `add_svg_text_fallback.py` Check Mode (E-017)

In `--check` and `--dry-run` modes, the script currently calls `add_fallbacks(path)` which writes modified XML to disk and then attempts to restore the original. This creates a data-loss window if the restore fails (disk full, process killed, permission change). Refactor `add_fallbacks()` to accept an `ET.ElementTree` or string and return a modified tree without performing disk I/O. Only call `tree.write()` in `--fix` mode. The `--check` mode should compare the returned tree against the original in memory and report differences without touching the filesystem.

### 2.4 Fix Blanket String Replacement in `fix_diagram_links.py` (E-018)

Line 21 performs `content.replace(".mmd", ".mermaid")` globally, corrupting any occurrence of `.mmd` in prose text, code blocks, and comments. Remove this blanket replacement entirely. The subsequent regex-based link fixer on line 40 already handles link-specific conversions. If blanket replacement was intended as a catch-all, replace it with a properly scoped regex that only matches `.mmd` when it appears as a file extension within markdown link syntax (e.g., `\]\([^)]*\.mmd\)` or similar). Additionally, add a proper shebang, argparse interface, docstring, and exit code handling to this script, which is currently the lowest-quality script in the toolchain (finding AUD-021 from Audit #2).

---

## 3. Phase 2: Eliminate Documentation Contradictions and Duplicates (P1 — Single Source of Truth)

**Goal:** Establish a clear, non-contradictory documentation hierarchy.
**Finding IDs:** E-001 through E-008, D-001 through D-006, E-020, E-021

### 3.1 Hard-Deprecate `00-diagramming-policy.md` (E-001, E-002, E-021, D-004)

This 275-line file contains a contradictory colour palette (single-hex Orange/Silver/Gold vs. canonical fill+stroke pairs), recommends PlantUML and ASCII Art (contradicting the Mermaid-only mandate), and has a weaker Definition of Done (4 criteria vs 5 in the canonical policy). Although it carries a "historical reference" note, the note is too subtle. Replace the entire file content with a 5-line deprecation stub:

```markdown
# Diagramming Policy (DEPRECATED)

> **This document is DEPRECATED.** All diagram governance is defined in:
> - [ADR-040](../../decisions/ADR-040-diagram-governance.md) — Authoritative governance
> - [06-diagram-policy.md](../../06-diagram-policy.md) — Canonical operational policy

See the files above for current rules, colour palette, and tooling.
```

This single change resolves findings E-001 (contradictory palette), E-002 (PlantUML recommendation), E-021 (stale content), D-004 (duplicate Definition of Done), and E-014 (broken relative path to 00-map.md, which becomes moot with the stub).

### 3.2 Consolidate Colour Palette to Two Canonical Locations (D-001)

Currently duplicated across 6 files. After removing the palette from `00-diagramming-policy.md` (step 3.1), reduce to exactly two canonical locations: (a) `theme/mermaid-config.json` for programmatic consumption and (b) `_template.mmd` header comments for copy-paste into new diagrams. In `06-diagram-policy.md`, `ADR-040`, `README.md`, and `mermaid-design.md`, replace inline palette tables with a one-line cross-reference: "See `_template.mmd` lines 19-36 and `theme/mermaid-config.json` for canonical colours."

### 3.3 Fix Skill File Inconsistencies (E-006, E-008, E-010, E-013)

In `.claude/skills/mermaid-design.md`:
- **Line 40:** Remove dead reference to `.codex/skills/technical-designer-mermaid/SKILL.md` (E-010). The skill file itself is the full specification.
- **Line 59:** Change path from `docs/02-architecture/diagrams/mermaid/{category}/{name}.mermaid` to `docs/02-architecture/mmd-diagrams/views/{name}.mermaid` (E-013).
- **Line 77:** Replace `{"flowchart": {"defaultRenderer": "elk"}}` with `{'layout': 'elk', 'elk': {...}}` to match ADR-040 D8 and Mermaid v11+ syntax (E-008).
- **Lines 197-198, 203-204:** Replace non-canonical Material colours `#2e7d32` (orchestration) and `#6a1b9a` (DI) with canonical ADR-040 values `#16a34a` and `#7c3aed` respectively (E-006). These Material colours would currently trigger COLOUR-003 lint errors if used in diagrams, creating a paradox where following the skill's guidance produces policy violations.

### 3.4 Fix `architecture-diagrams.md` (E-011, E-012)

Change all 13 broken `.mermaid` references to `.mmd` (the actual extension used by foundation files). Fix the link at line 410 where display text says `30-port-adapter-mapping` but the URL targets `26-hexagonal-ports-adapters`.

### 3.5 Resolve ELK edgeRouting Default (E-003)

`06-diagram-policy.md` says POLYLINE; `ADR-040` and `_template.mmd` say ORTHOGONAL; the skill provides context-dependent guidance. Since all actual `.mmd` files use ORTHOGONAL and ADR-040 is authoritative, update `06-diagram-policy.md` section 6.4 to specify ORTHOGONAL as the default, matching the template and actual files. Note the skill's context-dependent guidance (POLYLINE for 11-30 nodes, ORTHOGONAL for >30) as an advisory note.

### 3.6 Synchronize Lint Rule Documentation (D-002, G-005)

ADR-040 lists 8 lint rules; `README.md` lists 13; actual `lint_diagrams.py` implements 15+. Add a comprehensive lint rule table to ADR-040 Decision D6, covering all implemented rules with their IDs, severities, and descriptions. In `README.md`, add a cross-reference note: "Complete rule list defined in ADR-040 D6." This eliminates the divergence where adding a new lint rule requires updating multiple places.

### 3.7 Merge or Cross-Reference `architecture-diagrams.md` (D6) and `README.md` (D9) (D-006)

These two files (744 lines + 346 lines) have significant overlap. Reduce `architecture-diagrams.md` to a lightweight overview (100-150 lines) of the diagram ecosystem with links to `README.md` for detailed diagram listings. This deduplicates the foundation diagram inventory, port counts, and directory structures.

### 3.8 Archive `diagram-catalog.md` (E-020)

The 500-diagram aspirational catalog has ~240 entries that don't correspond to actual files. Move it to `docs/99-archive/diagram-catalog-aspirational.md` and add a note explaining it was an early planning document. Replace the reference in `architecture-diagrams.md` with a link to `diagrams-index.md` which accurately reflects the actual inventory.

---

## 4. Phase 3: Complete Legacy Migration (P1 — Data Hygiene)

**Goal:** Remove all vestiges of the pre-ADR-040 `diagrams/mermaid/` directory structure.
**Finding IDs:** D-015, G-003, G-004, E-024

### 4.1 Delete Legacy `diagrams/mermaid/` Directory (D-015, G-003)

All 12 legacy `.mermaid` files have diverged from their canonical counterparts in `mmd-diagrams/views/`. The canonical copies are newer and more complete. Delete `docs/02-architecture/diagrams/mermaid/` entirely. This also resolves E-024 (render.sh rendering stale legacy files).

### 4.2 Update All Legacy Path References (G-004)

After deleting the legacy directory, update 41+ references across documentation. In `diagram-descriptions/INDEX.md`, change 12 entries pointing to `diagrams/mermaid/` to point to `mmd-diagrams/views/`. In the 12 description cards under `diagram-descriptions/diagrams/mermaid/`, either redirect to `mmd-diagrams/views/` descriptions or merge them. In `diagrams-index.md`, remove the line about legacy snapshots. In planning docs under `docs/plans/`, add a note that paths refer to pre-migration state.

### 4.3 Add Legacy Exclusion to `render.sh` (E-024)

While the directory is being deleted in 4.1, as a defense-in-depth measure, also add `"docs/02-architecture/diagrams"` to the `EXCLUDE_PATHS` array in `render.sh` line 250 alongside the existing `docs/99-archive` exclusion. This prevents future accidental re-creation of legacy files from being rendered.

### 4.4 Generate 19 Missing Description Cards (G-001, G-002)

Create description `.md` files for the 19 architecture sub-diagrams that lack them: `03a, 06a, 06b, 07a, 07b, 08a, 08b, 09a, 09b, 11a, 11b, 13e, 13f, 14a, 14b, 16a, 16b, 18a, 18b`. Use the `py-doc-bot` agent or `build_diagram_docs.py` tool to generate descriptions from the diagram source content. Regenerate `INDEX.md` with the updated count (target: 289 entries to match 277 non-template diagrams plus legacy descriptions).

---

## 5. Phase 4: Script Consolidation (P2 — Technical Debt)

**Goal:** Eliminate code duplication and dead scripts through a shared utility module.
**Finding IDs:** D-007 through D-014, E-022, E-023

### 5.1 Create `scripts/diagram_utils.py` Shared Module (D-007 through D-013)

Extract the following functions into a new `scripts/diagram_utils.py` module:

- `load_manifest(path: Path, allowed_suffixes: set[str] | None = None) -> list[Path]` — unified manifest loader replacing 5 divergent implementations.
- `is_flowchart(lines: list[str]) -> bool` — single canonical implementation resolving the 3-way divergence where `lint_diagrams.py` skips empty lines but the other two do not. Choose the `lint_diagrams.py` behavior as canonical (skip comments and empty lines before the first directive).
- `normalize_label(text: str) -> str` — extract from 2 copies.
- `class_tokens(element: ET.Element) -> set[str]` — extract from 2 copies.
- `local_name(tag: str) -> str` — extract from 2 copies.
- `collect_svg_files(directory: Path, manifest: list[Path] | None = None) -> list[Path]` — extract from 2 copies.
- Output helpers: `out(msg: str)` and `err(msg: str)` — extract from 5 copies. Include ANSI colour constants.

Update all 10+ consuming scripts to import from `diagram_utils`. This is the highest-leverage change in the entire refactoring — it reduces approximately 300 lines of duplicated code, eliminates the divergent `is_flowchart()` logic that can produce different results in different scripts, and creates a single point of maintenance for manifest loading behavior.

### 5.2 Delete Legacy `mermaid_prune_orphans.py` (D-014, E-022)

This 300-line script is entirely superseded by the 762-line `prune_orphan_nodes.py`, which adds grandfather mode, JSON output, advanced subgraph handling, and lenient child-node rules. `lint_diagrams.py` already imports from `prune_orphan_nodes.py`. Delete `mermaid_prune_orphans.py` and verify no remaining references. Update any Makefile targets or documentation that reference the old script name.

### 5.3 Delete Deprecated `render_diagrams.py` (AUD-019 from Audit #2)

This 289-line script has a docstring stating to use `render.sh` instead. It is not referenced by any workflow, Makefile target, or other script. Delete it. The canonical rendering path is `docs/02-architecture/mmd-diagrams/render.sh` invoked via `make render-diagrams`.

### 5.4 Fix Minor Quality Issues (E-023, AUD-024, AUD-027)

Remove unused `import os` from `fix_diagram_links.py`. Fix typo `nbps_per_line` to `nbsp_per_line` in `report_diagram_padding.py`. Move the `sys.path.insert` in `lint_diagrams.py:797-798` from call-time to module-level import with a guard, or refactor the `prune_orphan_nodes` import to use a proper package structure.

---

## 6. Phase 5: Strengthen CI/CD Integration (P2 — Automation)

**Goal:** Close gaps between local Makefile targets, CI workflow steps, and the unified check runner.
**Finding IDs:** G-011, G-014, G-015, G-016, AUD-009, AUD-011 from Audit #4

### 6.1 Wire `run_diagram_checks.sh` into Workflows (AUD-011)

The 283-line unified runner with `--profile pr|nightly|quick` is documented, tested by architecture tests, but never actually invoked by any workflow or Makefile target. Replace the manually replicated steps in `docs.yml` and `diagram-nightly.yml` with calls to `run_diagram_checks.sh --profile pr` and `--profile nightly` respectively. This ensures that adding a new check to the runner automatically propagates to CI without requiring parallel edits to workflow files.

### 6.2 Expand `docs.yml` Path Triggers (G-014)

Add `scripts/*diagram*`, `scripts/*mermaid*`, `scripts/*svg*`, `scripts/lint_diagrams.py`, `scripts/prune_orphan_nodes.py`, `src/tools/harmonize_link_styles.py`, and `docs/02-architecture/mmd-diagrams/render.sh` to the `paths:` trigger in `docs.yml`. Currently, changes to these scripts do not trigger the diagram validation workflow.

### 6.3 Add Missing Makefile Targets (G-011, AUD-009, AUD-012)

Add new Makefile targets for the three scripts that are in CI but not in Makefile: `check-diagram-artifacts`, `check-diagram-smoke`, `check-diagram-quality-gates`. Include all three in the `diagrams-all` aggregate target. Optionally add a `diagrams-pr` target that invokes `run_diagram_checks.sh --profile pr` for developers who want to run the full PR validation locally.

### 6.4 Fix Mermaid Version Mismatch (E-009)

Update Makefile `vendor-mermaid` target from version `10.4.0` to `10.6.1` to match CI workflows. Additionally, create a cross-platform vendoring script (bash or Python) to replace the Windows-only PowerShell script, or add a conditional that uses `curl`/`wget` on Linux and PowerShell on Windows.

### 6.5 Add Nightly Failure Notification (G-016)

Add a final step to `diagram-nightly.yml` conditioned on `if: failure()` that creates a GitHub Issue with the label `diagram-regression` summarizing the failed checks. This ensures nightly regressions are not silently missed.

### 6.6 Add Missing Lint Step to Nightly (G-015)

Add `python3 scripts/lint_diagrams.py docs/02-architecture/mmd-diagrams` to the nightly-phase2 job between syntax validation and render. This is already part of the `--profile nightly` in `run_diagram_checks.sh`, so step 6.1 would resolve this automatically.

---

## 7. Phase 6: Expand Coverage and Quality Gates (P3 — Hardening)

**Goal:** Increase regression detection from 1.8% to a meaningful baseline.
**Finding IDs:** G-007, G-009, G-010

### 7.1 Add @nodes Metadata to Foundation and Class-Diagram Files (G-007)

70 of 121 `.mmd` files lack `@nodes` metadata, causing SIZE and LAYOUT lint rules to be silently skipped. Add `@nodes` counts to all 54 foundation files and 16 class-diagram files. This can be done programmatically by counting flowchart node definitions (`[a-zA-Z_]+[\[\(\{]`) in each file. After adding, re-run `lint_diagrams.py` to identify any diagrams that now exceed the 35-node threshold requiring decomposition.

### 7.2 Expand Quality-Gate Manifest (G-009, G-010)

Expand `quality-gate-manifest.txt` from 5 entries to at least 18, covering one diagram per architectural category (architecture, class-diagrams, foundation, views) and all diagrams referenced in key documentation sections. Similarly expand `visual-smoke-manifest.txt`. The manifests should include at minimum the 12 diagrams that have full descriptions in `diagram-descriptions/diagrams/mermaid/`, as these represent the most critical visualizations.

### 7.3 Resolve Architecture 13-Series Naming Collision (AUD-009 from Audit #3)

Rename the alternate slices `13a-port-contracts-data-sources.mmd`, `13b-port-contracts-storage.mmd`, `13c-port-contracts-observability.mmd` to `13g-port-contracts-data-sources.mmd`, `13h-port-contracts-storage.mmd`, `13i-port-contracts-observability.mmd` to eliminate the collision with `13a-data-storage-ports.mmd`, `13b-operational-ports.mmd`, `13c-validation-dq-ports.mmd`. Update any references in descriptions, README, and INDEX.md.

---

## 8. Execution Order and Dependencies

```
Phase 1 (Script Bugs)           ─── No dependencies, start immediately
Phase 2 (Doc Contradictions)    ─── No dependencies, can run parallel with Phase 1
Phase 3 (Legacy Migration)      ─── Depends on Phase 2 (doc fixes should come first)
Phase 4 (Script Consolidation)  ─── Depends on Phase 1 (bugs fixed before refactoring)
Phase 5 (CI/CD)                 ─── Depends on Phase 4 (consolidated scripts wired in)
Phase 6 (Coverage)              ─── Depends on Phase 3 + 4
```

Phases 1 and 2 can proceed in parallel. Each phase is independently committable and testable:
- **Phase 1 validation:** Run `pytest tests/architecture/` and manual verification of the 4 fixed scripts.
- **Phase 2 validation:** Run `make lint-diagrams` and verify all cross-references resolve.
- **Phase 3 validation:** Run `make render-diagrams` and verify no references to deleted paths.
- **Phase 4 validation:** Run full test suite; verify all scripts import from `diagram_utils`.
- **Phase 5 validation:** Trigger CI workflows manually; verify `make diagrams-all` covers all checks.
- **Phase 6 validation:** Run `make lint-diagrams` with @nodes added; verify expanded manifests pass quality gates.

---

## 9. Expected Outcome

After completing all six phases:

| Metric | Current | Target |
|--------|---------|--------|
| Overall audit score | 6.5/10 (WARN) | >=8.0/10 (PASS) |
| Documentation contradictions | 9 | 0 |
| Broken references | 5 | 0 |
| Script bugs (CRITICAL/HIGH) | 6 | 0 |
| Duplicated functions | 14 instances across 10 scripts | 0 (all in diagram_utils.py) |
| Dead/legacy scripts | 2 (render_diagrams.py, mermaid_prune_orphans.py) | 0 |
| Legacy diagram files | 12 diverged copies | 0 |
| Quality-gate coverage | 1.8% (5/277) | ~6.5% (18/277) minimum |
| @nodes metadata coverage | 42% (51/121 .mmd files) | 100% |
| Authoritative policy documents | 6+ (with contradictions) | 2 (ADR-040 + 06-diagram-policy.md) |

---

*Plan generated from consolidated findings of 5 parallel audits. Total findings addressed: 82.*
