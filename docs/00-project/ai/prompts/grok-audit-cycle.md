# Grok Audit Cycle Prompt (short)

*Status: internal working prompt | Class: operator aid | Not governance SSOT*

Default **one** full cycle per session. Raise to 2 only if explicitly requested.
Do not run empty cycles "for form".

## Paste template

```text
# BioETL audit cycle

## Params
- REPO: SatoryKono/BioactivityDataAcquisition
- BASE: main
- WORK_BRANCH: fix/<audit-slug> (never main)
- SCOPE: <surface list or theme>
- MODE: audit
- CYCLE_COUNT: 1
- AUDIT_MODE: full | differential
- REQUIRE_GH_TRACKING: true
- LANGUAGE: ru (code/ids/paths original)

## Read (do not restate)
1. AGENTS.md (precedence, mirrors, env ban, debt budgets)
2. docs/00-project/NORMATIVE_SOURCES.md
3. Relevant accepted ADRs only as needed
4. MEMORY_USAGE.md if memory/AI surfaces in SCOPE

## Stage 1 — Findings
- Inventory only paths that exist in this checkout
- Each finding: severity, path, symbol, claim, evidence (test/command/snippet)
- No finding without file-level proof; mark NOT_PROVEN otherwise

## Stage 2 — GitHub tracking
- Search open issues before create
- Create/reopen/link one issue per root cause (or path-cluster)
- No duplicate issues

## Stage 3 — Remediation
- Fix available findings; do not close blocked items
- Tests/checks listed; no tech-debt budget growth
- PR for product/docs deltas

## Cycle closeout
- Table: finding | issue | state | commit/PR | verification
- Run the offline Proof-or-Stop verifier; only ADMIT qualifies a lifecycle transition
- Use .venv-win on Windows and .venv in WSL/Linux; vendor evidence cannot override core
- If NO_ACTIONABLE_FINDINGS: stop (do not invent work for remaining cycles)

## Git safety
Same as grok-closeout.md
```

## Anti-patterns (do not paste)

- Nine simultaneous "Principal *" roles
- Full RULES/ADR dump in the prompt
- CYCLE_COUNT=5 with mandatory empty cycles
- 24-section mandatory report outline every time
