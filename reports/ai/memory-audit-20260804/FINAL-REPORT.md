# AI Agent Memory Audit — Final Report (5 cycles)

- **Date:** 2026-08-04
- **Repository:** `SatoryKono/BioactivityDataAcquisition`
- **Target branch:** `main` (`f6e4ee589baa58fca81a149819266d20c41d8de2` at program start)
- **Working branch:** `fix/ai-memory-audit-cycle-20260804`
- **PR:** https://github.com/SatoryKono/BioactivityDataAcquisition/pull/7487
- **CYCLE_COUNT:** 5
- **REQUIRE_GITHUB_TRACKING_BEFORE_IMPLEMENTATION:** true

---

## 1. Executive Summary

Выполнены ровно пять полных трёхэтапных циклов аудита AI agent memory / runtime.

| Cycle | Audit mode | New findings | Stage 3 outcome |
| --- | --- | ---: | --- |
| CYCLE-01 | full | 3 | remediations landed; PR #7487 |
| CYCLE-02 | differential | 0 | `NO_ACTIONABLE_FINDINGS` |
| CYCLE-03 | differential | 0 | `NO_ACTIONABLE_FINDINGS` |
| CYCLE-04 | differential | 0 | `NO_ACTIONABLE_FINDINGS` |
| CYCLE-05 | differential | 0 | `NO_ACTIONABLE_FINDINGS` |

Подтверждённые дефекты CYCLE-01 устранены локально и на рабочей ветке; Issues #7482–#7484 в состоянии `RESOLVED_AWAITING_PR_OR_MERGE` до merge PR #7487.

---

## 2. Scope and Methodology

### Fixed parameters

```text
CYCLE_COUNT: 5
REQUIRE_GITHUB_TRACKING_BEFORE_IMPLEMENTATION: true
INITIAL_AUDIT_MODE: full
FOLLOWUP_AUDIT_MODE: differential
```

### Method

1. Normative load per `AGENTS.md` precedence.
2. Runtime inventory (existence + tracked status; candidate ≠ active).
3. Memory taxonomy separation (procedural / semantic / episodic / project; canonical vs mirror vs cache).
4. Evidence-based findings only; GitHub tracking before remediation.
5. Cycle Closeout Verification after each Stage 3.

### Out of scope for this program

- CI findings #7480, #7473, #7402 (not AI memory).
- Local-only IDE state (`.idea/*`, machine Gemini config).
- Secret-bearing `.env` surfaces (not modified).

---

## 3. Normative Source Baseline

| Source | Path | Status |
| --- | --- | --- |
| AI entry | `AGENTS.md` | present, equal-peer runtime contract |
| Normative index | `docs/00-project/NORMATIVE_SOURCES.md` | present |
| Rules | `docs/00-project/RULES.md` | present |
| Requirements | `docs/01-requirements/REQUIREMENTS.md` | present |
| Memory usage | `docs/00-project/ai/agents/guides/MEMORY_USAGE.md` | present |
| Mirror ownership | `docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md` | present |
| Post-change | `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` | present |
| Codex runtime | `.codex/agents/CODEX-RUNTIME.md` | runtime SSOT for Codex |
| Junie runtime | `.junie/agents/JUNIE-RUNTIME.md` | runtime SSOT for Junie |
| Mirror contract | `scripts/ai/junie/junie-mirror-contract.json` | enforces codex_only for CODEX-RUNTIME |

Precedence: active runtime source → runtime profiles/skills → NORMATIVE_SOURCES → RULES → REQUIREMENTS → ADRs. Docs mirrors are not independent runtime SSOT.

---

## 4. Agent and Runtime Inventory

| Agent/runtime | Config entry point | Runtime proven | Skills | MCP | Persistent memory | Session memory | Shared memory | Status |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| Codex | `.codex/agents/CODEX-RUNTIME.md` | yes (tracked peer) | `.codex/skills/**` | via `.mcp.json` / scripts | `src/memory/**` curated+episodic | episodic tasks | project docs/ai mirrors | **active peer** |
| Junie | `.junie/agents/JUNIE-RUNTIME.md` | yes (tracked peer) | `.junie/skills/**` | shared | same package | same | same | **active peer** |
| Devin | `.devin/` + skills | present tracked | `.devin/skills/**` | NOT_PROVEN as default | same package | same | same | **active tracked** |
| Gemini | `.gemini/settings.json` | machine-local config only | no tracked agents/skills tree on main | NOT_PROVEN | same package | same | same | **config-only** |
| Cursor | `.cursor/` | present; rules/skills absent | absent | NOT_PROVEN | n/a | n/a | n/a | **partial/candidate** |
| GitHub Copilot | `.github/copilot-instructions.md` + instructions | docs surface | n/a | n/a | n/a | n/a | n/a | **instructions** |
| Claude / Windsurf | paths absent | no | no | no | n/a | n/a | n/a | **absent** |
| Memory package | `src/memory/**` + `python -m memory.tooling.workflow` | yes | n/a | neo4j MCP scripts | curated/episodic/derived | session notes | FAIL-closed durable writes | **tooling subsystem** (not `src/bioetl` domain) |

---

## 5. Memory Taxonomy

| Class | Location examples | Notes |
| --- | --- | --- |
| Procedural | runtime maps, skills, workflow CLI | how to act |
| Semantic / curated | `src/memory/curated/**` | durable, review cadence 90d |
| Episodic | `src/memory/episodic/**` | task-scoped, TTL/prune |
| Project docs | `docs/00-project/ai/**` | mirrors / guidance |
| Derived / cache | `src/memory/derived/**`, RAG/timeline projections | rebuildable, not SSOT |
| Session / local | IDE state, `.gemini/settings.json` | not project truth |

---

## 6. Memory Artifact Inventory (high-signal)

| Artifact | Role | Fingerprint (sha256 prefix) after CYCLE-01 |
| --- | --- | --- |
| `src/memory/tooling/workflow.py` | pre/post/smoke workflow | `3bb6c768000d` |
| `.codex/agents/CODEX-RUNTIME.md` | Codex SSOT | `cab5110b170c` |
| `.junie/agents/CODEX-RUNTIME.md` | pointer stub | `e3b22ffb062a` |
| `.junie/agents/JUNIE-RUNTIME.md` | Junie SSOT | `3c4561759454` |
| `scripts/ai/junie/junie-mirror-contract.json` | parity contract | `0d60f8c08d91` |
| curated notes (3 re-verified) | semantic memory | last_verified `2026-08-04` |

---

## 7. Per-Agent Audit (summary)

### Codex

- Provenance env guidance present in CODEX-RUNTIME.
- Skills catalog under `.codex/skills/**`.
- Memory writes require `BIOETL_AI_RUNTIME` + `BIOETL_AI_AGENT`.

### Junie

- Equal peer via mirror contract.
- CODEX-RUNTIME historically diverged (truncated); fixed to pointer in CYCLE-01.
- JUNIE-RUNTIME is peer SSOT.

### Devin

- Tracked `.devin/**` present; subordinate to repo governance.
- No new AI-MEM defect confirmed in this program.

### Gemini / Cursor / others

- No evidence of independent durable memory backend separate from `src/memory`.
- `.gemini/settings.json` is machine-local; not promoted to project SSOT.

---

## 8. Current Memory Data Flow

```text
Agent runtime (codex|junie|devin|…)
  → set BIOETL_AI_RUNTIME / BIOETL_AI_AGENT [/ BIOETL_AI_MODEL]
  → python -m memory.tooling.workflow pre-task
       → retrieval (catalog/RAG/timeline profiles)
       → optional session note (FAIL-closed provenance)
  → work
  → python -m memory.tooling.workflow post-task
       → summary note + optional promote/prune/refresh
  → smoke: temporary identity inject → pre/post → restore env
```

---

## 9. Precedence and Conflict Resolution

Documented in `AGENTS.md` and mirror ownership policy. Codex and Junie are equal peers; CODEX-RUNTIME is codex_only per contract (not mirrored). No parallel precedence invented.

---

## 10. Shared Memory and Multi-Agent Coordination

Shared surfaces: `src/memory/**` and docs mirrors. Isolation relies on:

- Actor identity in record envelopes.
- Task/branch/worktree scope.
- FAIL-closed durable writes without runtime/agent env.

No multi-writer race finding proven beyond the smoke gap fixed in CYCLE-01.

---

## 11. Freshness, Invalidation and Provenance

| Control | Evidence |
| --- | --- |
| Curated review cadence | 90d via retention policy |
| review_curated after fix | due_count=0 |
| Provenance | envelope binds runtime/agent/model/commit/branch/task |
| Smoke provenance | injected only inside smoke |

---

## 12. Security, Privacy and Memory Poisoning

- Durable write path asserts security/trust classes.
- Smoke uses non-production identity; does not weaken production fail-closed.
- No secrets/PII introduced in curated notes.
- `.env` surfaces not modified.

---

## 13. Performance and Growth

- Episodic prune tooling present; density controls in prune report.
- No new unbounded growth finding confirmed this program.

---

## 14. Duplication and Drift Analysis

| Surface | Finding | Status |
| --- | --- | --- |
| Junie CODEX-RUNTIME vs Codex | silent drift outside parity scope | **fixed** (pointer) |
| Curated source_refs pollution | body text in source_refs | **fixed** on re-verify |
| Skills codex↔junie | parity check OK historically | no new drift |

---

## 15. Findings Register

| Finding | Fingerprint | Severity | Lifecycle | First | Last | Issue | Remediation | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AI-MEM-C1-001 | smoke missing provenance inject | P1 | remediated_awaiting_merge | C01 | C05 | #7484 | smoke inject+restore | smoke ok + tests |
| AI-MEM-C1-002 | junie CODEX-RUNTIME truncated fork | P2 | remediated_awaiting_merge | C01 | C05 | #7483 | pointer stub | mirror check OK |
| AI-MEM-C1-003 | curated due_count=3 | P2 | remediated_awaiting_merge | C01 | C05 | #7482 | re-verify notes | due_count=0 |

Regression checks C02–C05: no regression of closed/remediated findings.

---

## 16. GitHub Issues Register

| Finding | Issue | Action | State | Commit/PR | Close reason |
| --- | --- | --- | --- | --- | --- |
| AI-MEM-C1-001 | #7484 | create + remediate | open (await merge) | PR #7487 | pending merge |
| AI-MEM-C1-002 | #7483 | create + remediate | open (await merge) | PR #7487 | pending merge |
| AI-MEM-C1-003 | #7482 | create + remediate | open (await merge) | PR #7487 | pending merge |

No issue created without confirmed finding. No formal close of BLOCKED/DEFERRED.

---

## 17. Remediation Register

| ID | Outcome | Evidence commands |
| --- | --- | --- |
| AI-MEM-C1-001 | `RESOLVED_AWAITING_PR_OR_MERGE` | `python -m memory.tooling.workflow smoke --json` |
| AI-MEM-C1-002 | `RESOLVED_AWAITING_PR_OR_MERGE` | `bash scripts/ai/junie/check_junie_mirror.sh --check` |
| AI-MEM-C1-003 | `RESOLVED_AWAITING_PR_OR_MERGE` | `python -m memory.tooling.workflow review-curated --json` |

---

## 18. Cycle-by-Cycle Ledger

### CYCLE-01 (full)

| Field | Value |
| --- | --- |
| cycle_start_sha | `f6e4ee589b` |
| cycle_end_sha | `3f9b8376df` (includes `43e9e6d235` remediations + ledger) |
| Stage 1 | 3 findings confirmed |
| Stage 2 | Issues #7484, #7483, #7482 |
| Stage 3 | remediations + tests + PR #7487 |
| Closeout | PASS |

### CYCLE-02 (differential)

| Field | Value |
| --- | --- |
| cycle_start_sha | `3f9b8376df` |
| cycle_end_sha | `3f9b8376df` (no code change) |
| Stage 1 | normative + regression + fingerprints stable; P0/P1 recheck OK |
| Stage 2 | GitHub reconcile: AI-MEM issues open awaiting merge; no new tracking needed |
| Stage 3 | `NO_ACTIONABLE_FINDINGS` |
| Closeout | PASS |

### CYCLE-03 (differential)

| Field | Value |
| --- | --- |
| cycle_start/end_sha | `3f9b8376df` |
| Stage 1 | recheck closed/remediated findings; smoke/review_curated/mirror OK |
| Stage 2 | no new issues; existing linked to PR #7487 |
| Stage 3 | `NO_ACTIONABLE_FINDINGS` |
| Closeout | PASS |

### CYCLE-04 (differential)

| Field | Value |
| --- | --- |
| cycle_start/end_sha | `3f9b8376df` |
| Stage 1 | fingerprint unchanged for key surfaces; no new drift |
| Stage 2 | GitHub state unchanged |
| Stage 3 | `NO_ACTIONABLE_FINDINGS` |
| Closeout | PASS |

### CYCLE-05 (differential)

| Field | Value |
| --- | --- |
| cycle_start/end_sha | `3f9b8376df` |
| Stage 1 | final regression; inventory reaffirmation |
| Stage 2 | final issue/PR reconcile |
| Stage 3 | `NO_ACTIONABLE_FINDINGS` |
| Closeout | PASS — program complete |

---

## 19. Gap Analysis

| Gap | Status |
| --- | --- |
| Smoke unusable without env | closed in branch |
| Junie CODEX-RUNTIME silent drift | closed in branch |
| Curated due reviews | closed in branch |
| Optional architecture guard “pointer-only junie CODEX-RUNTIME” | not implemented (optional AC); deferred by scope — no budget increase |
| Devin deep memory isolation proof | NOT_PROVEN beyond package-level controls |
| Cursor skills/rules empty | candidate surface; not a defect |

---

## 20. Target Memory Architecture (vendor-neutral)

1. **Equal-peer runtimes** with explicit SSOT maps (no content forks of foreign runtime maps).
2. **Single durable memory package** (`src/memory`) outside BioETL domain hexagon.
3. **FAIL-closed actor provenance** on all durable writes.
4. **Deterministic smoke** with temporary non-production identity.
5. **Curated vs episodic** separation with review cadence and prune.
6. **Mirrors ≠ SSOT**; contract-enforced parity for shared skill/agent surfaces.
7. **Derived/RAG/timeline** rebuildable; never treat cache as project memory.

---

## 21. Remaining Risks and Blockers

| Risk | Severity | Notes |
| --- | --- | --- |
| PR #7487 not yet merged | process | Issues remain open until merge |
| External CI open issues | unrelated | #7480, #7473, #7402 outside AI-MEM scope |
| Optional pointer guard | low | not required for closeout |
| Token/local git push friction | ops | MCP used for remote updates |

---

## 22. Verification Strategy

```text
# Smoke health
python -m memory.tooling.workflow smoke --json

# Curated freshness
python -m memory.tooling.workflow review-curated --json

# Mirror parity
bash scripts/ai/junie/check_junie_mirror.sh --check

# Integration tests
pytest tests/integration/memory/test_workflow_tooling.py -k "smoke or pre_task_rejects or review_curated"

# Fail-closed durable write (manual)
# unset BIOETL_AI_RUNTIME/AGENT → pre-task with session_note_path must raise ValueError
```

Observed post-remediation:

- smoke `ok=true`, actor `smoke` / `memory-workflow-smoke`
- review_curated `due_count=0`
- junie mirror OK
- targeted pytest passed

---

## 23. Open Questions and Evidence Gaps

| Item | Classification |
| --- | --- |
| Whether Devin always sets provenance env in practice | NOT_PROVEN |
| Full live MCP neo4j backend health | NOT_IN_SCOPE / platform-dependent |
| Historical plan doc path for promote-only note | removed; replaced with live source_refs |

---

## 24. Final Verdict

| Criterion | Result |
| --- | --- |
| Exactly 5 cycles with Stages 1–2–3 | **YES** |
| CYCLE-01 full baseline | **YES** |
| C02–C05 differential + regression | **YES** |
| GitHub tracking before remediation | **YES** (#7482–#7484 before edits) |
| Actionable findings remediable without debt growth | **YES** |
| Issues closed only after AC / not formal | **YES** (await PR merge) |
| Architecture boundaries preserved | **YES** |
| Debt budgets not increased | **YES** |
| Evidence-based final report | **YES** |

**Program status:** COMPLETE at local/working-branch level.  
**Merge gate:** PR #7487 → closes #7482 #7483 #7484.

---

## Agent Inventory (table)

| Agent/runtime | Config entry point | Runtime proven | Skills | MCP | Persistent memory | Session memory | Shared memory | Status |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- |
| Codex | `.codex/agents/CODEX-RUNTIME.md` | yes | yes | via project MCP config | `src/memory` | episodic | yes | active peer |
| Junie | `.junie/agents/JUNIE-RUNTIME.md` | yes | yes | via project MCP config | `src/memory` | episodic | yes | active peer |
| Devin | `.devin/` | yes (tracked) | yes | NOT_PROVEN default | `src/memory` | episodic | yes | active tracked |
| Gemini | `.gemini/settings.json` | config only | no tracked tree | NOT_PROVEN | `src/memory` | n/a | yes | machine-local |
| Copilot | `.github/copilot-instructions.md` | instructions | n/a | n/a | n/a | n/a | n/a | instructions |
| Cursor | `.cursor/` | partial | absent | NOT_PROVEN | n/a | n/a | n/a | candidate |

## Findings Register (table)

| Finding | Fingerprint | Severity | Lifecycle | First cycle | Last cycle | Issue | Remediation | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AI-MEM-C1-001 | smoke provenance | P1 | remediated_awaiting_merge | 01 | 05 | #7484 | inject/restore | smoke+tests |
| AI-MEM-C1-002 | junie CODEX-RUNTIME drift | P2 | remediated_awaiting_merge | 01 | 05 | #7483 | pointer | mirror check |
| AI-MEM-C1-003 | curated due reviews | P2 | remediated_awaiting_merge | 01 | 05 | #7482 | re-verify | due_count=0 |

## GitHub Register (table)

| Finding | Issue | Action | State | Commit/PR | Close reason |
| --- | --- | --- | --- | --- | --- |
| AI-MEM-C1-001 | #7484 | create+fix | open | PR #7487 | awaiting merge |
| AI-MEM-C1-002 | #7483 | create+fix | open | PR #7487 | awaiting merge |
| AI-MEM-C1-003 | #7482 | create+fix | open | PR #7487 | awaiting merge |

## Cycle Register (table)

| Cycle | Audit mode | New | Resolved | Regressed | Blocked | Issues created | Issues closed | Debt outcome | Verdict |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 01 | full | 3 | 3 (await merge) | 0 | 0 | 3 | 0 | unchanged | PASS |
| 02 | differential | 0 | 0 | 0 | 0 | 0 | 0 | unchanged | NO_ACTIONABLE_FINDINGS |
| 03 | differential | 0 | 0 | 0 | 0 | 0 | 0 | unchanged | NO_ACTIONABLE_FINDINGS |
| 04 | differential | 0 | 0 | 0 | 0 | 0 | 0 | unchanged | NO_ACTIONABLE_FINDINGS |
| 05 | differential | 0 | 0 | 0 | 0 | 0 | 0 | unchanged | NO_ACTIONABLE_FINDINGS |

---

*End of report.*
