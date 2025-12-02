# 00 Pipeline Output Service

## Описание

`PipelineOutputService` — сервис верхнего уровня для записи результатов пайплайна. Получает на вход DataFrame и артефакты, находит настроенный writer в конфигурации и вызывает его для атомарной записи датасета. После успешной записи генерирует QC-метрики (при помощи `emit_qc_artifact`). Используется в `ChemblAssayPipeline` для сохранения с использованием унифицированного writer или отката к `ChemblWriteService`.

## Модуль

`src/bioetl/core/io/output_service.py`

## Основные методы

### `__init__(self, config: Mapping[str, Any] | None = None, logger: UnifiedLogger | None = None)`

Инициализирует сервис вывода с конфигурацией и логгером.

**Параметры:**
- `config` — конфигурация пайплайна (опционально)
- `logger` — логгер для записи событий (опционально)

### `resolve_writer(self, output_dir: Path) -> UnifiedOutputWriter | None`

По переданному каталогу пытается получить объект writer из конфигурации (например, заранее сконфигурированный `ArtifactWriter`), устанавливает для него выходной каталог.

**Параметры:**
- `output_dir` — директория вывода

**Процесс:**
1. Поиск настроенного writer в конфигурации
2. Установка выходного каталога для writer
3. Возврат writer или `None`, если не найден

**Возвращает:** настроенный writer или `None`, если writer не найден в конфигурации.

### `save(self, df: pd.DataFrame, artifacts: WriteArtifacts, output_dir: Path, format: str = "csv") -> WriteResult`

Сохраняет DataFrame, используя настроенный writer: либо через метод `write_dataset_atomic`, либо `write`, в зависимости от доступности, затем ловит исключения и логирует их; после успешной записи пытается сгенерировать QC-отчёт (`emit_qc_artifact`).

**Параметры:**
- `df` — DataFrame для сохранения
- `artifacts` — объект `WriteArtifacts` с путями к артефактам
- `output_dir` — директория вывода
- `format` — формат данных (по умолчанию "csv")

**Процесс:**
1. Разрешение writer из конфигурации через `resolve_writer`
2. Атомарная запись данных через `write_dataset_atomic` (если доступно) или стандартная через `write`
3. Обработка исключений (логирование и пробрасывание)
4. Генерация QC-артефактов через `emit_qc_artifact` после успешной записи

**Возвращает:** `WriteResult` с информацией о записанных файлах.

## Использование

Сервис используется пайплайнами для сохранения результатов в различные хранилища:

- Локальные файлы (CSV, Parquet)
- Внешние хранилища (S3, GCS)
- Базы данных

## Related Components

- **UnifiedOutputWriter**: унифицированный writer для записи (см. `docs/02-pipelines/core/04-unified-output-writer.md`)
- **ChemblDocumentPipeline**: может использовать сервис для сохранения результатов (см. `docs/02-pipelines/chembl/document/00-document-chembl-overview.md`)

