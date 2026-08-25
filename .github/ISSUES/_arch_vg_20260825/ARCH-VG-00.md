## Контекст

Прогон **verify-architecture full** 2026-08-25 на Windows (`.venv-win`):

```text
pytest tests/architecture/ -m "not slow and not benchmark and not memory"
```

Результат: **92 failed / 4318 passed / 74 skipped / 4484**, exit 1, ~692 с. Канон: pre-commit `architecture-full`, lane `architecture` в `configs/quality/test_matrix.yaml`.

Это **операционный unblocker гейта**, не повтор программы интеграла 7.43 (#9617).

## Уже открыто — не дублировать

| Issue | Почему не этот epic |
|---|---|
| #9617 | Программа shrink god-packages / lazy / scorecard honesty |
| #9624 | Regen ADR matrix + совпадение integral md/json |
| #9622 | Долгая пересборка mixin-агрегатов к target_modules |
| #9626 | Плановый shrink private-import ниже 19 |
| #9620 | Sunset `*_api` facades |

## Дочерние issues этой волны

| Code | Pri | Issue | Тема |
|---|---|---|---|
| ARCH-VG-01 | P0 | #9640 | Починить quality-артефакты (JSON/hash/inventory) |
| ARCH-VG-02 | P0 | #9642 | Синхронизировать Batch-фасад с реестрами/тестами/SCC |
| ARCH-VG-03 | P1 | #9641 | Контракты ADR-058 `application/ports` |
| ARCH-VG-04 | P1 | #9644 | Запретить `interfaces → composition._resource_management` |
| ARCH-VG-05 | P2 | #9643 | Точечные ratchet: ruff, Any, LOC, entrypoints, silver wiring |

Порядок: #9640 → параллельно #9642 / #9644 / #9641 → #9643.

## Правила

- Бюджеты техдолга не повышать (`AGENTS.md`).
- Не ослаблять architecture-тесты, чтобы закрыть гейт.
- Не сливать `application/ports` обратно в `domain/ports` (ADR-058).

## Definition of Done

- Тот же pytest-гейт зелёный на GitHub SHA (кроме известных Windows skip).
- Все дочерние issues закрыты или явно wontfix с причиной.
- Связанные #9622 / #9624 / #9626 не блокируются этой волной и не переоткрываются как дубли.
