# Devin Setup Prompt для BioETL

## Контекст
Ты работаешь с проектом BioETL — системой ETL-пайплайнов для биоактивности данных. Проект имеет строгие архитектурные стандарты, нормативные источники и обязательные workflow для AI-агентов.

## Обязательный Bootstrap Перед Любой Задачей

### 1. Чтение Нормативных Источников (CRITICAL)

**В следующем порядке:**

1. `AGENTS.md` — root AI runtime contract
2. `docs/00-project/NORMATIVE_SOURCES.md` — индекс нормативного стека
3. `docs/00-project/RULES.md` — Конституция проекта (архитектура, Medallion, DQ, testing, governance)
4. `docs/00-project/ai/agents/guides/MEMORY_USAGE.md` — policy для memory surfaces
5. `docs/00-project/ai/memory/agent-memory.md` — navigation entry point
6. Релевантные ADR из `docs/02-architecture/decisions/` (согласно NORMATIVE_SOURCES.md)
7. Role-specific memory sheet (если используется named role): `memory-py-*.md`

### 2. Memory Workflow (ОБЯЗАТЕЛЬНЫЙ)

**Pre-task (перед существенной работой):**

```bash
# Используй project venv с PYTHONPATH=src
bash scripts/memory/run_workflow.sh pre-task \
  --task-id <task-id> \
  --title "<описание задачи>" \
  --query <ключевые слова> \
  --profile <general|architecture|implementation|operations|audit> \
  --source-ref <ссылка на план/требование> \
  --json
```

**Post-task (после завершения работы):**

```bash
# Установи переменные окружения
export BIOETL_AI_RUNTIME=devin
export BIOETL_AI_AGENT=<agent-name>
export BIOETL_AI_MEMORY_MODE=read-write  # или read-only

python -m memory.tooling.workflow post-task \
  --task-id <task-id> \
  --title "<описание задачи>" \
  --summary "<краткое резюме изменений>" \
  --source-ref <изменённый файл> \
  --prune \
  --json
```

**Порядок чтения retrieved context:**
```
catalog -> graph -> rag -> source
```

**Важно:** Всегда сверяй memory с canonical source files. Memory — navigation layer, не source of truth.

### 3. Runtime Precedence (Критично для конфликтов)

При конфликтах инструкций используй этот приоритет:

1. **Active runtime source** (equal peers):
   - `.codex/agents/CODEX-RUNTIME.md` + `.codex/agents/py-*.md` + `.codex/skills/**`
   - `.junie/agents/JUNIE-RUNTIME.md` + `.junie/guidelines.md` + `.junie/agents/py-*.md` + `.junie/skills/**`
   - `.devin/agents/**` + `.devin/skills/**` (для Devin sessions)
   - Tracked `.gemini/**` (только если существует в checkout)
2. `docs/00-project/NORMATIVE_SOURCES.md`
3. `docs/00-project/RULES.md`
4. `docs/01-requirements/REQUIREMENTS.md`
5. Accepted ADRs в `docs/02-architecture/decisions/`
6. Docs mirrors в `docs/00-project/ai/**`

## Архитектурные Ограничения (CRITICAL)

### Слои и Импорты (Ports & Adapters)

```
src/bioetl/
├── domain/          # Чистая логика, Protocols (Ports), бизнес-модели
├── application/     # Пайплайны, Use Cases, оркестрация
├── composition/     # Composition Root (DI-контейнер, factories, bootstrap)
├── infrastructure/  # Адаптеры (HTTP, локальное хранилище), реализация портов
└── interfaces/      # CLI, PipelineRunner
```

**Матрица импортов:**
- `domain` ← `application` ← `composition` → `infrastructure`
- `interfaces` может импортировать `domain`, `application`, `composition`
- **ЗАПРЕЩЕНО:** `interfaces` → `infrastructure` напрямую
- **ЗАПРЕЩЕНО:** `domain` → `infrastructure`

**DI:** Зависимости передаются через конструктор. `composition/bootstrap/` — единственное место сборки.

### Medallion Architecture

- **Bronze:** JSONL, append-only
- **Silver:** Delta Lake, merge/upsert по `content-hash`
- **Gold:** Delta Lake, overwrite/append

### Операционные Политики

- **Стратегия загрузки (ADR-031):** `full_scan_only` ТОЛЬКО для публикаций. Остальные сущности (activity, molecule, target) MUST использовать `null` (incremental).
- **VCR кассеты:** Используй для HTTP-тестов. Никаких секретов в кассетах.
- **DQ контракты:** Следуй ADR-027, ADR-045.

## Guardrails (ЗАПРЕЩЕНЫЕ ДЕЙСТВИЯ)

### 1. Env File Guardrail (CRITICAL)

**ЗАПРЕЩЕНО:** Создавать, редактировать, переименовывать, перемещать, перезаписывать или удалять любой `.env` файл без явного разрешения пользователя.

Если задача требует изменения `.env`:
1. ОСТАНОВИСЬ
2. Опиши точное изменение
3. Запроси явное разрешение пользователя

### 2. Technical Debt Guardrail

**ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА:**
- `scorecard budgets` из `configs/quality/debt_scorecard.yaml`
- Exemption limits из `configs/quality/architecture_metric_exemptions.yaml`
- Hotspot thresholds из `scripts/engineering/README.md`
- Family caps для duplication, file size, complexity

Если изменение упирается в лимит:
- Уменьши scope
- Или эскалируй пользователю

### 3. Root Scratch Ban

**ЗАПРЕЩЕНО:** Создавать файлы в корне репозитория:
- `_tmp_*.py`
- `/_cr_*.py`
- `/_publish_*.py`
- `test_*.py` (ad-hoc)
- Windows device names (`nul`, `NUL`)

Используй:
- `scripts/**` для скриптов
- `reports/**` для отчётов

### 4. Destructive Operations

**ЗАПРЕЩЕНО** без явного подтверждения:
- `rm -rf` на директориях
- Удаление/обрезание таблиц БД
- Force-push, rewrite git history
- Отправка email, платежей, API calls с реальными side effects

## Post-Change Validation (ОБЯЗАТЕЛЬНО)

После любой write-capable задачи:

1. **Re-scan** затронутые и связанные surfaces
2. **Repo search + memory/evidence anchors** для поиска related tests, docs, contracts
3. **Edit runtime source first**, затем sync docs mirrors
4. **Runtime mirror parity:** после изменений `.codex/**` или `.junie/**`:
   ```bash
   bash scripts/ai/junie/check_junie_mirror.sh --check
   ```
5. **Module coverage inventory hash** после изменений `src/bioetl/**/*.py`:
   ```bash
   python -m scripts.engineering.qa report-module-coverage --allow-missing-coverage-xml
   ```
6. **Отчёт:** Explicitly укажи:
   - Какие проверки запущены
   - Какие пропущены и почему
   - Статус mirror-sync
   - Debt outcome: `improved` | `unchanged` | `worsened`

## Verification Protocol (ЗАПРЕЩЕНО ЛОЖНЫЕ УТВЕРЖДЕНИЯ)

**ПРИЧИНА:** ~60% ложных утверждений в планах рефакторинга.

**ПРОТОКОЛ:**

1. **Прочитай целевой файл** (read tool)
2. **Проверь размер** (`wc -l`, `grep -c "def "`)
3. **Проверь делегирование** (`grep` по вызовам сервисов)
4. **Сверься с кодом и active docs** → RULES / ADR / review artifacts

**Формат верифицированного предложения:**

```markdown
## Предложение: [Название]

### Верификация
- **Файл:** `path/to/file.py` (N строк, M методов)
- **Текущее поведение:** [описание с ссылками на строки]
- **Проверено по коду и active docs:** ✅

### Проблема
[Конкретное описание с `файл:строка`]

### Предлагаемое решение
[Решение]
```

## Environment Configuration

**ВСЕ токены и параметры** из repository root `.env`:

- **MCP интеграции:** `DEEPWIKI_API_KEY`, `DEEPWIKI_ORGANISATION_ID`, `CONTEXT7_API_KEY`, `NEEDLE_API_KEY`
- **GitHub:** `GITHUB_TOKEN`, `GITHUB_PERSONAL_ACCESS_TOKEN`, `GITHUB_CDX_PERSONAL_ACCESS_TOKEN`
- **LLM:** `OPENAI_API_KEY`, `GROK_API_TOKEN`
- **Search:** `BRAVE_API_KEY`
- **Code quality:** `QODO_API_KEY`, `SONARQUBE_TOKEN`
- **Docker:** `DOCKER_API_KEY`, `DOCKER_USERNAME`, `HUB_PAT_TOKEN`

**Важно:** `.env` — machine-local и secret-bearing. НЕ коммить в репозиторий.

## Skills Routing

Используй соответствующие skills для задач:

- **py-plan-bot:** Планирование задач
- **py-audit-bot:** Аудит кода/конфигов
- **py-debug-bot:** Отладка, RCA, bug fixes
- **py-doc-bot:** Документация, ADR, CHANGELOG
- **py-test-bot:** Тесты, анализ покрытия
- **py-config-bot:** YAML конфигурации (pipeline, DQ, filter, composite)
- **observability-dashboard:** Grafana dashboards (без запуска monitoring)
- **observability-prometheus:** Prometheus alerts/recording rules
- **verify-architecture:** Architecture compliance checks
- **new-pipeline:** Scaffold нового pipeline
- **vcr-record:** VCR кассеты для HTTP-тестов

## Dashboard Skill Routing (Optional)

- **Monitoring/Grafana — OPTIONAL (ADR-010)**
- **НЕ запускай** `docker-compose.monitoring.yml` без явного запроса
- Default Docker surface: **main only** (health on `:8000`)

## Response Language

- **По умолчанию:** Отвечай на русском, если пользователь пишет на русском
- **Технические литералы:** Код, команды, пути, идентификаторы, имена полей API — в оригинальной форме
- **Switch:** Меняй язык только при явном запросе пользователя

## Ключевые Команды

```bash
# Bootstrap
make install
make test-deps
make setup-plugins

# Проверка статуса
make lint && make test

# Основные команды
make run-local    # сэмпловый pipeline-run
make lint         # ruff + mypy
make test         # локальный стабильный прогон

# Memory workflow
bash scripts/memory/run_workflow.sh pre-task ...
python -m memory.tooling.workflow post-task ...

# Architecture checks
python -m scripts.engineering.qa report-module-coverage
bash scripts/ai/junie/check_junie_mirror.sh --check
```

## Навигация по Репозиторию

- **Product code:** `src/bioetl/`
- **Tests:** `tests/`
- **Configuration:** `configs/`
- **Architecture evidence:** `docs/reports/evidence/`
- **Quality/debt governance:** `configs/quality/`, `reports/quality/`
- **Runtime tooling:** `scripts/ai/`, `scripts/ops/`
- **Documentation map:** `docs/00-project/00-map.md`
- **Glossary:** `docs/00-project/glossary.md`

## Evidence Calibration

Для задач, затрагивающих файловую структуру, package topology, hotspot selection:

**Сверься с:**
- `docs/reports/evidence/project-file-structure/SUMMARY.md`
- `docs/reports/evidence/project-package-topology/SUMMARY.md`
- `docs/reports/evidence/governance-signals/SUMMARY.md`

**Operational rule:**
- Breadth сама по себе ≠ debt
- Package family важнее whole layer
- Governance signals важнее интуитивных structural claims

## DI False-Positive Guardrail

**НЕ помечай как AP-001:**
- Test-only scaffolding в `tests/**` (`MagicMock`, `AsyncMock`, `SimpleNamespace`)
- `Path(...)` и stdlib conversions (если только нормализуют вход)
- Infrastructure-local helper construction в `infrastructure/**` (adapter implementation)

## Заключительные Правила

1. **Читай RULES.md → Планируй → Делай → Проверяй → Документируй**
2. **Никаких предположений** — верифицируй по коду
3. **Memory ≠ source of truth** — сверяй с canonical sources
4. **Не увеличивай техдолг** — только уменьшай или оставляй неизменным
5. **Env files — sacred** — не трогай без разрешения
6. **Post-change validation — обязательна** — включи в отчёт

## Related Files

- `AGENTS.md` — root AI runtime contract
- `docs/00-project/NORMATIVE_SOURCES.md` — нормативный стек
- `docs/00-project/RULES.md` — Конституция проекта
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md` — memory policy
- `docs/00-project/ai/memory/agent-memory.md` — navigation entry point
- `src/memory/DAILY_WORKFLOW.md` — memory workflow
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` — post-change protocol
