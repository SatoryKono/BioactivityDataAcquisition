# SchemaRegistry

**Модуль:** `src/bioetl/schemas/registry.py`

Центральный реестр для управления схемами данных (Pandera Schemas). Обеспечивает доступ к схемам по имени сущности и хранит метаданные, необходимые для детерминизма.

## Задачи

1. **Регистрация схем**: Связывание имени сущности (например, `activity`) с классом схемы (`ActivitySchema`).
2. **Порядок колонок**: Хранение канонического списка колонок `column_order` для обеспечения стабильности CSV/Parquet.
3. **Бизнес-ключи**: Хранение определения бизнес-ключа для дедупликации.

## Использование

### Регистрация

```python
registry = SchemaRegistry()
registry.register(
    name="activity",
    schema=ActivitySchema,
    column_order=["activity_id", "molecule_chembl_id", ...],
    business_key=["assay_chembl_id", "molecule_chembl_id", "standard_type"]
)
```

### Получение схемы

```python
schema = registry.get_schema("activity")
# Возвращает класс ActivitySchema
```

### Получение порядка колонок

```python
cols = registry.get_column_order("activity")
# ["activity_id", "molecule_chembl_id", ...]
```

## Валидация

Реестр используется `ValidationService` для проверки данных и приведения порядка колонок. Если в DataFrame порядок отличается от зарегистрированного, он будет автоматически исправлен перед записью.

