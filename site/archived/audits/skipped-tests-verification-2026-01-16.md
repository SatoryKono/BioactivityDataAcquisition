# Skipped Tests Verification Report

**Дата**: 2026-01-16
**RULES.md**: v5.10
**Версия проекта**: 5.9.0+

---

## Сводка

Все пропущенные тесты проверены и подтверждены как **легитимные** (by design).

| Метрика | Значение |
|---------|----------|
| Всего тестов | 6928 |
| Passed | 6862 |
| Skipped | 31 |
| Deselected | 35 |
| Failed | 0 |

---

## Классификация пропущенных тестов

### 1. Architecture Tests (1 skipped)

| Тест | Файл | Причина | Статус |
|------|------|---------|--------|
| `test_allowed_composition_files_still_exist` | `test_env_var_centralization.py:169` | `ALLOWED_COMPOSITION_FILES` пуст (ожидаемо) | ✓ Легитимный |

**Анализ**: Тест проверяет, что файлы из списка `ALLOWED_COMPOSITION_FILES` существуют. Когда список пуст (что является желаемым состоянием — нет исключений для прямого доступа к env vars в composition слое), тест пропускается. Это корректное поведение.

### 2. Contract Tests (30 skipped)

| Провайдер | Тестов | Причина |
|-----------|--------|---------|
| ChEMBL | 8 | `BIOETL_LIVE_API_TESTS=false` |
| PubChem | 8 | `BIOETL_LIVE_API_TESTS=false` |
| PubMed | 7 | `BIOETL_LIVE_API_TESTS=false` |
| UniProt | 7 | `BIOETL_LIVE_API_TESTS=false` |

**Анализ**: Contract тесты требуют реальных API-вызовов и отключены по умолчанию для безопасности CI/CD. Это **by design** согласно ADR-010 (Local-Only Deployment).

**Запуск вручную**:
```bash
BIOETL_LIVE_API_TESTS=true pytest tests/contract/ -v --tb=short
```

---

## Условные пропуски (skipif) — Не активны

Следующие `@pytest.mark.skipif` присутствуют в коде, но **не срабатывают** на Python 3.11:

| Условие | Тестов | Статус на Python 3.11 |
|---------|--------|----------------------|
| `PYTHON_314` (Hypothesis issues) | 3 | Не срабатывает |
| `PYTHON_314` (Pandera issues) | 5 | Не срабатывает |
| `not ORJSON_AVAILABLE` | 5 | Не срабатывает (orjson установлен) |
| `not _ruff_available` | 3 | Не срабатывает (ruff установлен) |

---

## Вывод

**Действия не требуются.**

Все 31 пропущенных тест имеют явное обоснование:
- 1 architecture тест — пропуск при пустом allowlist (ожидаемо)
- 30 contract тестов — отключены для CI безопасности (by design)

Условные skipif декораторы настроены для Python 3.14 совместимости и не влияют на текущее окружение (Python 3.11).

---

## Команды верификации

```bash
# Полный прогон тестов
python3 -m pytest tests/ --tb=no -q

# Проверка пропущенных тестов
python3 -m pytest tests/ -rs --tb=no

# Contract тесты (требуют Live API)
BIOETL_LIVE_API_TESTS=true python3 -m pytest tests/contract/ -v
```

---

## Сравнение с предыдущим отчётом

| Метрика | 2026-01-06 | 2026-01-16 | Изменение |
|---------|------------|------------|-----------|
| Всего тестов | 5856 | 6928 | +1072 |
| Passed | 5825 | 6862 | +1037 |
| Skipped | 31 | 31 | 0 |
| Failed | 0 | 0 | 0 |

Рост количества тестов обусловлен добавлением новых unit и architecture тестов. Количество skipped тестов осталось неизменным.

---

*Отчёт создан: 2026-01-16*
