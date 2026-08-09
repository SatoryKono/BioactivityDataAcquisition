# Test Fix/Re-test Loop

## Evaluation Metadata
- **Category:** Test Prompts
- **Weighted Score:** 7.06 / 10
- **Overall Rating:** High
- **Path:** docs/00-project/ai/prompts/test_fix_retest_loop.md

## Evaluation Breakdown
- Clarity: 7/10 (weight: 0.15)
- Completeness: 7/10 (weight: 0.15)
- Specificity: 7/10 (weight: 0.12)
- Context: 7/10 (weight: 0.10)
- Guardrails: 7/10 (weight: 0.10)
- Maintainability: 7/10 (weight: 0.08)
- Reusability: 7/10 (weight: 0.08)
- Error Handling: 7/10 (weight: 0.08)
- Validation: 7/10 (weight: 0.07)
- Documentation: 7/10 (weight: 0.07)

## Original Content

# Test Fix/Re-test Loop

*Статус: internal (working prompt artifact)*

> **Surface note:** Это рабочий промт, не каноническая политика проекта.
> Для реальных правил пользуйтесь `docs/00-project/RULES.md` и runtime
> guides under `docs/00-project/ai/agents/`.

## Prompt

```text
Цель: отлаживать и исправлять задачу до зелёного состояния тестов по циклу «run → fix → run».

## 1) Запусти тесты (целево, минимально)
- Если есть известная ошибка (failure) — прогоняю только затронутые тесты.
- Если падений нет, запускаю минимальный релевантный scope для текущей задачи.
- Запускаю подходящую команду для окружения:
  - Linux/WSL: `bash scripts/engineering/dev/run_pytest.sh <scope> --maxfail=1 -q`
  - Windows: `.\scripts\engineering\dev\run_pytest.ps1 <scope> --maxfail=1 -q`
  - fallback: `python -m pytest <scope> -q`
- В каждом прогоне фиксирую: команду, scope, статус, количество падений, первые ошибки.

## 2) Если ошибок нет — заверши
- Если все тесты пройдены (`exit code == 0`): зафиксируй результат и заверши задачу.
- Отчёт по шагу 2:
  - что именно тестировал;
  - итоговый статус;
  - фактический scope и команда.

## 3) Если есть ошибки — фиксишь и возвращаешься к шагу 1
- Разбираю root cause по первому приоритетному фейлу.
- Вношу минимально достаточное исправление (без расширения scope без нужды).
- Снова запускаю **тот же scope**.
- Повторяю цикл, пока:
  - получен green;
  - либо обнаружен блокер non-actionable (инфраструктурный/внешний фактор) с явной фиксацией,
    почему он не может быть исправлен в текущем контуре,
  - либо исчерпан лимит итераций (по умолчанию 5).

## 4) Условия остановки
- Завершай только когда:
  - все тесты зелёные; или
  - лимит итераций исчерпан с явной фиксацией блокеров и следующими шагами.
- В финале всегда указывай:
  - число итераций;
  - какие ошибки были и как исправлялись;
  - текущее состояние (`green / partially green / blocked`);
  - следующий шаг для ручного/внешнего блокера.
```
