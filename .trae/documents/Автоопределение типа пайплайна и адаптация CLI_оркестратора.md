**Цели**

* Автоопределять `PipelineType` (`extract`, `full`, `transform`) по заполненности стадий.

* Оркестратор пропускает неактивные стадии и хуки вызываются только для активных.

* CLI поддерживает частичный запуск и учитывает авто‑тип.

**Модель и определение типа**

* Добавить `PipelineType(str, Enum)` в `src/bioetl/domain/pipelines/types.py`.

* В `PipelineConfig` добавить:

  * свойство `pipeline_type: PipelineType` и метод `detect_pipeline_type()`.

  * Логика:

    * `extract_active`: если задан `input_mode`/`input_path`, есть `provider_config`, или в контейнере присутствует `ExtractorABC`.

    * `transform_active`: если задан `_transformer` в контейнере либо включены нормализация/хеши (секции `quality.normalization`/`quality.hashing` по умолчанию активны → трактуем как активную стадию). Разрешить явное отключение через `pipeline.transform: false`.

    * `load_active`: если не `dry_run` и задан `output_path`.

    * Итог: `EXTRACT_ONLY` (extract\_active and not transform\_active and not load\_active), `TRANSFORM_ONLY` (transform\_active and not extract\_active), иначе `FULL`.

  * Поддержать явные флаги в `PipelineConfig.pipeline`: `{"extract": bool, "transform": bool, "load": bool}`; если они заданы, приоритет над автоопределением.

**Оркестратор**

* В `src/bioetl/application/orchestrator.py`:

  * Определить активные стадии: `active = {"extract","transform","validate","write"}` → фильтровать по типу:

    * `EXTRACT_ONLY`: только `extract`, без `transform/validate/write`.

    * `TRANSFORM_ONLY`: только `transform` (ожидает входной `DataFrame` из CLI/файла), без `extract/validate/write`.

    * `FULL`: стандартный порядок.

  * Передавать в пайплайн список активных стадий.

**Пайплайн**

* В `src/bioetl/application/pipelines/base.py`:

  * `run(output_path, *, dry_run=False, stages: set[str] | None = None, **kwargs)`.

  * Пропускать стадии, если их нет в `stages`.

  * `StageRuntimeManagerImpl.notify_stage_start/end` вызывать только для выполняемых стадий.

**CLI**

* В `src/bioetl/interfaces/cli/app.py`:

  * Расширить команду `run` параметром `type` (`extract|transform|full`).

  * Если не задан, использовать `config.pipeline_type`.

  * Для `transform` принимать источник `--input-path` или загрузку `DataFrame` из CSV согласно `input_mode`.

**Совместимость**

* Поведение по умолчанию — `FULL`.

* Существующие пайплайны не меняются; новые параметры необязательны.

**Файлы**

* `src/bioetl/domain/pipelines/types.py` — Enum.

* `src/bioetl/domain/configs/pipeline.py` — `pipeline_type` + автоопределение + флаги `pipeline.extract/transform/load` (опционально).

* `src/bioetl/application/orchestrator.py` — выбор стадий.

* `src/bioetl/application/pipelines/base.py` — `stages` в `run()` и пропуски.

* `src/bioetl/interfaces/cli/app.py` — опция `type` и проксирование.

**Тесты**

* Архитектурные: проверка корректности Enum/свойства.

* Unit: `PipelineConfig.detect_pipeline_type()` на кейсах (явные флаги, автоопределение).

* Интеграция: оркестратор с `EXTRACT_ONLY`/`TRANSFORM_ONLY` пропускает стадии и хуки.

* CLI: `run extract|transform|full` вызывает ожидаемые стадии.

