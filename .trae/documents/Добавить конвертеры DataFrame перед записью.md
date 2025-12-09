**Цели**

* Ввести подключаемый конвертер `DataFrame → DataFrame` перед записью.

* Поддержать указание конвертера через `pipeline_config.yaml` (`output.converter`).

* Реализовать базовые конвертеры: `Noop`, `RenameColumns`, `DropNaRows` и композицию `rename_and_dropna`.

**Контракты**

* Добавить `OutputFrameConverterABC(Protocol)` с методом `convert(df) -> pd.DataFrame` в `bioetl.domain.clients.base.output.contracts`.

* Зарегистрировать роль в `abc_registry.yaml` и default‑factory в `abc_impls.yaml`.

**DI и фабрики**

* Создать `bioetl.infrastructure.output.converters.factories.default_output_frame_converter(converter_id: str | None) -> OutputFrameConverterABC`.

  * `None|"noop"` → `NoopConverter`.

  * `"rename_columns"` → `RenameColumnsConverter` (snake\_case → kebab-case).

  * `"dropna"` → `DropNaRowsConverter`.

  * `"rename_and_dropna"` → композиция (сначала rename, затем dropna) без ввода нового публичного класса (через объект с `convert`).

* Обновить `bioetl.interfaces.container_factory.build_default_container()` для создания конвертера из `config.output.converter` и передачи его в `OutputWriter`.

**Модель конфига**

* Добавить `OutputOptionsConfig` в `bioetl.domain.configs.pipeline` с полем `converter: str | None = None`.

* Добавить поле `output: OutputOptionsConfig` в `PipelineConfig`.

* В `infrastructure/config/loader._migrate_legacy_pipeline_config()` поддержать упаковку секции `output` (как сделано для `runtime/quality/...`).

**Фасад записи**

* Модифицировать `UnifiedOutputWriterImpl.__init__(..., converter: OutputFrameConverterABC | None = None)` и хранить `self._converter`.

* В `write_result()` (`src/bioetl/infrastructure/output/unified_output_writer_impl.py:71`):

  * Подготовка: `apply_column_order` (`column_order` из схемы) → стабильная сортировка.

  * Применить конвертер: `df_converted = self._converter.convert(df_prepared)` если задан.

  * Обновить порядок колонок: `column_order_to_write = list(df_converted.columns)` чтобы не «переписать» переименованные колонки во внутреннем `Writer` (`base_writer.py:44-55`).

  * Писать и строить QC/метаданные уже по `df_converted`.

**Реализация конвертеров**

* `NoopConverter`: возвращает `df` без изменений.

* `RenameColumnsConverter`: `df.rename(columns=lambda c: c.replace("_", "-").lower())`.

* `DropNaRowsConverter`: `df.dropna(how="all")` или по явному списку колонок (начать с `all`).

* Композиция `rename_and_dropna`: объект с `convert` последовательно применяет две операции.

**Валидация и детерминизм**

* Валидация Pandera остаётся на стадии `validate()`; конвертер не должен нарушать состав колонок, только их названия/порядок/NA‑строки. Для безопасности:

  * Обеспечить стабильный порядок: после конвертера использовать фактический порядок колонок `df_converted.columns`.

  * QC отчёты генерировать по уже конвертированному `df_converted`.

* При необходимости в дальнейшем добавить адаптер колонок для пост‑валидации (не входит в текущий объём).

**Тесты**

* Unit:

  * `RenameColumnsConverter` преобразует `snake_case → kebab-case` и сохраняет значения.

  * `DropNaRowsConverter` удаляет полностью пустые строки.

  * Композиция `rename_and_dropna` выполняет обе операции в корректном порядке.

* Интеграция: `UnifiedOutputWriterImpl.write_result()` пишет файл с переименованными колонками и стабильным порядком; QC строится на конвертированных колонках.

**Конфиг и пример**

* Поддержать в YAML:

  ```yaml
  output:
    converter: rename_and_dropna
  ```

* Значения: `noop | rename_columns | dropna | rename_and_dropna`.

**Обновления реестров**

* `abc_registry.yaml`: добавить `OutputFrameConverterABC: bioetl.domain.clients.base.output.contracts.OutputFrameConverterABC`.

* `abc_impls.yaml`: добавить default‑factory `bioetl.infrastructure.output.converters.factories.default_output_frame_converter`.

**Риски и совместимость**

* Изменение имён колонок может расходиться с Pandera‑схемой (snake\_case). В текущей реализации порядок колонок для записи берётся из конвертированного `df`, что исключает перезаполнение незаданных колонок. Валидация по схеме остаётся до конвертации.

* Backwards‑compatible: без `output.converter` поведение не меняется.

**Файлы для изменений**

* `src/bioetl/domain/clients/base/output/contracts.py` — добавить `OutputFrameConverterABC`.

* `src/bioetl/infrastructure/output/unified_output_writer_impl.py` — добавить поддержку конвертера.

* `src/bioetl/infrastructure/output/converters/*.py` — реализации и фабрика.

* `src/bioetl/interfaces/container_factory.py` — провязать конвертер из `PipelineConfig`.

* `src/bioetl/domain/configs/pipeline.py` — `OutputOptionsConfig` и поле `output`.

* `src/bioetl/infrastructure/config/loader.py` — миграция секции `output`.

* `src/bioetl/infrastructure/clients/base/abc_registry.yaml` и `abc_impls.yaml` — регистрировать роль/фабрику.

* Тесты в `tests/bioetl/infrastructure/output/` и обновление

