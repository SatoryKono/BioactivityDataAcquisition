# BioETL AI Rules

Правила проекта для AI-ассистентов (Claude, Cursor, и др.)

## Структура

```
docs/00-project/ai/rules/
├── README.md                    # Этот файл
├── bioetl-ai-rules.md         # Универсальные правила (любой AI)
├── cursor/                      # Cursor IDE правила (.mdc)
│   ├── 00-architecture.mdc
│   ├── 01-data-quality.mdc
│   ├── 02-code-style.mdc
│   ├── 03-testing.mdc
│   └── 04-patterns.mdc
└── [скопировать в .cursor/rules/]
```

Источник канонических правил: `docs/00-project/RULES.md` (v6.1.4)

Этот каталог является condensed AI guidance surface. Он **не заменяет**
канонический governance stack и должен ссылаться на него, а не дублировать его
без необходимости:

- `AGENTS.md`
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
- `00-architecture.mdc` — слои, импорты, порты
- `01-data-quality.mdc` — Medallion, Delta Lake
- `02-code-style.mdc` — mypy strict, ruff
- `03-testing.mdc` — VCR.py, coverage
- `04-patterns.mdc` — адаптеры, композиты

**Как работает:** Cursor автоматически применяет эти правила при:
- Автодополнении кода
- Генерации новых файлов
- Рефакторинге
- Code review

### B. Codex / Claude-style CLI workflows

**Настройка:**

- Канонический источник правил: `docs/00-project/RULES.md`
- Runtime orchestration guidance: `.codex/agents/ORCHESTRATION.md`
- Legacy Claude mirror paths are retired and must not be used as active
  reference paths.

**Ручное использование:** При новом чате упомяните:
> "Следуй правилам из docs/00-project/RULES.md и orchestration guidance из .codex/agents/ORCHESTRATION.md"

### C. Универсальные правила (любой AI)

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
2. Обновить `.cursor/rules/*.mdc` (если скопированы)
3. Обновить `docs/00-project/ai/rules/cursor/*.mdc` (источник)

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
