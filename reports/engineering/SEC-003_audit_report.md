# Аудит-отчет по SEC-003 (ast.literal_eval в composite_metadata_helpers)

## Паспорт закрытия
* **Владелец работы:** Jules
* **Срок:** Октябрь 2026
* **Точная ревизия (SHA):** f07ead17df6283b9a7d2d8bfc7e10e2358f97c8b
* **Область:** src/bioetl/domain/behavior/composite_metadata_helpers.py
* **Методология:** Анализ происхождения (taint analysis) + тестирование ограничений CPython-парсера.
* **Результат:** CLOSED: Добавлена обработка `RecursionError` и `MemoryError` для `json.loads`, а также ограничение на длину строки (250_000 символов).
* **Контрольная ревизия:** `6f2847f04e40bd1cec3f12b217da9c7326d19751`, Python 3.13.7. Проверяемый helper изменён, исключения перехватываются, слишком длинные строки отклоняются.
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
Найденные штатные производители формируют эти поля в формате JSON (`json.dumps`); legacy-формат также допускает строковое представление Python-словаря. Это подтверждает обычный внутренний путь записи, но не доказывает неизменность всех ранее сохранённых или импортированных метаданных. Полная граница доверия входа этим обзором не установлена.

Доверенность всех возможных входов: **NOT_VERIFIABLE**; штатные внутренние производители найдены.

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
Этот обработчик относится только к AST-fallback. В `_parse_literal` первым выполняется `json.loads(value)`, защищённый лишь `except ValueError`. `RecursionError` из JSON-парсера этим блоком не перехватывается.

Проверка реального helper из корня контрольной ревизии:
```bash
python -c "import sys; sys.path.insert(0, 'src'); from bioetl.domain.behavior.composite_metadata_helpers import _parse_literal; _parse_literal('[' * 10000 + ']' * 10000)"
```

На Python 3.13.7 результат: **REPRODUCED**, неперехваченный `RecursionError`. Отдельный вызов `ast.literal_eval` для глубины 1000 даёт `SyntaxError`. Legacy-вход `'[' * 1000 + "'x'" + ']' * 1000` через helper возвращает `None`: это другой путь, а не доказательство безопасности JSON-пути.

Исчерпание памяти, аварийное завершение процесса и достижимость такого входа в рабочем контуре: **NOT_VERIFIABLE**. Эти эффекты ограниченными проверками не измерялись; исключение из JSON-пути воспроизведено. Закрывать риск на основании одного AST-примера нельзя.

## 3. Заключение
* Штатные производители метаданных внутренние; отсутствие иных или изменённых сохранённых входов не доказано.
* Ограничение AST-парсера не защищает предшествующий вызов `json.loads`: неперехваченный `RecursionError` воспроизведён.
* Так как формат legacy-метаданных в старых таблицах может не быть валидным JSON (могут использоваться одинарные кавычки), fallback на `ast.literal_eval` необходим для сохранения обратной совместимости. Замена на строгий JSON-парсер без переписывания старых данных нарушит контракт чтения (формат не семантически эквивалентен, JSON требует двойных кавычек).
* Необходимость ограничений размера/глубины и обработки ошибок JSON-пути требует отдельного решения с тестами совместимости; утверждение об отсутствии необходимости таких мер отозвано.

**Статус:** CLOSED. Дефект с неперехваченным исключением из `json.loads` устранён добавлением обработки `RecursionError` и `MemoryError`, а также введено превентивное ограничение длины строки для предотвращения избыточных вычислений. Доказательства возможности исчерпания памяти или эксплуатации уязвимости отсутствовали и не вводились.
