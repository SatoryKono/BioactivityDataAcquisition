# Pre-flight Check Report

**Дата**: 2026-01-06
**Версия проекта**: 5.9.0
**RULES.md**: v5.10

## Состояние репозитория

- **Working tree**: чистый
- **Текущая ветка**: `claude/project-preflight-cleanup-Wj18M`
- **Синхронизация с main**: да (0 коммитов отставания)
- **Последний коммит**: `d6c04d70` - Merge pull request #1379

## Зависимости

### pip-audit
- **Статус**: Выполнено
- **Результат**: 0 уязвимостей (HIGH/CRITICAL)
- **Примечание**: bioetl (5.9.0) не на PyPI — ожидаемое поведение для локального пакета

### Удалённые зависимости (ADR-010)
| Пакет | Статус |
|-------|--------|
| redis | ✓ Отсутствует |
| boto3 | ✓ Отсутствует |
| prefect | ✓ Отсутствует |
| aioredis | ✓ Отсутствует |
| fakeredis | ✓ Отсутствует |
| moto | ✓ Отсутствует |

## Версионирование

| Файл | Версия | Статус |
|------|--------|--------|
| pyproject.toml | 5.9.0 | ✓ |
| src/bioetl/__init__.py | 5.9.0 | ✓ |
| CHANGELOG.md | [5.9.0] - 2026-01-06 | ✓ |
| docs/RULES.md | v5.10 | ✓ |

## Local-Only Deployment (ADR-010)

### Облачные зависимости в коде
- **Статус**: ✓ Отсутствуют (импорты)
- **Найдено упоминаний**: 2 (только в документации/комментариях)
  - `pipeline_runner_service.py:164` — перечисление возможных schedulers (документация)
  - `_bootstrap/lock.py:27` — примечание о distributed scenarios (комментарий)

### MemoryLock параметры

| Параметр | Код | RULES.md v5.10 | Статус |
|----------|-----|----------------|--------|
| Lock TTL | 90s | 90s (heartbeat × 3) | ✓ Совпадает |
| Heartbeat | 30s | 30s | ✓ Совпадает |

**Источники в коде:**
- `application/core/config.py:47` — `lock_ttl: int = 90`
- `application/core/config.py:50` — `heartbeat_interval: int = 30`
- `domain/config.py:238,241` — defaults совпадают
- `infrastructure/config.py:254` — `heartbeat_interval: int = Field(default=30, ge=5, le=60)`

## Очистка

| Категория | До очистки | Удалено |
|-----------|------------|---------|
| `__pycache__/` | 58 dirs | 58 dirs |
| `.pyc` files | 405 files | 405 files |
| `.egg-info/` | 1 dir | 1 dir |
| `.pytest_cache/` | 0 | — |
| `.mypy_cache/` | 0 | — |
| `.ruff_cache/` | 0 | — |
| `.coverage*` | 0 | — |
| `*.log` | 0 | — |
| IDE/OS artifacts | проверено | очищено |

## .gitignore

- **Статус**: ✓ Полный
- **Ключевые паттерны присутствуют**:
  - `__pycache__/`, `*.py[cod]`
  - `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
  - `.coverage`, `.coverage.*`, `htmlcov/`
  - `*.log`, `*.tmp`
  - `.DS_Store`, `Thumbs.db`
  - `.env` (кроме `.env.example`)

## data/ директория

- **Статус**: ✓ Чистая
- **Содержимое**: только `input/` (fixtures)
- **Временные файлы**: не найдены (`*.tmp`, `test_output_*`, `debug_*`)

## Секреты и конфиденциальность

- **Tracked .env files**: ✓ Нет (только `.env.example` разрешён)
- **VCR кассеты**: Настроена санитизация в `.gitignore`

## Блокеры для следующего этапа

Нет блокеров. Проект готов к следующему этапу валидации.

---

*Отчёт сгенерирован автоматически: 2026-01-06*
