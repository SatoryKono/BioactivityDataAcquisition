# Agents / runtime instructions audit

| Field | Value |
| --- | --- |
| domain_id | `agents-runtime` |
| prompt_id | `prompt.audit.agents-runtime` v1.2.0 |
| MODE | `audit` |
| AUDIT_MODE | `full` |
| LANGUAGE | `ru` |
| REQUIRE_GH_TRACKING | `false` |
| SCOPE | `AGENTS.md` `.codex/` `.junie/` `.devin/` `docs/00-project/ai/` |
| generated_at | 2026-08-26 |
| surface_score | **2** / 3 (core mechanism correct; local non-critical gaps) |
| debt_outcome | `unchanged` (бюджеты не трогались) |
| blocked | `false` |

## Executive summary

Канонический runtime-контур BioETL **собран и в основном согласован**:

- `AGENTS.md` задаёт equal-peer precedence (`.codex/**` ≡ `.junie/**`, `.devin/**` для Devin, `.gemini/**` только если дерево реально есть).
- `.junie/guidelines.md` lock-step с `AGENTS.md` по env/debt/guardrails; dashboard-пути Junie-native — допустимое runtime-specific расхождение.
- Шесть `py-*` профилей есть в Codex, Junie и Devin. `py-code-bot` — documented exclusion.
- CI `.github/workflows/skills-consistency.yml` гоняет `check_junie_mirror.sh --check` и Codex–Devin/docs skills-mirror.
- Env-guardrail и запрет роста tech-debt бюджетов повторены в runtime maps, Copilot, GEMINI.md, Devin config (`Write(**/.env*)` deny).
- `.codex/config.toml` портабелен (нет auth/MCP/абсолютных путей). `.devin/mcp_config.json` использует `${env:VAR}`, не секреты.
- Prompts library явно **не** SSOT (`docs/00-project/ai/prompts/README.md`).
- `.claude/**` и tracked `.gemini/agents|skills` корректно помечены unavailable. `.junie/agents/CODEX-RUNTIME.md` — navigation stub, не fork.

Материальные gaps — **не P0**: усечённый precedence в always-on Cursor/Windsurf правилах, stale RULES v6.1.5 в Claude/Windsurf/coverage matrix, inversion «canonical script» под `docs/00-project/ai/agents/scripts/`, docs-only `sp-*` с Write/sonnet, Devin maps читают RULES раньше `AGENTS.md`, post-change policy не покрывает `.devin/**`, Windows-рецепт junie-check не документирован.

P0 (secret leak / destroy-without-guard / RCE): **не найдено**. `curl|bash` в agent scripts нет. Live SHA-256 parity **не прогонялась** в этой сессии (`AUD-015` NOT_PROVEN).

## Surface score

| Score | Meaning (kit) | Why 2 |
| --- | --- | --- |
| 3 | consistent + automated | CI parity jobs exist, but IDE/Devin/docs mirrors still contradict AGENTS.md |
| **2** | main workflow reliable; undocumented preconditions | Windows bash-only junie check; Cursor/Windsurf/Devin precedence drift; docs-owned debt script |
| 1 | material gaps / weak enforcement | Core Codex/Junie CI gate is present — not this band |
| 0 | leak/destroy/uncontrolled privilege | No proven P0 |

Mapping: qualitative kit scale (not 0–5 dimension average).

## Instruction scope graph

```text
AGENTS.md  (root contract)
 ├─ .junie/guidelines.md          equal-peer root (Junie)
 ├─ .codex/agents/CODEX-RUNTIME.md
 │    └─ .codex/agents/py-*.md + .toml  → .codex/skills/** → memory-py-*.md
 ├─ .junie/agents/JUNIE-RUNTIME.md
 │    └─ .junie/agents/py-*.md (SHA parity vs Codex) → .junie/skills/**
 ├─ .devin/agents/DEVIN-RUNTIME.md
 │    └─ .devin/agents/*/AGENT.md → .devin/skills/** (+ optional coderabbit-audit)
 ├─ docs/00-project/NORMATIVE_SOURCES.md → RULES.md → REQUIREMENTS.md → ADRs
 ├─ docs/00-project/ai/**          mirrors / prompts / cursor rules (not behavior SSOT
 │                                 except cursor/ which IS Cursor guidance SSOT)
 └─ scripts/ai/junie|codex|sync    parity + doctor + windsurf/cursor sync
        └─ CI: skills-consistency.yml
```

Optional discovery (present): `.github/copilot-instructions.md`, `.github/instructions/**`, root `GEMINI.md`. `CLAUDE.md` at repo root — нет; stub в `docs/00-project/ai/agents/CLAUDE.md`. `.agents/` directory — нет (gitignore un-ignore `!.agents/skills/*/SKILL.md` остаётся контрактом). `.gemini/settings.json` — gitignored local-only.

## What is healthy

| Surface | Evidence |
| --- | --- |
| Precedence SSOT | `AGENTS.md` L6–26; `NORMATIVE_SOURCES.md` L39–52 points back, does not fork a numbered list |
| Junie lock-step | `.junie/guidelines.md` L9–34 + env/debt/guardrails match AGENTS |
| Profile set | Codex/Junie: 6 `py-*.md`; Devin: 6 `*/AGENT.md`; contract excludes `py-code-bot` |
| Skill catalogs | `.codex/skills/SKILLS-CATALOG.md` prefix identical to `.devin/skills/` and `docs/00-project/ai/skills/local/` (spot-read) |
| Env deny | `.devin/config.json` deny `Write(**/.env*)`; AGENTS.md Env File Guardrail |
| Debt ban | Runtime maps + Copilot + GEMINI.md + Devin ORCHESTRATION §1.0 |
| Portable Codex config | `.codex/config.toml` only `agents.max_threads = 3` |
| MCP tokens | `.devin/mcp_config.json` `${env:DEEPWIKI_API_KEY}` etc.; `export_mcp_env_from_dotenv.ps1` prints name+len only |
| CI | `skills-consistency.yml` jobs `verify-codex-junie-runtime-parity`, `verify-local-skills-mirror`, `verify-native-codex-runtime` |
| Gemini/Claude claims | AGENTS.md L113–121; GEMINI.md L26–29, L56–58; no tracked `.gemini/agents` |

## Findings (16; 15 PROVEN + 1 NOT_PROVEN)

| ID | Pri | Status | Path | One-line |
| --- | --- | --- | --- | --- |
| AUD-001 | P2 | PROVEN | `docs/00-project/ai/rules/cursor/05-agent-workflow.mdc:12` | Always-on Cursor/Windsurf precedence = Codex then RULES; Junie/Devin/NORMATIVE_SOURCES omitted |
| AUD-002 | P2 | PROVEN | `docs/00-project/ai/rules/windsurf/rules/00-bioetl-core-governance.md:8` | Windsurf core rule stale vs Cursor: RULES v6.1.5, ADR-050, priority starts at RULES |
| AUD-003 | P2 | PROVEN | `docs/00-project/ai/agents/guides/CLAUDE.md:9` | Claude stub/guide + RULES_COVERAGE_MATRIX still pin RULES v6.1.5; live RULES is 6.1.11 |
| AUD-004 | P2 | PROVEN | `docs/00-project/ai/agents/scripts/architecture-techdebt-automation.py` | Debt-exemptions and config-gap “canonical scripts” live under docs AI tree |
| AUD-005 | P2 | PROVEN | `docs/00-project/ai/agents/agents/sp-test-automator.md:21` | docs-only sp-* still Write/sonnet, coverage >80%, escalate to missing `sp-workflow-orchestrator` |
| AUD-006 | P2 | PROVEN | `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md:27` | Applies To omits `.devin/**` |
| AUD-007 | P2 | PROVEN | `.devin/agents/DEVIN-RUNTIME.md:7` | Devin Canonical Sources lists docs/RULES before AGENTS.md |
| AUD-008 | P2 | PROVEN | `AGENTS.md:86` | Junie parity MUST is bash-only; Windows `.venv-win` python path undocumented |
| AUD-009 | P3 | PROVEN | `docs/00-project/ai/rules/cursor/00-bioetl-core-governance.mdc:37` | Cites nonexistent AGENTS.md import matrix |
| AUD-010 | P3 | PROVEN | `.codex/agents/CODEX-RUNTIME.md:55` | Broken “python -m is not used here” sentence |
| AUD-011 | P3 | PROVEN | `docs/00-project/ai/agents/scripts/py-config-bot-1.py:12` | Default output `docs/audits/` (not `reports/`) |
| AUD-012 | P3 | PROVEN | `.devin/config.json:17` | Unbounded `Exec(git)` at project allow-list |
| AUD-013 | P3 | PROVEN | `AGENTS.md:136` | Dashboard routing only `.codex/skills/` (Junie guidelines use `.junie/skills/`) |
| AUD-014 | P3 | PROVEN | `.devin/skills/coderabbit-audit/SKILL.md:294` | Audit skill runs `gh issue create` and `git tag` without dry-run |
| AUD-015 | P3 | NOT_PROVEN | `scripts/ai/junie/check_junie_mirror.sh` | Live SHA parity not executed this session |
| AUD-016 | P3 | PROVEN | `docs/00-project/ai/agents/policy/SPECIALIST_PROFILE_TEMPLATE.md:17` | Template still `model: sonnet` + Write tools |

P0/P1 count: **0**. Proven: **15**.

## Top remediations

1. Выровнять always-on Cursor `05-agent-workflow.mdc` с `AGENTS.md` (Junie/Devin/NORMATIVE_SOURCES), затем `python -m scripts.ai.sync.windsurf`.
2. Прогнать Windsurf sync и убрать hardcoded `RULES v6.1.5` / `ADR-001…ADR-050` из `00-bioetl-core-governance.md`.
3. Снять version banners в `CLAUDE.md` (stub+guide) и `RULES_COVERAGE_MATRIX.md`; читать header `Version:`.
4. Перенести implementations `architecture-techdebt-automation.py` / `py-config-bot-1.py` в `scripts/**`; docs оставить wrappers.
5. Починить Devin Canonical Sources order + добавить `.devin/**` в `POST_CHANGE_VALIDATION.md` и skills-mirror check.
6. Документировать Windows-вызов `python scripts/ai/junie/check_junie_mirror.py --check`.
7. Нейтрализовать docs-only `sp-*` (no Write/sonnet/missing orchestrator) и шаблон.
8. Прогнать live `--check` junie + skills-mirror на этом checkout (закрыть AUD-015).

## Command matrix (canonical)

| Need | Command | Notes |
| --- | --- | --- |
| Codex–Junie parity | `bash scripts/ai/junie/check_junie_mirror.sh --check` | Python twin: `python scripts/ai/junie/check_junie_mirror.py --check` (undocumented in AGENTS.md) |
| Codex–Devin + docs skills | `bash scripts/ops/support/skills/check_skills_mirror.sh --check` | |
| Codex native doctor | `python scripts/ai/codex/doctor.py static --no-write` | Windows: `.\\.venv-win\\Scripts\\python.exe ...` |
| Docs runtime-mirror drift | `python -m scripts.docs check-drift --runtime-mirrors --freshness` | |
| Windsurf regen | `python -m scripts.ai.sync.windsurf` | From cursor/*.mdc |
| Memory pre-task | `python -m memory.tooling.workflow pre-task --profile audit ...` | Skipped this session |
| Operator bootstrap | `make install` / `make test-deps` / `make setup-plugins` | AGENT.md / CLAUDE.md |
| Risk-tier tests | V1–V4 in CODEX-RUNTIME / JUNIE-RUNTIME | Not a single `make test` for every task |

## Scripts / permissions (summary)

- `scripts/ai/junie/check_junie_mirror.sh`: `--check` read-only exit 1 on drift; `--sync` one-way Codex→Junie, never writes Codex. No extra dry-run (check is the preview).
- `scripts/ai/mcp/export_mcp_env_from_dotenv.ps1`: prints key name + length, not values.
- `docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-*.sh`: thin exec wrappers to `scripts/diagrams/`.
- Codex `py-audit-bot.toml`: `sandbox_mode = "read-only"`.
- Devin `py-test-bot` AGENT.md denies write/edit (orchestrator owns test file edits) — documented platform difference vs Codex/Junie workspace-write.
- No `curl|bash`, no `eval`, no `rm -rf` under `scripts/ai/**` in this scan.

## Skipped checks

| Check | Reason |
| --- | --- |
| `bash scripts/ai/junie/check_junie_mirror.sh --check` | no shell in this auditor runtime |
| `bash scripts/ops/support/skills/check_skills_mirror.sh --check` | same |
| `python scripts/ai/codex/doctor.py static --no-write` | same |
| `python -m scripts.docs check-drift --runtime-mirrors --freshness` | same |
| `python -m memory.tooling.workflow pre-task --profile audit` | same; memory sheets read directly |
| GitHub issue tracking | `REQUIRE_GH_TRACKING=false` |

## Mirror-sync status

This audit is **read-only**. Runtime trees were not edited. Live `--check` exit codes: **skipped** (AUD-015). CI contract for both Junie and Devin/docs mirrors is present on `main` workflow file.

## Kit extras

- `reports/audit/agents/agent-instruction-map.md`
- `reports/audit/agents/agent-scripts.csv`
- `reports/audit/agents/tool-permissions.csv`
- `reports/audit/agents/instruction-conflicts.csv`
- `reports/audit/agents/command-matrix.md`
- `reports/audit/agents/findings.json`

## Guardrails honored

- Product code not edited.
- Tech-debt budgets not increased.
- `.env` not created/edited/moved.
- No secrets in this report.
- Artifacts only under `reports/audit/agents/`.
