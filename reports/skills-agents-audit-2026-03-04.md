# Critical Audit: Skills & Agents Ecosystem

**Date:** 2026-03-04
**Scope:** `.claude/`, `.ai/memory/`, prompts, commands, skills, agents, rules
**Total AI config size:** 1.67 MB (`.claude/` 1.6 MB + `.ai/` 68 KB)

---

## Executive Summary

The BioETL project has accumulated **1.67 MB of AI orchestration configuration** across 70+ files in 6 directories. The system suffers from:

1. **Triple indirection** — commands → skills → actual logic (3 hops)
2. **Massive duplication** — standalone specs duplicate agent prompts (98K redundant)
3. **Legacy dead weight** — 7 SUBAGENT.md files (103K) are "read-only references" never used
4. **Skill/Agent role confusion** — same capability exists as both skill and agent
5. **Scattered context** — same information repeated across rules, memory, PROJECT_CONTEXT, agent prompts
6. **Orphan prompts** — 16 prompt files in `.claude/prompts/` with unclear status

**Estimated waste:** ~400 KB (55-60%) of content is redundant or obsolete.

---

## 1. Inventory Matrix

### 1.1 Directory Breakdown

| Directory | Files | Size | Purpose |
|-----------|-------|------|---------|
| `.claude/agents/` | 21 | 375K | Agent specs + legacy subagents |
| `.claude/skills/` | 30 | 229K | Skill definitions + templates |
| `.claude/commands/` | 17 | 9.5K | Stub redirects to skills |
| `.claude/rules/` | 2 | 30K | Auto-loaded rules |
| `.claude/prompts/` | 16 | 147K | Manual prompt templates |
| `.ai/memory/` | 8 | 67K | Agent memory files |
| **Total** | **94** | **857K** | |

### 1.2 Agent Inventory (14 files, 375K)

| Agent | Size | Registered subagent_type? | Standalone copy? |
|-------|------|--------------------------|-------------------|
| ORCHESTRATION.md | 27K | — (master spec) | No |
| py-audit-bot.md | 15K | Yes | Legacy (16K) |
| py-plan-bot.md | 11K | Yes | Legacy (12K) |
| py-test-bot.md | 9.8K | Yes | Legacy (14K) |
| py-code-bot.md | 14K | **No** (direct use) | Legacy (19K) |
| py-config-bot.md | 13K | Yes | Legacy (17K) |
| py-debug-bot.md | 11K | Yes | Legacy (11K) |
| py-doc-bot.md | 5.1K | Yes | Legacy (14K) |
| py-diagram-bot.md | 3.5K | **No** (not in rules) | No |
| py-doc-swarm.md | 5.3K | Yes | **56K standalone** |
| py-test-swarm.md | 27K | Yes | **42K standalone** |
| py-review-orchestrator.md | 32K | Yes | No |

### 1.3 Skill Inventory (30 files, 229K)

**BioETL-specific skills (15):**
architecture-guardian, verify-architecture, config-validate, ci-diagnose,
dependency-audit, new-pipeline, new-composite, test-swarm, review-orchestrator,
vcr-record, mermaid-design, schema-parity, provider-health, migration,
release-checklist

**Generic/reusable skills (12):**
capability-discovery, collecting-evidence, deep-research, generating-constrained-specs,
initializing-ledger, making-decisions, nci-analysis, repo-config, suggest-users,
synthesizing-pillars, create-pr, documentation-audit

**Templates/support (3):**
documentation-audit.audit-checklist.md, documentation-audit.report-template.md,
documentation-cascade-audit.skill.md (50K — largest single file)

---

## 2. Critical Findings

### FINDING-01: Triple Indirection Pattern (CRITICAL)

**Problem:** Every `/command` is a 5-line stub that says "read skill X and execute".

```
User: /architecture-guardian full
  → .claude/commands/architecture-guardian.md (399 bytes)
    → "Прочитай .claude/skills/architecture-guardian.skill.md"
      → Actual skill logic (6K)
```

**Impact:** 17 command files × ~350 bytes = 6K of pure boilerplate.
The commands/ layer adds zero value — it's a redirect table.

**Verdict:** Commands should either contain the logic directly or be eliminated.

---

### FINDING-02: Standalone Spec Duplication (CRITICAL)

| Agent prompt | Standalone spec | Overlap |
|-------------|----------------|---------|
| py-test-swarm.md (27K) | py-test-swarm-standalone.md (42K) | ~80% |
| py-doc-swarm.md (5.3K) | py-doc-swarm-standalone.md (56K) | ~70% |

**Total waste:** ~98K of near-duplicate content.

**Problem:** The standalone specs were created for "complete context" but the agent prompts already contain the necessary information. Two sources of truth that inevitably diverge.

---

### FINDING-03: Legacy SUBAGENT.md Files (HIGH)

7 files in `.claude/agents/subagents/` totaling **103K**:

| Legacy File | Size | Current Agent |
|-------------|------|---------------|
| pyAuditBot/SUBAGENT.md | 16K | py-audit-bot.md (15K) |
| pyCodeBot/SUBAGENT.md | 19K | py-code-bot.md (14K) |
| pyConfigBot/SUBAGENT.md | 17K | py-config-bot.md (13K) |
| pyDebugBot/SUBAGENT.md | 11K | py-debug-bot.md (11K) |
| pyDocBot/SUBAGENT.md | 14K | py-doc-bot.md (5.1K) |
| pyPlanBot/SUBAGENT.md | 12K | py-plan-bot.md (11K) |
| pyTestBot/SUBAGENT.md | 14K | py-test-bot.md (9.8K) |

**Status:** Marked as "v1.2 legacy reference, read-only". No agent or skill references them.
**Verdict:** Dead code. Delete.

---

### FINDING-04: Skill ↔ Agent Role Confusion (HIGH)

Several capabilities exist as BOTH a skill AND an agent:

| Capability | Skill | Agent | Who runs it? |
|-----------|-------|-------|-------------|
| Test orchestration | test-swarm.md (6.3K) | py-test-swarm.md (27K) | Unclear |
| Code review | review-orchestrator.md (3K) | py-review-orchestrator.md (32K) | Unclear |
| Documentation audit | documentation-audit.skill.md (2.9K) + cascade (50K) | py-doc-swarm.md (5.3K) + standalone (56K) | Unclear |
| Architecture check | architecture-guardian.skill.md (6K) + verify-architecture.md (8.9K) | py-audit-bot.md (15K) | Partially clear |

**Problem:** A user doesn't know whether to run `/test-swarm` (skill) or invoke `py-test-swarm` (agent). The skill reads a spec, the agent has its own prompt — they may diverge.

---

### FINDING-05: Context Fragmentation (MEDIUM)

The same architectural rules are repeated in:

1. `.claude/rules/ai-selfreview-rules.md` (23K) — auto-loaded
2. `.ai/memory/agent-memory.md` (18K) — referenced by agents
3. `.ai/memory/memory-py-audit-bot.md` (7.5K) — agent-specific
4. `.claude/agents/py-audit-bot.md` (15K) — inlined in agent prompt
5. `.claude/skills/architecture-guardian.skill.md` (6K) — skill version
6. `docs/00-project/RULES.md` — canonical source

**Example:** The import matrix (ARCH-001) appears in at least 4 locations.
When it changes, all 4 must be updated manually.

---

### FINDING-06: Orphan Prompts Directory (MEDIUM)

`.claude/prompts/` contains 16 files (147K) from an earlier workflow:

- `00-Audit/` — 3 audit prompts
- `00-Documentation/` — 3 doc prompts
- `02-Sync/` — 7 sync prompts
- 2 standalone prompts + README

**Problem:** These are not referenced by any command, skill, or agent. They appear to predate the skills system. No mechanism invokes them automatically.

---

### FINDING-07: Oversized Skill Files (MEDIUM)

| File | Size | Issue |
|------|------|-------|
| documentation-cascade-audit.skill.md | **50K** | Larger than most agent prompts combined |
| mermaid-design.md | **14K** | Contains 10 LBP rules inline |
| nci-analysis/SKILL.md | **14K** | 20-category analysis framework |
| vcr-record.md | **9.6K** | Full VCR lifecycle documentation |
| deep-research/SKILL.md | **9.5K** | Multi-cycle research protocol |

Skills should be concise instructions. A 50K skill file is an entire specification document masquerading as a skill.

---

### FINDING-08: py-diagram-bot Unregistered (LOW)

`py-diagram-bot.md` exists in agents/ but is not listed in:
- `agent-orchestration-rules.md` (subagent table)
- `ORCHESTRATION.md` (interaction matrix)

It's a phantom agent — defined but not integrated.

---

## 3. Overlap Map

```
┌─────────────────────────────────────────────────────────┐
│                    ARCHITECTURE                          │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐ │
│  │ architecture- │  │  verify-      │  │ py-audit-bot │ │
│  │ guardian.skill│  │  architecture │  │   (agent)    │ │
│  │  (6K skill)  │  │   (9K skill)  │  │   (15K)      │ │
│  └──────┬───────┘  └───────┬───────┘  └──────┬───────┘ │
│         └──────────┬───────┘                  │         │
│              OVERLAP: boundary checks         │         │
│              + DI + naming                    │         │
│                    └──────────────────────────┘         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    TESTING                                │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐ │
│  │  test-swarm  │  │ py-test-swarm │  │ py-test-swarm│ │
│  │  (6K skill)  │  │  (27K agent)  │  │ -standalone  │ │
│  │              │  │               │  │  (42K spec)  │ │
│  └──────┬───────┘  └───────┬───────┘  └──────┬───────┘ │
│         └──────────┬───────┘                  │         │
│              OVERLAP: L1→L2→L3 hierarchy      │         │
│              + modes + scaling                │         │
│                    └──────────────────────────┘         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  DOCUMENTATION                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ doc-audit    │  │ doc-cascade  │  │ py-doc-swarm │  │
│  │ (3K skill)   │  │ (50K skill!) │  │  (5K agent)  │  │
│  ├──────────────┤  └──────┬───────┘  ├──────────────┤  │
│  │ + checklist  │         │          │ + standalone  │  │
│  │ + template   │         │          │   (56K spec)  │  │
│  └──────┬───────┘         │          └──────┬───────┘  │
│         └─────────┬───────┘                 │          │
│             OVERLAP: audit modes,           │          │
│             hierarchy, reporting            │          │
│                   └─────────────────────────┘          │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Consolidation Plan

### Phase 1: Delete Dead Weight (saves ~250K)

| Action | Files | Savings |
|--------|-------|---------|
| **DELETE** legacy subagents/ | 7 SUBAGENT.md files | 103K |
| **DELETE** standalone agent specs | py-test-swarm-standalone.md, py-doc-swarm-standalone.md | 98K |
| **DELETE** orphan prompts/ | 16 files in .claude/prompts/ | 147K |
| **Subtotal** | 25 files | **~348K** |

**Risk:** Low. Legacy files are unused. Standalone specs duplicate agent prompts. Prompts are unreferenced.

### Phase 2: Merge Commands into Skills (saves ~6K, eliminates indirection)

**Current:** 17 command stubs → 17 skill files (triple indirection)

**Proposed:** Move skill content directly into `.claude/commands/` as the canonical location. Delete the separate `.claude/skills/` files for BioETL-specific skills.

| Before | After |
|--------|-------|
| `/cmd` → commands/cmd.md (stub) → skills/cmd.md (logic) | `/cmd` → commands/cmd.md (logic) |

**Keep `.claude/skills/` only for:** generic reusable skills (deep-research, nci-analysis, etc.) that are not BioETL-specific.

### Phase 3: Resolve Skill ↔ Agent Overlaps

| Capability | Keep As | Eliminate |
|-----------|---------|-----------|
| Architecture validation | **Agent** (py-audit-bot) + **1 command** (verify-architecture) | architecture-guardian.skill.md (merge into verify-architecture) |
| Test orchestration | **Agent** (py-test-swarm) + **1 command** (test-swarm as thin trigger) | test-swarm.md skill body (move to agent) |
| Code review | **Agent** (py-review-orchestrator) + **1 command** | review-orchestrator.md skill body |
| Documentation audit | **Agent** (py-doc-swarm) + **1 command** | documentation-cascade-audit.skill.md (50K!) + documentation-audit templates |

**Principle:** Agent = full spec with orchestration logic. Command = thin trigger that invokes agent with args.

### Phase 4: Deduplicate Context (saves ~40K)

**Current:** Import matrix, naming rules, DI rules repeated in 4-6 places.

**Proposed:**
1. **Single source of truth:** `docs/00-project/RULES.md`
2. **Rules files** (`.claude/rules/`): Keep compact, reference RULES.md sections by `§` number
3. **Agent memory files:** Remove duplicated rules, keep only agent-specific heuristics
4. **Agent prompts:** Reference rules by ID (e.g., "enforce ARCH-001..008"), don't inline them

### Phase 5: Rationalize Agent Count

| Current Agent | Recommendation |
|---------------|---------------|
| py-audit-bot | **Keep** — distinct gating role |
| py-plan-bot | **Keep** — central coordinator |
| py-test-bot | **Keep** — baseline/final executor |
| py-code-bot | **Absorb** — not a registered subagent_type, just direct coding guidelines → move to rules |
| py-config-bot | **Keep** — distinct zone (configs/) |
| py-debug-bot | **Keep** — distinct RCA methodology |
| py-doc-bot | **Merge into py-doc-swarm** — swarm subsumes simple doc work |
| py-diagram-bot | **Merge into py-doc-swarm** — diagram rendering is doc work |
| py-doc-swarm | **Keep** (absorbs py-doc-bot + py-diagram-bot) |
| py-test-swarm | **Merge with py-test-bot** — swarm is just test-bot at scale |
| py-review-orchestrator | **Keep** — distinct review workflow |

**Result:** 14 agents → **8 agents** (audit, plan, test, config, debug, doc-swarm, review-orchestrator + ORCHESTRATION.md)

### Phase 6: Slim Down Oversized Files

| File | Current | Target | Method |
|------|---------|--------|--------|
| documentation-cascade-audit.skill.md | 50K | 5K | Extract templates, reference agent prompt |
| py-review-orchestrator.md | 32K | 15K | Extract S1-S8 checklists to reference doc |
| py-test-swarm.md | 27K | 12K | Remove duplicated rules, reference RULES.md |
| mermaid-design.md | 14K | 6K | Extract LBP rules to docs/02-architecture/ |

---

## 5. Target State

### Directory Structure After Consolidation

```
.claude/
├── agents/                    # 8 files, ~120K (was 375K)
│   ├── ORCHESTRATION.md       # Master spec (slimmed)
│   ├── py-audit-bot.md
│   ├── py-plan-bot.md
│   ├── py-test-bot.md         # Absorbs test-swarm capability
│   ├── py-config-bot.md
│   ├── py-debug-bot.md
│   ├── py-doc-swarm.md        # Absorbs doc-bot + diagram-bot
│   └── py-review-orchestrator.md
├── commands/                  # 17 files, ~80K (commands now contain logic)
│   ├── architecture-guardian.md  # Self-contained
│   ├── verify-architecture.md
│   ├── test-swarm.md          # Thin trigger → py-test-bot
│   └── ... (14 more)
├── rules/                     # 2 files, ~15K (slimmed, reference §IDs)
│   ├── agent-orchestration-rules.md
│   └── ai-selfreview-rules.md
├── skills/                    # 12 files, ~70K (generic skills only)
│   ├── capability-discovery/
│   ├── collecting-evidence/
│   ├── deep-research/
│   ├── nci-analysis/
│   └── ... (8 more generic skills)
└── PROJECT_CONTEXT.md

.ai/memory/                    # 8 files, ~35K (deduplicated)
    ├── agent-memory.md         # Slim: project overview + refs only
    └── memory-py-*.md          # Agent-specific heuristics only
```

### Metrics

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Total files | 94 | ~47 | **-50%** |
| Total size | 857K | ~320K | **-63%** |
| Agents | 14 | 8 | **-43%** |
| Indirection hops (command → logic) | 3 | 1 | **-67%** |
| Duplicate content | ~400K | ~0 | **-100%** |

---

## 6. Implementation Priority

| Priority | Phase | Effort | Impact | Risk |
|----------|-------|--------|--------|------|
| **P0** | Phase 1: Delete dead weight | 1h | High (348K freed) | Very Low |
| **P1** | Phase 3: Resolve skill↔agent overlaps | 4h | High (clarity) | Medium |
| **P2** | Phase 5: Rationalize agent count | 3h | High (simplicity) | Medium |
| **P3** | Phase 2: Merge commands into skills | 2h | Medium (UX) | Low |
| **P4** | Phase 4: Deduplicate context | 3h | Medium (maintainability) | Low |
| **P5** | Phase 6: Slim oversized files | 2h | Low (size) | Low |

---

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Agent merge breaks orchestration | HIGH | Update ORCHESTRATION.md interaction matrix first |
| Skill deletion breaks `/command` | MEDIUM | Verify each command's target exists before deleting |
| Context dedup loses important details | LOW | Diff before/after for each agent memory file |
| Legacy subagent deletion loses history | LOW | Git history preserves everything |

---

*Generated by critical audit. Next step: prioritize and execute phases.*
