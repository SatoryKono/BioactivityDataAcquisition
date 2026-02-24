# Codex Branches Summary — 2026-02-24, 12:45–13:15 MSK

> Окно: последний 1 час (12:45–13:15 +0300)
> Фильтр: только ветки с изменениями в коде (`.py`, `.sh`, `.yml`, `Makefile`, `.gitignore`)
> Всего codex-веток в окне: **7**, из них с кодом: **5** (2 — чисто документационные)

---

## Группа 1: CI/CD & Version Governance (2 ветки)

### 1.1 `codex/update-version-in-documentation-and-add-ci-check`
- **Commit:** `799a588dc` — Add version consistency CI check and update docs version
- **Время:** 13:09:51 +0300
- **Изменения:**
  - Новый скрипт `scripts/check_version_consistency.py` (+80 строк) — проверяет синхронность версии между `pyproject.toml`, `src/bioetl/__init__.py`, `docs/00-project/index.md` и `CHANGELOG.md`
  - Добавлен step "Validate version consistency" в `.github/workflows/docs.yml` и `.github/workflows/tests.yml`
  - Обновлён `docs/00-project/index.md` (метаданные версии)
- **Характер:** CI-гейт для consistency версий

### 1.2 `codex/update-documentation-for-current-version`
- **Commit:** `cf49c8e80` — docs: sync release metadata and enforce version check
- **Время:** 13:09:22 +0300
- **Изменения:**
  - Новый скрипт `scripts/check_docs_version_sync.py` (+59 строк) — проверяет синхронность версии между `pyproject.toml` и `docs/00-project/index.md`
  - Обновлены `docs/00-project/00-map.md`, `docs/00-project/index.md`, `.github/CONTRIBUTING.md`
- **Характер:** Дублирует часть функционала 1.1 (проверка pyproject vs docs/index.md)

> **Замечание:** Ветки 1.1 и 1.2 содержат пересекающуюся логику. `check_version_consistency.py` — более полная версия (4 источника вместо 2). Рекомендуется объединить или оставить только 1.1.

---

## Группа 2: Скрипты Cleanup & Data Governance (2 ветки)

### 2.1 `codex/add-preflight-cleanup-script-with-dry-run`
- **Commit:** `2adee9a96` — Add preflight cleanup script with dry-run and Make target
- **Время:** 13:09:56 +0300
- **Изменения:**
  - Новый скрипт `scripts/preflight_cleanup.sh` (+125 строк) — удаляет `__pycache__`, `*.pyc`, `*.egg-info`, `build/`, `dist/`, `htmlcov/`, `.coverage`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`. Поддерживает `--dry-run` для превью
  - Новый Makefile target `clean-preflight` с поддержкой `DRY_RUN=1`
  - Обновлён `docs/05-operations/RELEASE_CHECKLIST.md`
- **Характер:** DevOps tooling — pre-release cleanup

### 2.2 `codex/document-file-categories-for-data-directory`
- **Commit:** `2ffb5d917` — Add data directory governance and validation checks
- **Время:** 13:13:55 +0300
- **Изменения:**
  - Новый скрипт `scripts/validate_data_dir.py` (+138 строк) — валидирует файлы в `data/` по allowlist и size limits. Категории: `input-fixture`, `reference-fixture`, `test-fixture`, `golden-data`, `directory-marker`, `documentation`
  - `.gitignore`: добавлены `data/local/*` и `!data/local/.gitkeep`
  - Удалены бинарные файлы `data/_publication.xlsx` и `data/publication.xlsx` (~45 МБ)
  - Создан `data/local/.gitkeep`
  - Обновлены `docs/00-project/governance/03-file-policy.md`, `docs/templates/pipeline-review-checklist.md`
- **Характер:** Data governance — размер и тип файлов в repo

---

## Группа 3: Архитектурные тесты (1 ветка)

### 3.1 `codex/update-adr-baseline-and-checklists`
- **Commit:** `054682c04` — docs(adr): normalize status policy and enforce ADR status gate
- **Время:** 13:09:11 +0300
- **Изменения:**
  - Новый тест `test_adr_status_is_from_allowed_set()` в `tests/architecture/test_documentation_sync.py` (+42 строки) — проверяет, что каждый ADR файл содержит статус из множества `{accepted, superseded, deprecated, added}`
  - Обновлены: `.claude/prompts/02-Sync/04-schema-review.md`, `.claude/prompts/02-Sync/05-vcr-tests.md`, `docs/00-project/RULES.md`, `docs/02-architecture/decisions/ADR-033-publication-validation-strategy.md`, `docs/02-architecture/decisions/README.md`, `docs/02-architecture/diagrams/PROMPT-diagram-expansion.md`
- **Характер:** Arch test — ADR status validation gate

---

## Чисто документационные ветки (без кода, исключены из анализа)

| Ветка | Commit | Описание |
|-------|--------|----------|
| `codex/update-documentation-with-latest-values-and-paths` | `a2300aadd` | Обновление AGENT.md, CLAUDE.md, ORCHESTRATION.md |
| `codex/update-git-setup-and-pre-flight-script` | `5efcec7b9` | Обновление `.claude/prompts/03-repository-cleanup-assistant.md` |

---

## Сводная таблица

| # | Ветка | Группа | Новые файлы | Строки кода | Пересечения |
|---|-------|--------|-------------|-------------|-------------|
| 1 | `update-version-in-documentation-and-add-ci-check` | CI/CD | `check_version_consistency.py`, 2× workflow steps | +86 | С веткой #2 |
| 2 | `update-documentation-for-current-version` | CI/CD | `check_docs_version_sync.py` | +59 | С веткой #1 (подмножество) |
| 3 | `add-preflight-cleanup-script-with-dry-run` | Cleanup | `preflight_cleanup.sh`, Makefile target | +135 | — |
| 4 | `document-file-categories-for-data-directory` | Data Gov | `validate_data_dir.py`, .gitignore, удалены .xlsx | +140 | — |
| 5 | `update-adr-baseline-and-checklists` | Arch Tests | `test_adr_status_is_from_allowed_set` | +42 | — |

## Рекомендации по мержу

1. **Мержить первой:** `#3 preflight-cleanup` — независимый, полезный tooling, конфликтов нет
2. **Мержить второй:** `#4 data-governance` — удаляет ~45 МБ бинарников из repo, добавляет валидацию
3. **Выбрать одну из:** `#1` или `#2` — содержат дублирующуюся логику проверки версий. Рекомендация: `#1` (более полная)
4. **Мержить последней:** `#5 adr-baseline` — затрагивает docs/RULES.md, потенциальные конфликты с другими ветками
