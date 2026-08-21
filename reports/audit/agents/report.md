# Аудит agents-runtime

| Поле | Значение |
| --- | --- |
| domain_id | `agents-runtime` |
| prompt_id | `prompt.audit.agents-runtime` |
| MODE / AUDIT_MODE | `audit` / `full` |
| LANGUAGE | `ru` |
| BASE | `main` |
| REPO | `SatoryKono/BioactivityDataAcquisition` |
| SCOPE | `AGENTS.md` `.codex/` `.junie/` `.devin/` `docs/00-project/ai/` `scripts/ai/` |
| surface_score | **2** (acceptable: ядро runtime согласовано и закрыто CI; локальный drift в Gemini/Devin skills/docs mirrors) |
| generated_at | 2026-08-21 |
| P0/P1 | 1 (P1) |
| PROVEN findings | 10 |
| Patches applied | нет (MODE=full, operator approval не дан) |

## Executive summary

Канонический AI runtime BioETL живой и в целом зрелый: equal-peer `.codex/**` ↔ `.junie/**` с контрактом и CI job `verify-codex-junie-runtime-parity`; Devin имеет собственные `DEVIN-RUNTIME.md` + 6 `AGENT.md`; Copilot path-scoped instructions согласованы с RULES; MCP wrappers не печатают значения токенов; `curl|bash` / `git reset --hard` в `scripts/ai` не найдены; `.env` create paths требуют `BIOETL_CREATE_LOCAL_ENV_FILES=1`.

Материальные разрывы — не в Codex/Junie maps, а в **боковых instruction surfaces**: корневой `GEMINI.md` всё ещё зовёт retired роли и несуществующие `make ai-*`; шесть Devin `SKILL.md` ставят Codex ORCHESTRATION `(v4.3)` как Team orchestration (P1 относительно AGENTS.md Devin guardrail); Devin `py-test-bot` выдумывает 90% domain gate; docs mirrors `docs/00-project/ai/README.md` и agent catalogs отстают от Junie equal-peer.

P0 (secret leak / uncontrolled destroy) **не доказан**. `docker rm -f` в MCP prune ограничен exited+image-match и исключает `bioetl-*`, но dry-run отсутствует (P2).

## Surface score

| Score | Meaning (domain card) | Этот прогон |
| ---: | --- | --- |
| 3 | Instructions consistent; scripts reproducible; tools limited; validation automated | нет: Gemini/Devin skill/docs drift |
| **2** | Main workflow reliable; a few undocumented preconditions | **выбрано** |
| 1 | Implicit env assumptions, excessive permissions, or conflicting instructions | нет: конфликты локальные, не ломают Codex/Junie CI |
| 0 | Agent can leak a secret, destroy data, or run uncontrolled privileged action | нет |

Mapping: kit 0–3 control maturity. Не ставился 3 из‑за P1 Devin skill SSOT и stale GEMINI.md.

## Instruction scope graph

```
AGENTS.md  (repo-wide contract)
 ├─ .junie/guidelines.md          equal-peer root (lock-step claimed)
 ├─ .codex/agents/CODEX-RUNTIME.md
 │   ├─ .codex/agents/py-*.md + py-*.toml
 │   └─ .codex/skills/**          skill SSOT for Codex
 ├─ .junie/agents/JUNIE-RUNTIME.md
 │   ├─ .junie/agents/py-*.md     parity vs Codex (contract)
 │   └─ .junie/skills/**          byte-identical vs .codex/skills
 ├─ .devin/agents/DEVIN-RUNTIME.md
 │   ├─ .devin/agents/*/AGENT.md
 │   └─ .devin/skills/**          allowed SKILL.md variants
 ├─ docs/00-project/NORMATIVE_SOURCES.md → RULES / REQUIREMENTS / ADR
 └─ docs/00-project/ai/**         mirrors/guides/prompts — NOT behavior SSOT
      ├─ prompts/library          operator paste only
      ├─ agents/guides            CLAUDE/GEMINI/AGENT/CODEX
      └─ skills/local             docs mirror of .codex/skills

Optional: GEMINI.md (root allowlist), .github/copilot-instructions.md,
.github/instructions/*.instructions.md. Tracked `.gemini/agents|skills` нет.
`.claude/**` объявлен unavailable. `.agents/` пустой (CI path trigger).
```

Противоречия (см. findings / `instruction-conflicts.csv`): GEMINI.md vs Makefile+forbidden identifiers; Devin SKILL.md vs AGENTS.md Devin ownership; docs/ai README vs equal-peer; AGENT.md `git add .`; Devin 90% domain vs RULES ≥85%.

## Inventory (owners)

| Surface | Owner | Role | Notes |
| --- | --- | --- | --- |
| `AGENTS.md` | runtime contract | SSOT precedence | 6 py-* + env/debt/mirror guards |
| `.codex/agents` | Codex runtime | 6 md + 6 toml + CODEX-RUNTIME/ORCHESTRATION/README | toml = Codex-only |
| `.codex/skills` | Codex skills | 13 skill dirs + catalog | includes observability-* |
| `.junie/guidelines.md` | Junie root | equal peer to AGENTS.md | dashboard skills point to `.junie/skills` |
| `.junie/agents` | Junie runtime | JUNIE-RUNTIME + py-* + CODEX-RUNTIME **stub** | stub documented, not SSOT |
| `.junie/skills` | Junie skills | same dir set as Codex | contract sha256 |
| `.devin/agents` | Devin runtime | DEVIN-RUNTIME + 6 AGENT.md | py-test-bot deny write (intentional) |
| `.devin/skills` | Devin skills | + coderabbit-audit extra (contract optional) | SKILL.md variants allowed |
| `docs/00-project/ai/**` | mirrors | not behavior SSOT | stale README/catalogs |
| `scripts/ai/**` | tooling | check/sync/launch/MCP | doctor, junie mirror, skill mirror, wrappers |
| `.github/copilot-instructions.md` | Copilot | defers to AGENTS.md | make lint/test существуют |
| `GEMINI.md` | Gemini session routing | root allowlist | stale make/agent names |

Codex/Junie py-* profiles (inventory): `py-audit-bot`, `py-config-bot`, `py-debug-bot`, `py-doc-bot`, `py-plan-bot`, `py-test-bot`. `py-code-bot` — documented exclusion / deprecated tombstone.

## Checks

| # | Check | Result |
| ---: | --- | --- |
| 1 | Inventory SCOPE trees | OK, non-empty |
| 2 | AGENTS.md ↔ `.junie/guidelines.md` lock-step (read) | OK semantic; Junie adds `--sync` note + `.junie/skills` dashboard paths |
| 3 | `.codex` vs `.junie` dir inventory | py-* and skill dirs match; Junie has CODEX-RUNTIME stub (intentional) |
| 4 | `junie-mirror-contract.json` + checker source | contract v1.1.0; `--check` read-only; `--sync` one-way |
| 5 | `.github/workflows/skills-consistency.yml` | jobs: doctor static, wrappers check, runtime-skill drift, junie parity, skills mirror |
| 6 | grep `curl\|` / `rm -rf` / `git reset --hard` in `scripts/ai` | no matches |
| 7 | grep secret-value print | wrappers print names not values; login uses stdin fd |
| 8 | `.env` create | gated by `BIOETL_CREATE_LOCAL_ENV_FILES=1` |
| 9 | Makefile `ai-review`/`ai-test`/`ai-docs` | **absent** (supports AGENTS-001) |
| 10 | Forbidden identifiers in live runtime maps | not in CODEX/JUNIE-RUNTIME; present in GEMINI.md |
| 11 | Devin SKILL.md orchestration pointer | **6 files → Codex ORCHESTRATION (v4.3)** |
| 12 | Coverage SSOT vs Devin py-test-bot | RULES ≥85%; Devin adds 90% domain |
| 13 | MCP prune / grok patch | destructive without dry-run |
| 14 | Copilot + path instructions | consistent with RULES/AGENTS |
| 15 | Optional CLAUDE.md / GEMINI.md guides | CLAUDE stub OK; guides still point at AGENT.md |
| 16 | Shell execution of mirror/doctor/memory | **SKIPPED** (no terminal tool in this agent) |

Skipped (fail-open for score, not for findings that have file proof):

- `bash scripts/ai/junie/check_junie_mirror.sh --check`
- `.\.venv-win\Scripts\python.exe scripts/ai/codex/doctor.py static --no-write`
- `bash scripts/ops/support/skills/check_skills_mirror.sh --check`
- `python -m scripts.ai.sync.runtime_skills --mode check`
- memory `pre-task` / `post-task`

Инвентарь **не** заменяет exit-code parity check. Byte-identical `.codex/skills` ↔ `.junie/skills` в этом прогоне не хешировался.

## Findings

| ID | Pri | Status | Path | Observation |
| --- | --- | --- | --- | --- |
| AGENTS-002 | P1 | PROVEN | `.devin/skills/py-*/SKILL.md:18` | Devin skills → Codex ORCHESTRATION (v4.3) |
| AGENTS-001 | P2 | PROVEN | `GEMINI.md:58-61` | retired agents + missing make targets |
| AGENTS-003 | P2 | PROVEN | `.devin/agents/py-test-bot/AGENT.md:58` | выдуман 90% domain coverage gate |
| AGENTS-004 | P2 | PROVEN | `docs/00-project/ai/README.md:35-56` | нет Junie equal-peer в reading priority |
| AGENTS-005 | P2 | PROVEN | `docs/00-project/ai/agents/agents/README.md:23` | Claude SSOT claim vs AGENTS.md |
| AGENTS-006 | P2 | PROVEN | `docs/00-project/ai/agents/guides/AGENT.md:35` | `git add . && git commit` |
| AGENTS-007 | P2 | PROVEN | `scripts/ai/mcp/support/mcp_docker_prune.sh:14` | `docker rm -f` без dry-run |
| AGENTS-008 | P2 | PROVEN | `scripts/ai/mcp/_patch_grok_mcp_tokens.py:69` | write `$HOME/.grok/config.toml` без dry-run |
| AGENTS-009 | P3 | PROVEN | `.codex/agents/CODEX-RUNTIME.md:55` | `python3` vs Windows `.venv-win` |
| AGENTS-010 | P3 | PROVEN | `docs/00-project/ai/agents/README.md:15-31` | edit `.codex` first, без junie check |

Полные поля: `findings.json`.

## Scripts / permissions (кратко)

- Большинство `scripts/ai/**/*.sh` имеют `set -euo pipefail`. Sourced helpers (`load_repo_env.sh`, `token_validation.sh`, `mcp_docker_prune.sh`) — нет, ожидаемо.
- `setup_agents.sh` имеет `--check` / `--dry-run` / `--install-personal`.
- MCP GitHub wrapper валидирует префикс токена, значение не echo.
- Filesystem MCP ограничен `REPO_ROOT`.
- `.devin/config.json`: deny `Write(**/.env*)` и session deny write docs/configs (оркестратор делегирует py-doc/py-config). `ask`+`deny` на Write `.env` — fail-closed, но шумно.
- Codex toml: `py-audit-bot` `sandbox_mode = read-only`. Devin py-test-bot deny write — documented vs Codex workspace-write (allowed divergence).

## Kit extras

- `agent-instruction-map.md`
- `agent-scripts.csv`
- `tool-permissions.csv`
- `instruction-conflicts.csv`
- `command-matrix.md`

## Top remediations (не применять без approval)

1. Devin `SKILL.md`: Team orchestration → `.devin/agents/ORCHESTRATION.md`; убрать `(v4.3)`; CI-assert.
2. `GEMINI.md`: живые py-audit-bot/py-test-bot/py-doc-bot; удалить `make ai-*` и forbidden identifiers; Junie equal peer.
3. Devin `py-test-bot`: убрать `≥90% domain`; сослаться на RULES ≥85%.
4. `docs/00-project/ai/README.md` + `agents/README.md`: Junie equal-peer + `check_junie_mirror.sh`.
5. `agents/agents/README.md`: Claude не SSOT.
6. `AGENT.md`: запретить `git add .`.
7. MCP prune + `_patch_grok_mcp_tokens.py`: dry-run / opt-in / не писать `$HOME` по умолчанию.
8. `CODEX-RUNTIME.md`: Windows doctor via `.venv-win`.

## Stop / residual

- Нет P0 secret/RCE в проверенном SCOPE.
- Mirror byte-parity **не верифицирован исполнением** в этой сессии.
- `.env` не читался на значения; секреты в отчёт не попали.
- Debt budgets не менялись. Код не патчился.
