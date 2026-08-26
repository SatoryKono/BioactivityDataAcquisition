# Agents / runtime audit — `prompt.audit.agents-runtime`

| Field | Value |
| --- | --- |
| `domain_id` | `agents-runtime` |
| `prompt_id` | `prompt.audit.agents-runtime` |
| `version` | card 1.2.0 |
| `MODE` | `audit` |
| `AUDIT_MODE` | `full` |
| `LANGUAGE` | `ru` |
| `REQUIRE_GH_TRACKING` | `false` |
| `SCOPE` | `AGENTS.md` `.codex/` `.junie/` `.devin/` `docs/00-project/ai/` |
| Date | 2026-08-26 |
| `surface_score` | **2** / 3 |
| `blocked` | `false` |

## Executive summary

Канонический runtime-стек на месте: equal-peer `.codex/**` ↔ `.junie/**` с контрактом
`scripts/ai/junie/junie-mirror-contract.json` и CI job
`verify-codex-junie-runtime-parity`; Devin — отдельное дерево `.devin/agents/**` +
`.devin/skills/**`; docs в `docs/00-project/ai/**` в основном помечены как mirrors.
Env-guardrail и запрет роста tech-debt бюджетов повторены в `AGENTS.md`,
`.junie/guidelines.md` и runtime maps. `curl|bash`, `git reset --hard` и печать
значений токенов в `scripts/ai/**` не найдены.

Материальные разрывы: (1) матрица permissions Devin (`config.json` deny write
`docs/`+`configs/` против профилей, которым эти write нужны); (2) Junie runtime map
заявляет content-parity с Codex, которую checker не считает, и уже разошёлся
WSL-интерпретатор; (3) docs-guides (`CODEX.md`, `GEMINI.md`, `AGENT.md`) обходят
`AGENTS.md` в обязательном read-order; (4) сломанный agent-script
`py-team-orchestration.py`. P0 (секрет/RCE/destroy without guard) не доказан.

**Оценка 2:** основной workflow воспроизводим и закрыт автоматизацией; есть
конфликтующие инструкции и избыточные/противоречивые permissions, но не
системный отказ механизма.

## Instruction scope graph

```text
AGENTS.md  ≡  .junie/guidelines.md          (root contracts, lock-step claimed)
    ├─ .codex/agents/CODEX-RUNTIME.md       (Codex-only map)
    ├─ .junie/agents/JUNIE-RUNTIME.md       (Junie-only map)
    ├─ .devin/agents/DEVIN-RUNTIME.md       (Devin-only map)
    ├─ profiles: .codex/agents/py-*.md  ==  .junie/agents/py-*.md  (SHA-256 contract)
    │            .devin/agents/*/AGENT.md   (platform variant)
    ├─ skills:   .codex/skills/**  →sync→  .junie/skills/**
    │            .devin/skills/**           (SKILL.md may vary; references identical)
    ├─ scripts:  scripts/ai/{junie,codex,mcp,sync}/
    ├─ CI:       .github/workflows/skills-consistency.yml
    └─ mirrors:  docs/00-project/ai/**      (MUST NOT redefine behavior)
                 .github/copilot-instructions.md
                 GEMINI.md (root)
```

Owner matrix coincides with
`docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md`.

## Method

- Read: audit card + fragments (`evidence-contract`, `finding-schema`,
  `debt-budget-ban`, `env-guardrail`, `audit-scale`, `generic-nine-contract`),
  `AGENTS.md`, `NORMATIVE_SOURCES.md`, ownership, POST_CHANGE, runtime maps,
  Devin config/profiles, catalogs, gitignore, skills-consistency workflow.
- Inventory: `.codex/`, `.junie/`, `.devin/`, `docs/00-project/ai/`, `scripts/ai/`.
- Grep: `curl|`, `git reset --hard`, secret-echo, `.env` writes, opus/sonnet,
  WSL venv, `rm -rf`.
- Static compare: sampled `.codex/agents/py-audit-bot.md` vs
  `.junie/agents/py-audit-bot.md` (identical prefix); `SKILLS-CATALOG.md` across
  Codex/Junie/Devin/docs-local (identical text); `ORCHESTRATION.md` Codex/Junie
  (identical header).
- **Не запускалось** (в этой сессии нет shell): live
  `bash scripts/ai/junie/check_junie_mirror.sh --check`,
  `python scripts/ai/codex/doctor.py static --no-write`,
  `bash scripts/ai/codex/check_skills_mirror.sh --check`,
  `python -m scripts.ai.sync.runtime_skills --mode check`,
  `python -m scripts.docs check-drift --runtime-mirrors --freshness`,
  memory `pre-task`/`post-task`.
- `.env` не читался на предмет значений; не изменялся. Бюджеты техдолга не
  трогались.

Live hash-parity `.codex/**`↔`.junie/**` = **NOT_PROVEN** (нет exit code
checker). Контракт, CI path-filter и architecture tests
(`tests/architecture/test_junie_runtime_ci_contract.py`) существуют.

## Surface score

| Score | Meaning (domain card) | This audit |
| ---: | --- | --- |
| 3 | Instructions consistent; scripts reproducible; tools limited; validation automated | — |
| **2** | Main workflow reliable; a few undocumented preconditions | **Selected** |
| 1 | Implicit env assumptions, excessive permissions, or conflicting instructions | partial (conflicts exist, not systemic) |
| 0 | Agent can leak a secret, destroy data, or run uncontrolled privileged action | not proven |

Mapping: domain card 0–3 (not 0–5).

## Findings (PROVEN preferred)

Полный machine-readable набор: `findings.json`. Ниже — condensed.

| ID | Pri | Status | Path | Observation |
| --- | --- | --- | --- | --- |
| AGT-001 | P1 | PROVEN | `.devin/config.json:24-27` | Project `deny` Write `docs/**` и `configs/**` противоречит `py-doc-bot` / `py-config-bot` |
| AGT-002 | P2 | PROVEN | `.junie/agents/JUNIE-RUNTIME.md:23-29,126-127` | Checker не сравнивает runtime maps; WSL python уже drifted |
| AGT-003 | P2 | PROVEN | `.devin/config.json:4-6,24-25` | `Write(**/.env*)` одновременно в `ask` и `deny` |
| AGT-004 | P2 | PROVEN | `.devin/agents/py-audit-bot/AGENT.md:6-21` | Read-only профили дают `Exec(python)` |
| AGT-005 | P2 | PROVEN | `docs/00-project/ai/agents/scripts/py-team-orchestration.py:15-25` | Резолв в несуществующий `src/tools/scripts/lint_terminology.py` |
| AGT-006 | P2 | PROVEN | `.devin/agents/DEVIN-SETUP-GUIDE.md:119` | Codex «opus/sonnet» — в `.codex` моделей нет, inherit parent |
| AGT-007 | P2 | PROVEN | `docs/00-project/ai/agents/guides/CODEX.md:21-35` | Обязательный контекст без `AGENTS.md` / runtime maps |
| AGT-008 | P2 | PROVEN | `docs/00-project/ai/agents/guides/GEMINI.md:17-24` | Mandate RULES-only, без runtime precedence |
| AGT-009 | P2 | PROVEN | `.devin/agents/py-test-bot/AGENT.md:4` | `model: swe-1.6` vs DEVIN-RUNTIME «Default subagent model» |
| AGT-010 | P2 | PROVEN | `scripts/ai/mcp/mcp_filesystem_wrapper.sh:17` | Filesystem MCP = весь `REPO_ROOT`, включая `.env` write |
| AGT-011 | P2 | PROVEN | `scripts/engineering/qa/check_quality_exemptions.py:4-5` | Canonical quality-exemptions script живёт в docs-дереве |
| AGT-012 | P3 | PROVEN | `docs/00-project/ai/agents/guides/CLAUDE.md:9` | Hardcoded RULES v6.1.5 vs 6.1.11 |
| AGT-013 | P3 | PROVEN | `.gitignore:300-305,657` | `.agents/` un-ignore затем полный ignore; CI всё ещё watches `.agents/skills/**` |
| AGT-014 | P3 | PROVEN | `docs/00-project/ai/memory/mcp-memory.json:8` | Stale Loki/Tempo observation |
| AGT-015 | P3 | PROVEN | `.codex/agents/CODEX-RUNTIME.md:54-57` | Сломанная фраза про `python -m` / doctor.py |
| AGT-016 | P3 | PROVEN | `docs/00-project/ai/agents/scripts/py-config-bot-1.py:12` | Output `docs/audits/config_gaps.md` — каталога нет |
| AGT-017 | P3 | PROVEN | `.devin/agents/README.md:70-77` | Сломанные markdown-таблицы `\|\|` |
| AGT-018 | P3 | PROVEN | `docs/00-project/ai/agents/runtime/orchestration/py-team-orchestration.md:16-28` | DEPRECATED, но описывает 8 агентов (`pyCodeBot`) |
| AGT-019 | P3 | PROVEN | `AGENTS.md:140-146` | Related Files не указывает `.junie/guidelines.md` / runtime maps |
| AGT-020 | P3 | PROVEN | `.devin/agents/DEVIN-SETUP-GUIDE.md:64` | «all 18 servers» vs MCP policy 21 |

`p0_p1_count` = 1. `proven_count` = 20. NOT_PROVEN findings в массив не включались
(live parity вынесен в skipped checks).

## Top remediations

1. Согласовать `.devin/config.json` deny/allow с профилями: либо убрать project-deny
   `Write(**/docs/**)` / `Write(**/configs/**)`, либо сузить deny так, чтобы
   `py-doc-bot`/`py-config-bot` могли писать свои поверхности; `Write(**/.env*)`
   оставить только в `deny` (не в `ask`).
2. Выровнять Proof-or-Stop WSL interpreter в `JUNIE-RUNTIME.md` с
   `CODEX-RUNTIME.md` / README (`${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}`);
   сузить формулировку «content parity enforced» до того, что реально проверяет
   `check_junie_mirror.py` (profile names + dashboard refs + forbidden ids).
3. В docs-guides (`CODEX.md`, `GEMINI.md`, `AGENT.md`) поставить `AGENTS.md` и
   matching runtime map первым пунктом обязательного контекста.
4. Починить `py-team-orchestration.py` → `scripts/engineering/qa/lint_terminology.py`
   (или удалить wrapper и ссылки из deprecated orchestration).
5. Убрать `Exec(python)` у read-only Devin профилей либо ограничить allow-list
   командами; не полагаться только на `deny: write`.
6. Перенести canonical quality-exemptions implementation из
   `docs/00-project/ai/agents/scripts/` в `scripts/engineering/qa/` (docs = wrapper).
7. Добавить в `AGENTS.md` portable команду
   `python scripts/ai/junie/check_junie_mirror.py --check` рядом с bash.
8. Почистить stale: RULES version literals, Loki/Tempo в `mcp-memory.json`,
   opus/sonnet, «18 servers», `||` tables, `docs/audits`.

## Scripts / permissions (summary)

- `setup_agents.sh` / `setup_skills.sh`: `--check` и `--dry-run` есть; `set -euo pipefail`.
- MCP wrappers: `set -euo pipefail`; `token_validation.sh` не печатает значения.
- `check-env.ps1` создаёт `.env.codex` только при `BIOETL_CREATE_LOCAL_ENV_FILES=1`.
- Codex native descriptors: `sandbox_mode = "read-only"` у `py-audit-bot` /
  `py-debug-bot`.
- Devin: profile-based + project `config.json` (конфликт — AGT-001/003/004).

## Kit extras

- `agent-instruction-map.md`
- `agent-scripts.csv`
- `tool-permissions.csv`
- `instruction-conflicts.csv`
- `command-matrix.md`

## Guardrails honored

- Tech-debt budgets: не предлагалось увеличивать.
- `.env`: не создавался/не редактировался.
- Product code: не изменялся.
- Runtime trees: не редактировались (MODE=audit).
