# /review-orchestrator

Иерархический code review BioETL по 8 секторам (L1/L2/L3).

## Использование

```
/review-orchestrator [mode] [scope]
```

**Режимы:**
- `full` — полный review всех секторов S1-S8 (по умолчанию)
- `sector` — review одного сектора
- `wave1` — только Wave 1 (S1-S4: layer reviews)
- `wave2` — только Wave 2 (S5-S8: cross-cutting, tests, configs, docs)

**Scope (опционально):**
- `S1`..`S8` — конкретный сектор
- `domain`, `application`, `infrastructure`, `composition`, `interfaces` — по слою
- Без scope — весь проект

**Секторы:**

| ID | Сектор | Scope | Weight |
|:--:|--------|-------|:------:|
| S1 | Domain Layer | `src/bioetl/domain/` | 20% |
| S2 | Application Layer | `src/bioetl/application/` | 20% |
| S3 | Infrastructure Layer | `src/bioetl/infrastructure/` | 20% |
| S4 | Composition + Interfaces | `src/bioetl/composition/` + `interfaces/` | 10% |
| S5 | Cross-cutting | All `src/bioetl/` (import matrix, AP-*) | 10% |
| S6 | Tests | `tests/` | 8% |
| S7 | Configs | `configs/` | 5% |
| S8 | Documentation | `docs/` | 7% |

**Примеры:**
```
/review-orchestrator                        # полный review S1-S8
/review-orchestrator sector S1              # только domain review
/review-orchestrator wave1                  # S1-S4 параллельно
/review-orchestrator full infrastructure    # полный, focus на infra
```

---

## Инструкции для Claude

### Шаг 1: Загрузить спецификацию

Прочитай `.claude/agents/py-review-orchestrator.md` — полный профиль агента (725 строк).

### Шаг 2: Запуск

Запустить через Task tool:

```python
Task(
  subagent_type="py-review-orchestrator",
  description="L1 review orchestrator: {mode}",
  prompt="""
  Прочитай `.claude/agents/py-review-orchestrator.md` и выполни роль L1-оркестратора.

  Параметры:
  - mode: {mode}
  - scope: {scope}

  Выполни review согласно профилю.
  Сохрани отчёты в reports/review/.
  """,
  model="opus"
)
```

### Шаг 3: Вывести результат

После завершения:

1. **Overall Score**: N/10 (PASS/WARN/FAIL)
2. **Таблица секторов** с оценками
3. **Critical/High issues** (top-10)
4. **Путь к `reports/review/FINAL-REVIEW.md`**

### Scoring

| Score | Status |
|:-----:|:------:|
| ≥ 8.0 | PASS |
| 6.0 - 7.9 | WARN |
| < 6.0 | FAIL |

Deductions: CRITICAL=-2.0, HIGH=-1.0, MEDIUM=-0.5, LOW=-0.25

### Артефакты

```
reports/review/
├── S1-domain.md
├── S2-application.md
├── S3-infrastructure.md
├── S4-composition-interfaces.md
├── S5-crosscutting.md
├── S6-tests.md
├── S7-configs.md
├── S8-documentation.md
└── FINAL-REVIEW.md
```
