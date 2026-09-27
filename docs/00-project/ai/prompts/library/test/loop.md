---
id: prompt.tests.loop
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- any
params:
- SCOPE
- MAX_ITERATIONS
- LANGUAGE
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/language-ru.md
related_ssot:
- AGENTS.md
- docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
- scripts/engineering/dev/run_pytest.sh
- scripts/engineering/dev/run_pytest.ps1
anti_patterns:
- Expanding test scope without justification
- Silent infra blockers
- Infinite fix loops without iteration cap
- Closing task before scope is green
- Skipping per-run report
tags:
- tests
- loop
- fix-retest
- operator
summary: Loop run → report → fix → retest until green with mandatory per-run report
---

# Test loop — run → report → fix → retest

Упрощённый цикл для оператора: последовательно гоняй тесты, чини, повторяй до зелёного. Расширен `prompt.tests.fix-retest` обязательным отчётом о каждом запуске.

## Параметры

| Param | Default | Описание |
| --- | --- | --- |
| `SCOPE` | `tests/` | путь/nodeid или `all` (явный синоним всего `tests/`, тяжёлый прогон) |
| `MAX_ITERATIONS` | `5` | лимит итераций, защита от бесконечного цикла |
| `LANGUAGE` | `ru` | язык отчёта |

## Команды

- Linux/WSL: `bash scripts/engineering/dev/run_pytest.sh <SCOPE> --maxfail=0 -q`
- Windows: `.\scripts\engineering\dev\run_pytest.ps1 <SCOPE> --maxfail=0 -q`
- fallback (только если враппер недоступен): `python -m pytest <SCOPE> -q` / `.\.venv-win\Scripts\python.exe -m pytest <SCOPE> -q`
- При `SCOPE=all`: `pytest tests` — весь `tests/` (тяжёлый прогон, только для релиза/регрессии).

Гардрейлы: не трогать `.env`, не повышать бюджеты техдолга, не создавать файлы в корне (`_tmp_*.py`, `test_*.py`, `nul`), не расширять scope без причины, ветка не `main`.

## Цикл /loop — итерация 1..MAX_ITERATIONS

### 1. Запусти тесты (целиком, по очереди)

Запусти **все тесты проекта** в `SCOPE` последовательно. Зафиксируй: команду, scope, длительность, exit code.

### 2. Обязательный отчёт о каждом запуске

После **каждого** прогона выведи блок в консоль:

```text
[Итерация N/M] SCOPE=<scope> CMD="<команда>" STATUS=green|red
Всего выполнено: <passed+failed+skipped> (passed: <N>, failed: <N>, skipped: <N>, xfail: <N>)
Если red:
  Упало: <failed_count> — список:
    - <nodeid1> — <короткий traceback / assert>
    - <nodeid2> — ...
  Остальные: <сколько прошло и каких категорий>
Если green:
  Все <total> тестов зелёные в scope
```

Правила:
- указывай **точные** `nodeid` упавших тестов;
- не агрегируй в "несколько тестов" — перечисли;
- при `red` добавь строку `Результат починки (предыдущая итерация): <что чинил → delta>`.

### 3. Если ошибок нет — завершай

- `exit 0` → итоговый отчёт: итераций, что тестировалось, scope, команда, `green`.
- Закрой задачу только когда `SCOPE` зелёный.

### 4. Если есть ошибки — исправь и вернись к п.1

- Определи первопричину самого приоритетного фейла (product / test-bug / fixture / env/infra / flaky-suspect).
- Минимальный фикс, тот же `SCOPE`. Flaky без N перезапусков не маркировать, ретрай ≠ фикс.
- Выполни `POST_CHANGE_VALIDATION`: ре-скан затронутых поверхностей, sync зеркал `.codex/.junie` если трогал.
- Снова п.1 с тем же `SCOPE` (или суженным списком упавших nodeid, затем полный `SCOPE` для верификации).
- В отчёте следующей итерации отрази `Результат починки`.

## Стоп-условия

Завершай только когда `green` **или** `MAX_ITERATIONS` исчерпан с `blocked`/`partial`. Всегда отчитайся: `iterations`, `fails_before/after`, `state` (`green` / `partial` / `blocked`), `next step` для внешних блокеров. Не лупуй бесконечно.

## Итоговый отчёт (после цикла)

| Итерация | SCOPE/CMD | Всего | Passed | Failed (список) | State | Починка |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `tests/`, `bash scripts/engineering/dev/run_pytest.sh tests/ --maxfail=0 -q` | 120 | 118 | 2 (`tests/test_x.py::test_a`, `tests/test_y.py::test_b`) | partial | фикс `test_a` → −1 фейл к итерации 2 |

Легенда: `State`: `green` — весь `SCOPE` зелёный; `partial` — часть прошла; `blocked` — лимит исчерпан или внешний блокер. `Починка`: что чинил в этой итерации → delta к следующей.
