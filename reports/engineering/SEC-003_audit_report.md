# Аудит-отчет по SEC-003 (ast.literal_eval в composite_metadata_helpers)

## Паспорт закрытия
* **Владелец работы:** Jules
* **Срок:** Октябрь 2026
* **Точная ревизия (SHA):** f07ead17df6283b9a7d2d8bfc7e10e2358f97c8b
* **Область:** src/bioetl/domain/behavior/composite_metadata_helpers.py
* **Методология:** Анализ происхождения (taint analysis) + тестирование ограничений CPython-парсера.
* **Результат:** PASS (невоспроизводимость, вход доверенный).
* **Независимый проверяющий:** n/a (аудит-сессия)

## 1. Происхождение входа (Taint Analysis)
Цель: `ast.literal_eval` в `src/bioetl/domain/behavior/composite_metadata_helpers.py` внутри функции `_parse_literal`.

Вызовы к `_parse_literal` приходят из:
1. `parse_composite_list`
2. `parse_composite_status`
3. `parse_composite_field_sources`

Они, в свою очередь, вызываются из:
* `_normalize_composite_lineage_payload`
* `_build_composite_output_ext`

Они принимают на вход сырые словари (Mapping[str, object]), содержащие метаданные (`_source_providers`, `_enrichment_status`, `_field_sources`).
Эти метаданные генерируются и записываются _самим пайплайном_ BioETL, например в `src/bioetl/application/composite/merger_metrics_mixin.py` в методе `_add_lineage`:
```python
pl.lit(json.dumps(sources_used)).alias("_source_providers"),
pl.lit(json.dumps(status_dict, sort_keys=True)).alias("_enrichment_status")
```
и сохраняются в Parquet/Delta Lake.
Таким образом, данные, попадающие в `ast.literal_eval`, являются полностью **внутренними и доверенными**. Они формируются системой в формате JSON (json.dumps) или в legacy-формате (строковое представление Python-словаря `str(dict)`). Пользовательский неконтролируемый ввод напрямую не попадает в эти поля.

Доверенность входа: **CONFIRMED** (системные артефакты).

## 2. Воспроизведение риска (Adversarial Testing)
**Команда:** `uv run python -c "import ast; ast.literal_eval('[' * 1000 + ']' * 1000)"`

**Результат тестирования на глубокую вложенность:**
```
SyntaxError: too many nested parentheses
```

Начиная с последних версий Python, `ast.literal_eval` (а точнее, сам парсер CPython) имеет жесткое ограничение на глубину вложенности (обычно 200 - **ESTIMATED** на основе реализации парсера). Попытка передать слишком глубоко вложенную структуру (глубина 1000 - **MEASURED**) вызывает не исчерпание памяти (MemoryError/Crash), а контролируемое исключение `SyntaxError` на этапе парсинга (время выполнения < 0.1s - **ESTIMATED**).

В коде `_parse_literal` уже присутствует обработка:
```python
except (ValueError, SyntaxError, MemoryError, TypeError, RecursionError):
    return None
```
Таким образом, `SyntaxError` (а также `MemoryError` и `RecursionError`) перехватывается, и функция безопасно возвращает `None`.

Риск отказа в обслуживании (DoS / исчерпание памяти / краш процесса): **NOT_VERIFIABLE** (полностью подавляется существующей обработкой исключений и ограничениями парсера CPython).

## 3. Заключение
* Вход `_parse_literal` происходит от внутренних, системно генерируемых метаданных (структуры lineage/enrichment). Он не подвержен инъекции произвольных вредоносных данных извне.
* Риск глубокой рекурсии не подтверждается. Ограничения встроенного парсера Python (`SyntaxError: too many nested parentheses`) перехватываются штатным блоком `except` в функции, возвращая `None`.
* Так как формат legacy-метаданных в старых таблицах может не быть валидным JSON (могут использоваться одинарные кавычки), fallback на `ast.literal_eval` необходим для сохранения обратной совместимости. Замена на строгий JSON-парсер без переписывания старых данных нарушит контракт чтения (формат не семантически эквивалентен, JSON требует двойных кавычек).
* Ограничивать длину строки перед разбором не требуется, так как риск не реализуем.

**Статус:** Проверено, риск не подтверждён.
Кодовые мутации не требуются (в соответствии с гейтом Этапа 0).
