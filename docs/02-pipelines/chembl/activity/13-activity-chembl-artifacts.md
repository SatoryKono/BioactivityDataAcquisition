# 13 Activity ChEMBL Artifacts

## Описание

Документ описывает компоненты, отвечающие за планирование и сохранение артефактов пайплайна ChEMBL Activity: `ActivityArtifactPlanner` и `ActivityWriteService`.

## ActivityArtifactPlanner

### Описание

`ActivityArtifactPlanner` — специализированный планировщик артефактов для пайплайна активности. Определяет, как будут именоваться и размещаться файлы вывода. В реализации для активности формирует поддиректорию с именем, основанным на `run_tag` и `mode`, и внутри неё задаёт имя файла данных формата `activity_<run_stem>.csv` для основного датасета.

### Модуль

`bioetl/pipelines/chembl/activity/run.py`

### Основной метод

#### `plan(self, output_dir: Path, pipeline_code: str, run_tag: str | None, mode: str | None) -> tuple[Path, WriteArtifacts]`

Переопределяет абстрактный метод базового класса `ArtifactPlanner`.

**Параметры:**
- `output_dir` — базовая директория вывода
- `pipeline_code` — код пайплайна
- `run_tag` — тег запуска
- `mode` — режим выполнения

**Процесс планирования:**

1. Создание целевой директории: формирование поддиректории `<output_dir>/<run_stem>` на основе `run_tag` и `mode`
2. Формирование путей: создание объекта `WriteArtifacts` с путём для будущего CSV-файла
3. Возврат результатов: возврат пути к директории и объекта `WriteArtifacts`

**Возвращает:** кортеж из пути к директории и объекта `WriteArtifacts`.

## ActivityWriteService

### Описание

`ActivityWriteService` — специализированный сервис записи результатов для пайплайна активности. Инкапсулирует `ActivityWriter` и предоставляет метод `save()`, соответствующий интерфейсу `WriteService`. В контексте данного пайплайна используется для сохранения данных через `ActivityWriter` с учётом особенностей именования выходных файлов (префикс `activity_` и т.д.).

### Модуль

`bioetl/pipelines/chembl/activity/run.py`

### Основной метод

#### `save(self, df: pd.DataFrame, artifacts: WriteArtifacts, options: StageExecutionOptions, *, context: StageContextProtocol, runtime: StageRuntimeContext) -> WriteResult`

Переопределяет метод базового класса `WriteService`.

**Параметры:**
- `df` — DataFrame с данными для сохранения
- `artifacts` — объект `WriteArtifacts` с путями к артефактам
- `options` — опции выполнения стадии
- `context` — контекст выполнения стадии
- `runtime` — контекст времени выполнения

**Процесс сохранения:**

1. Определение директории вывода: извлечение пути из контекста
2. Формирование имени файла: создание имени по шаблону `activity_<run_stem>.csv` при необходимости
3. Вызов writer: использование `self.writer.write(...)` для непосредственной записи
4. Возврат результата: возврат `WriteResult` с информацией о записанных файлах

**Возвращает:** `WriteResult` с метриками записи.

## Related Components

- **ActivityWriter**: стадия записи результатов (см. `docs/02-pipelines/chembl/activity/03-activity-chembl-write.md`)
- **UnifiedOutputWriter**: унифицированный writer для записи (см. `docs/02-pipelines/04-unified-output-writer.md`)

