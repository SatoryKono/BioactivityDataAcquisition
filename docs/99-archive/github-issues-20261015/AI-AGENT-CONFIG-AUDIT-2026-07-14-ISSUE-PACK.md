# AI Agent Configuration Audit 2026-07-14 Issue Pack

This pack reconciles the supplied static AI-agent configuration audit against
the tracked `main` branch and the current GitHub issue history. It publishes
only findings that remain reproducible and actionable.

## Reconciliation Summary

| Audit finding | Current `main` evidence | Disposition |
| --- | --- | --- |
| F-01: `.codex/agents/CODEX-RUNTIME.md` is missing | `.codex/agents/CODEX-RUNTIME.md` and the tracked `.codex/agents/*.md` profile set are present | Stale; do not create an issue |
| F-02: one MCP setup flow is documented | `scripts/ai/codex/setup_mcp.py` generates the tracked and local projections described by `README.md` | Confirmed design fact; no issue by itself |
| F-03: MCP server sets have drifted | `.mcp.json`, `scripts/ai/.mcp.json`, `.devin/config.json`, and generated editor/Codex projections all expose the same 17-server set; `README.md` lists that same set | Remediated by closed issues including #6026 and #6050; do not reopen |
| F-04: tracked MCP files contain workstation paths | `.mcp.json` and `scripts/ai/.mcp.json` are repo-relative; tracked `.devin/config.json` still contains `/mnt/e/g-drive/...` paths under an explicit policy exception | Partially current; create AI-RUNTIME-AUDIT-002 |
| F-05: Codex config conventions are mixed | The repo now distinguishes tracked behavior sources under `.codex/**`, local generated `.codex/settings.json`, and the Codex-native managed block in `~/.codex/config.toml` | Not reproduced as an unresolved defect; migration to another Codex agent format requires a separate owner decision and runtime evidence |
| F-06: Cursor/Copilot runtime files are not auditable | `.cursor/mcp.json` and `.vscode/mcp.json` remain intentionally local/generated, but their shape is owned by `setup_mcp.py` and covered by setup tests | Accepted generated-local design; no issue from absence alone |
| F-07: Devin skill parity is not CI-enforced | All 37 `SKILL.md` directories exist in both trees, but the current mirror checker only checks that two directories exist and always succeeds; `skills-consistency.yml` does not watch `.devin/skills/**` | Confirmed residual; create AI-RUNTIME-AUDIT-001 |
| F-08: Copilot contradicts Gemini runtime policy | Current `.github/copilot-instructions.md` matches `AGENTS.md`; #5798 and #5801 are closed as completed | Remediated; do not recreate |
| F-09: security controls are stronger than config drift controls | Directionally true, but it is context rather than an independently actionable defect | Address only through the two scoped issues below |
| F-10: `.devin/wiki.json` precedence is unclear | Root precedence and the closed `.devin/` governance decision #5767 keep project-wide sources above helper/navigation content; no conflicting runtime instruction was reproduced | Insufficient evidence for a new issue |

## Publish-Ready Set

1. [#6281](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6281) `AI-RUNTIME-AUDIT-001` — [Make AI skill mirror CI truthful and enforce sanctioned Codex-Devin parity](AI-RUNTIME-AUDIT-001-Make-AI-Skill-Mirror-CI-Truthful-And-Enforce-Devin-Parity.md)
2. [#6282](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6282) `AI-RUNTIME-AUDIT-002` — [Eliminate tracked workstation paths from the Devin MCP projection](AI-RUNTIME-AUDIT-002-Eliminate-Tracked-Devin-MCP-Workstation-Paths.md)

## Existing Issues Used For Deduplication

- #3423 — runtime-source-first precedence (closed/completed)
- #3427 — MCP local path strategy (closed/completed)
- #3526 — MCP runtime inventory classification (closed/completed)
- #5767 — `.devin/` governance decision (closed/completed)
- #5770 — `.devin/config.json` policy classification (closed/completed)
- #5798 — Gemini runtime source-of-truth conflict (closed/completed)
- #5801 — Cursor/Windsurf/Copilot governance references (closed/completed)
- #5802 — AI governance drift gate (closed/completed)
- #6017 — tracked-vs-local MCP policy alignment (closed/completed)
- #6026 — MCP setup/config convergence (closed/completed)
- #6050 — root `.mcp.json` retention and portability (closed/completed)
- #6113 and #6177 — generated skill mirror ownership/cleanup (closed/completed)

## Recommended Order

1. Implement AI-RUNTIME-AUDIT-001 first. It closes a false-green CI gap and
   establishes the parity contract needed to review future runtime-specific
   skill differences safely.
2. Implement AI-RUNTIME-AUDIT-002 after the Devin owner chooses a supported
   materialization strategy.

The two issues can be implemented independently, but both should preserve the
rule that technical-debt budgets may not increase.

## Assignee Recommendation

- Recommended assignee: `@SatoryKono`
- Confidence: high
- Evidence: default and affected-path ownership in `.github/CODEOWNERS`, plus
  recent commit ownership for `.codex/skills/**`, `.devin/**`, MCP setup, and
  `skills-consistency.yml`.
- Missing data: authenticated collaborator/workload data was unavailable, so no
  unsupported alternative assignees are proposed.

## Suggested Labels

| Issue | Labels |
| --- | --- |
| AI-RUNTIME-AUDIT-001 | `ai-runtime`, `governance`, `testing`, `technical-debt` |
| AI-RUNTIME-AUDIT-002 | `ai-runtime`, `governance`, `config`, `technical-debt` |

## Publication Status

Published on 2026-07-14 as GitHub issues #6281 and #6282. Do not run a second
publication pass from the local drafts.
