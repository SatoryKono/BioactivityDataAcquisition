# BioETL AI Rules

Правила проекта для AI-ассистентов (Claude, Cursor, и др.)

## Структура

```
docs/00-project/ai/rules/
├── README.md                    # Этот файл
├── bioetl-ai-rules.md         # Универсальные правила (любой AI)
├── cursor/                      # Cursor IDE правила (.mdc)
│   ├── 00-bioetl-core-governance.mdc
│   ├── 00-architecture.mdc
│   ├── 01-data-quality.mdc
│   ├── 02-code-style.mdc
│   ├── 03-testing.mdc
│   ├── 04-patterns.mdc
│   ├── 05-agent-workflow.mdc
│   ├── 06-docs-standards.mdc
│   ├── 07-qodo-enforcement.mdc  # Индекс правил Qodo (синхронизация)
│   ├── 08-operations.mdc        # Secrets, locks, backfill, DR
│   ├── 09-observability.mdc     # Logs, metrics, anomaly, control plane
│   ├── 10-error-resilience.mdc  # Retry, CB, DQ thresholds
│   └── 11-schema-evolution.mdc  # Drift SLA, contracts, rollback
├── windsurf/                    # Windsurf/Cascade (производная от cursor/)
│   ├── rules/*.md
│   └── workflows/*.md
└── [скопировать в .cursor/rules/ и .windsurf/]
```

Источник канонических правил: `docs/00-project/NORMATIVE_SOURCES.md` → `docs/00-project/RULES.md` (v6.1.5)
Текущую canonical version всегда сверяйте по `Version:` header в `RULES.md`.

Этот каталог является condensed AI guidance surface. Он **не заменяет**
канонический governance stack и должен ссылаться на него, а не дублировать его
без необходимости:

- `AGENTS.md`
- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`

## Использование

### A. Cursor IDE

**Настройка:**

```bash
# Скопировать правила в директорию Cursor
mkdir -p .cursor/rules
cp docs/00-project/ai/rules/cursor/*.mdc .cursor/rules/
```

**Структура `.cursor/rules/`:**
- `00-bioetl-core-governance.mdc` — инварианты, детерминизм, секреты
- `00-architecture.mdc` — слои, импорты, порты
- `01-data-quality.mdc` — Medallion, Pandera, Delta Lake
- `02-code-style.mdc` — mypy strict, ruff
- `03-testing.mdc` — VCR.py, coverage
- `04-patterns.mdc` — адаптеры, композиты
- `05-agent-workflow.mdc` — workflow агента, guardrails
- `06-docs-standards.mdc` — стандарты документации
- `07-qodo-enforcement.mdc` — индекс правил Qodo platform
- `08-operations.mdc` — secrets, locks, backfill, checkpoint, DR
- `09-observability.mdc` — structured logs, Prometheus, anomaly detection
- `10-error-resilience.mdc` — retry, circuit breaker, DQ policy
- `11-schema-evolution.mdc` — schema drift, contracts, deprecation

**Как работает:** Cursor автоматически применяет эти правила при:
- Автодополнении кода
- Генерации новых файлов
- Рефакторинге
- Code review

### B. Windsurf Cascade

**SSOT:** `docs/00-project/ai/rules/cursor/*.mdc`
**Tracked mirror:** `docs/00-project/ai/rules/windsurf/`
**Local deploy:** `.windsurf/` (gitignored)

```bash
# Сгенерировать rules + deploy workflows в .windsurf/
uv run python scripts/ai/sync_windsurf_rules.py

# Только проверить синхронизацию
uv run python scripts/ai/sync_windsurf_rules.py --check
```

**Workflows (slash commands):** `/review`, `/post-change`, `/pre-commit`, `/qodo-sync`

### B2. Devin

**Tracked workflows:** `.devin/workflows/`
Держите parity с Cascade workflows: `review`, `post-change`, `pre-commit`, `qodo-sync` (плюс специализированный `audit-documents`).

**DeepWiki:** `.devin/wiki.json` — navigation only; не заменяет `RULES.md` / ADR / Cursor SSOT.

При обновлении Qodo/rules:
1. Править `docs/00-project/ai/rules/cursor/*.mdc`
2. `sync_cursor_rules.py --deploy` + `sync_windsurf_rules.py`
3. Синхронизировать текст `.devin/workflows/{review,post-change,pre-commit,qodo-sync,audit-documents}.md`
4. При необходимости обновить notes в `.devin/wiki.json` (Project Governance / AI Runtime / Secret Rules)

### C. Codex / Claude-style CLI workflows

**Настройка:**

- Канонический источник правил: `docs/00-project/RULES.md`
- Runtime orchestration guidance: `.codex/agents/ORCHESTRATION.md`
- Legacy Claude mirror paths are retired and must not be used as active
  reference paths.

**Ручное использование:** При новом чате упомяните:
> "Следуй правилам из docs/00-project/RULES.md и orchestration guidance из .codex/agents/ORCHESTRATION.md"

### D. Универсальные правила (любой AI)

Используйте: `docs/00-project/ai/rules/bioetl-ai-rules.md`

Подходит для:
- GitHub Copilot
- ChatGPT с Custom Instructions
- Локальных моделей через Continue.dev
- Любого другого AI-ассистента

## Ключевые принципы (кратко)

### 1. Архитектура (Clean / Ports & Adapters)

```
domain/         → Pure logic, NO I/O
application/    → Orchestration
infrastructure/ → Adapters
composition/    → DI wiring ONLY
interfaces/     → CLI
```

**Импорты строго по матрице** — слой не может импортировать выше себя.

### 2. Код

- **Всегда:** `from __future__ import annotations`
- **Типы:** `list[str]`, `X | None` (не `List`, не `Optional`)
- **Проверка:** `mypy --strict`, `ruff`

### 3. Данные (Medallion)

| Слой | Формат | Ключевое |
|------|--------|----------|
| Bronze | JSONL+zstd | Append-only |
| Silver | Delta Lake | Merge/Upsert |
| Gold | Delta Lake | SCD Type 2 |

### 4. Критические правила

- ❌ NO `random` в writers
- ❌ NO `datetime.now()` в infrastructure
- ✅ Все адаптеры: `async def health_check(self) -> HealthStatus`
- ✅ Все сервисы: `async def aclose(self) -> None`
- ✅ JSON поля: `Series[str]` (canonical JSON)
- ✅ Hash: `sha256(provider + canonical_json(record))`

### 5. Тестирование

- Coverage: ≥85%
- Integration: VCR.py с sanitize secrets
- E2E: `@pytest.mark.e2e`, local-only

## Обновление правил

При изменении `docs/00-project/RULES.md`:

1. Обновить `bioetl-ai-rules.md` (краткая версия)
2. Обновить `docs/00-project/ai/rules/cursor/*.mdc` (источник)
3. Обновить `docs/00-project/ai/rules/RULES_COVERAGE_MATRIX.md` при изменении покрытия
4. Синхронизировать governance surfaces:
   ```bash
   uv run python scripts/ai/sync_ai_governance.py
   uv run python scripts/ai/sync_cursor_rules.py --deploy
   uv run python scripts/ai/sync_windsurf_rules.py
   ```

### Синхронизация с Qodo platform

Правила Qodo загружаются через skill `/qodo-get-rules` (или полный extract в `reports/quality/qodo-rules-extract-*.md`) и интегрируются в тематические `.mdc` файлы.
Индекс синхронизации: `07-qodo-enforcement.mdc` (последний sync: **2026-07-16**, 66 unique rule IDs).
После обновления cursor rules:

```bash
uv run python scripts/ai/sync_cursor_rules.py --deploy
uv run python scripts/ai/sync_windsurf_rules.py
```

## Команды верификации

```bash
# Архитектурные тесты
uv run python -m scripts.engineering.qa check-exemptions
uv run python -m pytest tests/architecture/test_quality_debt_scorecard.py -q

# Линтинг и тесты
make lint
make test

# E2E
pytest tests/e2e/ -v -m e2e
```

## Troubleshooting

### Cursor не применяет правила

- Проверьте что `.cursor/rules/*.mdc` существуют
- Перезапустите Cursor
- Проверьте синтаксис YAML frontmatter (должен быть валидным)

### Claude игнорирует правила

- В новом чате явно упомяните: "Используй правила из docs/00-project/RULES.md"
- При необходимости отдельно укажите orchestration guidance из
  `.codex/agents/ORCHESTRATION.md`
- Не полагайтесь на legacy Claude mirror paths как на canonical source

### Конфликт версий правил

Канонический источник: `docs/00-project/RULES.md`
Версия в этих файлах должна соответствовать.

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
