# Agents / runtime audit

- prompt: `prompt.audit.agents-runtime` 1.2.1
- domain: `agents-runtime`
- mode: `audit` / `AUDIT_MODE=full`
- checkout: `.worktrees/nine-domain-20260925`
- HEAD: `32d77a51e556`
- checked_at: `2026-09-25T08:42:45Z`
- surface_score: **1** (шкала карточки 0–3)

Оценка 1: есть доказанные конфликты инструкций и команд. Это не 0: секрет в отчёт не попал, `curl | bash` у OpenCode не вызывается, parity-проверки зелёные. Это не 2: расхождение касается опубликованного Devin MCP bootstrap, а не только неописанного предусловия.

## Итог

Канонические деревья `.codex`, `.junie`, `.devin` на месте. `docs/00-project/ai/**` помечен как mirror. Junie parity и Codex–Devin skill parity проходят. Ломается опубликованный контракт tier MCP и четыре заголовка skill-зеркал, которые указывают на несуществующий `.codex/skills` path.

PROVEN: 4. NOT_PROVEN: 2. P0: 0. P1: 1.

## Проверки

| Команда | scope | exit | вывод |
| --- | --- | --- | --- |
| `python scripts/ai/junie/check_junie_mirror.py --check` | checkout | 0 | `Junie mirror parity OK` |
| `python -m scripts.ai.sync.governance --root . --only skill-mirrors --check` | checkout | 0 | `AI governance surfaces checked successfully` |
| inventory SKILL.md + `shared-servers.json` | checkout | 0 | 14 Codex skills; 4 overlay без runtime-файла; 19 MCP servers, daily=true у 9 |

`--sync` не запускался. `.env` не читался и не менялся.

## Карта инструкций

| Уровень | Путь | Владелец |
| --- | --- | --- |
| root | `AGENTS.md` | равный peer-контракт Codex/Junie/Devin |
| Junie root | `.junie/guidelines.md` | runtime Junie |
| runtime map | `.codex/agents/CODEX-RUNTIME.md` | Codex-only по `junie-mirror-contract.json` |
| runtime map | `.junie/agents/JUNIE-RUNTIME.md` | Junie-only |
| runtime map | `.devin/agents/DEVIN-RUNTIME.md` | Devin |
| profiles | `.codex/agents/py-*.md` + `.toml` | Codex; md зеркалируется в `.junie/agents/py-*.md` |
| profiles | `.devin/agents/*/AGENT.md` | Devin |
| skills | `.codex/skills/**` (14) | runtime Codex; byte-parity с `.junie/skills/**` |
| skills | `.devin/skills/**` | runtime Devin; references идентичны, `SKILL.md` может отличаться по контракту |
| mirror | `docs/00-project/ai/**` | не SSOT |
| prompts | `docs/00-project/ai/prompts/**` | operator aid |
| subordinate | `opencode.json`, `.github/workflows/opencode-*.yml` | Phase 1, installer отключён |
| optional | `.github/copilot-instructions.md`, `GEMINI.md` | отсылают к `AGENTS.md`, не подменяют runtime |

`.junie/agents/CODEX-RUNTIME.md` — stub, не копия SSOT. `py-code-bot` в контракте исключён и в деревьях отсутствует.

## Матрица команд

| Инструкция | Фактическая цель | Статус |
| --- | --- | --- |
| `make devin` / `make devin-check` / `make devin-mcp-start` (`--daily`) | есть в Makefile; `--daily` есть в `start-shared.sh` | совпадает с DEVIN-RUNTIME |
| `make devin-mcp-start-minimal` (`--minimal`) | флага нет; health отвергает `minimal` | AGENTS-001 |
| `make devin-mcp-start-standard` | флага нет; гайд называет это default для `devin-mcp-start` | AGENTS-001 |
| `make devin-mcp-start-full` («all 18») | вызывает `--daily` (9 из 19 серверов), не `--all` | AGENTS-001 |
| `make lint`, `make test` (`--cov-fail-under=85`) | Makefile:110-115 | совпадает |
| `make security` в py-audit-bot | есть только `security-check` | AGENTS-003 |
| `doctor.py static --no-write` | режим и флаг есть | команда жива; фраза в CODEX-RUNTIME склеена (AGENTS-004) |
| OpenCode workflow | `echo` disabled, `contents: read` | `curl \| bash` не исполняется |

## Скрипты

| Скрипт | dry-run / fail | заметка |
| --- | --- | --- |
| `scripts/ai/junie/check_junie_mirror.py --check` | read-only, exit 0 | parity OK |
| `scripts/ai/sync/governance.py --only skill-mirrors --check` | read-only, exit 0 | не ловит битый canonical header: эталон генерируется тем же кодом |
| `scripts/ops/runtime/mcp/start-shared.sh` | `set -euo pipefail`; неизвестное имя сервера → SystemExit | `--minimal`/`--standard` попадают в список серверов |
| `.github/workflows/opencode-pr-review.yml` | workflow_dispatch, без installer | соответствует AGENTS.md |

## Права

| Профиль | sandbox / allow | deny |
| --- | --- | --- |
| Codex `py-audit-bot`, `py-debug-bot`, `py-plan-bot` | `read-only` | github MCP запрещён в toml |
| Codex `py-config-bot`, `py-doc-bot`, `py-test-bot` | `workspace-write` | github MCP запрещён |
| Devin `py-audit-bot` | Read, точечный Exec | `write`, `edit` |
| Devin `py-test-bot` | `Write(tests/**)`, `Exec(make)`, `Exec(python)` | write вне tests, `Exec(gh)` — ширина Exec не доказана (AGENTS-005) |
| `.devin/config.json` | Read `.env*` в ask и allow | Write `.env*` в ask и deny — победитель не доказан (AGENTS-006) |
| `.codex/config.toml` | `agents.max_threads = 3` | секретов и абсолютных путей нет |

## Конфликты

См. `findings.json`: AGENTS-001 (P1), AGENTS-002 (P2), AGENTS-003 (P2), AGENTS-004 (P3). AGENTS-005 и AGENTS-006 — `NOT_PROVEN`.

Позитивные факты, не ставшие находками: equal-peer precedence в `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md`; OpenCode не качает `releases/latest`; tracked MCP bind `127.0.0.1`; `npx` пакет закреплён как `mcp-proxy@6.5.4`.
