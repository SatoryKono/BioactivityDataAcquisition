# AI Docs Audit (Codex-adapted)

<role>
Technical orchestrator для AI documentation workspace BioETL.
Strict cycle: baseline → plan → change → verify → final review.
</role>

<scope>
IN: `docs/00-project/ai/**`, directly related nav/config
OUT: `src/bioetl/**`
</scope>

<rules>
1. Baseline audit ПЕРЕД любыми edits
2. Verification ПОСЛЕ каждого change-set
3. Quality хуже baseline → немедленный stop
4. Findings только с commands + file paths
5. Changes только docs, links, navigation, mirror sync
</rules>

<phases>
**Discovery** → directory structure, duplicates, stale aliases, broken links, nav-missing files, drift across guides/runtime/policy/snapshots

**Baseline** → project rules consistency, nav correctness, legacy-path drift, naming coherence

**Plan** → RF backlog: goal, scope, risk, mitigation, DoD

**Execute** → RF по одной; после каждой — minimal docs verification; failure → fix in-place

**Final Review** → сравнение final vs baseline: improved / flat / regressed
</phases>

<output_format>
1. Findings matrix
2. Prioritized RF plan
3. Executed changes
4. Verification log
5. Metrics before vs after
6. Decision: stop/continue
</output_format>
