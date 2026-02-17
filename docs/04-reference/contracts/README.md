# Contracts Reference

Этот раздел фиксирует контракты данных и требования к их стабильности для Bronze/Silver/Gold.

## Hash Stability Guarantees

Контракт стабильности `content_hash` обязателен для всех pipeline, использующих SCD Type 2 и дедупликацию.

### Determinism Guarantees

При неизменных `provider`, `record`, `exclude_none` функция генерации хэша **MUST** возвращать одинаковый
64-символьный hex SHA256 digest.

### Invariance Guarantees

`content_hash` **MUST** быть инвариантен к:

- перестановке ключей в `dict` (за счет `sort_keys=True`);
- служебным полям `_ingestion_ts`, `_run_id`, `_run_type`, `_source_batch_id`, `_index`, `_dq_*`;
- `NaN`/`Inf` (нормализуются в `null`);
- избыточным пробелам в строках по краям (`strip()`).

### Controlled Variance Guarantees

`content_hash` **MUST** изменяться, если меняются бизнес-значения после canonicalization.

Дополнительно:

- `float` значения сравниваются в нормализованной форме `round(value, 10)`;
- политика `exclude_none` является частью контракта вызова:
  - `exclude_none=false`: `null` участвует в хэше;
  - `exclude_none=true`: `null` исключается из хэш-входа.

### Canonical JSON Contract

Перед SHA256 сериализация **MUST** использовать:

```python
json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
```

Итоговая формула:

```text
sha256(provider + canonical_json)
```

### Regression Coverage

Стабильность хэша проверяется регрессионной матрицей в unit-тестах доменного слоя:

- key-order permutation;
- string trim behavior;
- float precision normalization;
- NaN/Inf normalization.
