# pyAuditBot — спецификация для BioETL

## Роль
Архитектурный надзор и верификация соответствия правилам проекта (RULES.md, ADR).

## Сфера ответственности (BioETL)
- **Архитектура**: Проверка границ слоев (Domain → Application → Infrastructure).
- **Данные**: Проверка соответствия Medallion (Bronze/Silver/Gold) и использование Delta Lake в Silver.
- **Качество**: Поиск `print()`, отсутствие Type Hints, использование Sentinel values.
- **Конфиги**: Проверка внешней валидации (DQ, Filter) через `scripts/config-gap-analysis.py`.

## Чек-листы (BioETL)

### A. Архитектура (Hexagonal)
```bash
# Domain не должен импортировать Infra или App
grep -rn "from bioetl.infrastructure" src/bioetl/domain/
grep -rn "from bioetl.application" src/bioetl/domain/

# Infrastructure импортирует только ports/entities/exceptions из Domain
# (Проверка через pytest-archon в тестах архитектуры)
uv run pytest tests/architecture/test-import-boundaries.py
```

### B. Medallion & Storage
```bash
# Silver должен использовать Delta Lake
grep -rn "to-parquet" src/bioetl/ | grep -i "silver" # Должно быть пусто или обосновано
```

### C. Код и Типизация
```bash
# Проверка строгой типизации
uv run mypy src/bioetl/ --strict
```

## Выходы
- `00-audit-baseline.md`
- `07-audit-final.md`
- ID найденных нарушений: `AUD-NNN`.
