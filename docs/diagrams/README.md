# BioETL Architecture Diagrams

*Версия: 1.1 | Дата: 2026-01-26*

Этот каталог содержит комплексную систему архитектурных диаграмм для проекта BioETL.

## Содержание

- **DIAGRAM_CATALOG.md** - Каталог из 500 предложенных диаграмм
- **TOP_50_DIAGRAMS.md** - Таблица 50 наиболее важных диаграмм с приоритетами
- **mermaid/** - 26 Mermaid диаграмм (`.mmd` files)
- **images/** - Отрендеренные PNG диаграммы (создаются при рендеринге)

## Структура Диаграмм

### TOP-26 Диаграммы (Priority ≥ 7.75)

| # | Файл | Название | Тип |
|---|------|----------|-----|
| 1 | `01_five_layer_architecture.mmd` | Five Layer Architecture | Component |
| 2 | `02_complete_pipeline_flow.mmd` | Complete Pipeline Flow | Flowchart |
| 3 | `03_hexagonal_architecture.mmd` | Hexagonal Architecture Overview | C4 Context |
| 4 | `04_layer_dependency_matrix.mmd` | Layer Dependency Matrix | Matrix |
| 5 | `05_medallion_architecture.mmd` | Medallion Architecture Overview | Flowchart |
| 6 | `06_domain_model_overview.mmd` | Domain Model Overview | Class Diagram |
| 7 | `07_ports_architecture.mmd` | Ports Architecture | Interface Diagram |
| 8 | `08_batch_processing_flow.mmd` | Batch Processing Flow | State Diagram |
| 9 | `09_ddd_aggregates.mmd` | DDD Aggregates | Class Diagram |
| 10 | `10_pipeline_core_components.mmd` | Pipeline Core Components | Component |
| 11 | `11_composition_root.mmd` | Composition Root | Flowchart |
| 12 | `12_error_classification.mmd` | Error Classification | Flowchart |
| 13 | `13_storage_architecture.mmd` | Storage Architecture | Component |
| 14 | `14_http_infrastructure.mmd` | HTTP Infrastructure | Component |
| 15 | `15_circuit_breaker_states.mmd` | Circuit Breaker States | State Diagram |
| 16 | `16_pipelinerun_aggregate.mmd` | PipelineRun Aggregate | Class Diagram |
| 17 | `17_retry_mechanism.mmd` | Retry Mechanism | Activity Diagram |
| 18 | `18_dq_check_flow.mmd` | DQ Check Flow | Sequence Diagram |
| 19 | `19_base_transformer_template_method.mmd` | BaseTransformer Template Method | Activity |
| 20 | `20_factory_pattern_usage.mmd` | Factory Pattern Usage | Class Diagram |
| 21 | `21_lock_acquisition_flow.mmd` | Lock Acquisition Flow | Sequence Diagram |
| 22 | `22_silver_merge_operation.mmd` | Silver Merge Operation | Flowchart |
| 23 | `23_provider_adapters_overview.mmd` | Provider Adapters Overview | Component |
| 24 | `24_graceful_shutdown.mmd` | Graceful Shutdown | Sequence Diagram |
| 25 | `25_pipeline_config_structure.mmd` | PipelineConfig Structure | Class Diagram |
| 26 | `26_composite_pipeline_workflow.mmd` | Composite Pipeline Workflow (ADR-026) | Flowchart |

## Рендеринг Диаграмм в PNG

### Опция 1: Mermaid CLI (Рекомендуется)

**Установка:**
```bash
npm install -g @mermaid-js/mermaid-cli
```

**Рендеринг всех диаграмм:**
```bash
cd docs/diagrams

# Создать директорию для PNG
mkdir -p images

# Рендерить все диаграммы с высоким разрешением (300 DPI)
for file in mermaid/*.mmd; do
    filename=$(basename "$file" .mmd)
    mmdc -i "$file" \
         -o "images/${filename}.png" \
         -w 2400 \
         -H 1800 \
         -s 3 \
         -b transparent
done
```

**Параметры:**
- `-w 2400` - Ширина 2400px
- `-H 1800` - Высота 1800px
- `-s 3` - Масштаб 3x (эквивалент 300 DPI для печати)
- `-b transparent` - Прозрачный фон

### Опция 2: Mermaid CLI с конфигурацией для больших диаграмм

Создайте файл `puppeteer-config.json`:

```json
{
  "args": ["--no-sandbox", "--disable-setuid-sandbox"],
  "defaultViewport": {
    "width": 3200,
    "height": 2400
  }
}
```

Рендеринг с конфигурацией:

```bash
mmdc -i mermaid/01_five_layer_architecture.mmd \
     -o images/01_five_layer_architecture.png \
     -p puppeteer-config.json \
     -s 3 \
     -b white
```

### Опция 3: Docker с Mermaid CLI

Если не хотите устанавливать Node.js локально:

```bash
docker run --rm -v $(pwd):/data minlag/mermaid-cli \
    -i /data/mermaid/01_five_layer_architecture.mmd \
    -o /data/images/01_five_layer_architecture.png \
    -w 2400 \
    -H 1800 \
    -s 3
```

### Опция 4: Онлайн рендеринг (для быстрого просмотра)

1. Откройте https://mermaid.live/
2. Скопируйте содержимое `.mmd` файла
3. Вставьте в редактор
4. Экспортируйте как PNG/SVG

### Опция 5: VS Code Extension

1. Установите расширение "Markdown Preview Mermaid Support"
2. Откройте `.mmd` файл
3. Используйте "Export to PNG" из контекстного меню

## Скрипт Автоматического Рендеринга

Создайте файл `render_diagrams.sh`:

```bash
#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MERMAID_DIR="$SCRIPT_DIR/mermaid"
IMAGES_DIR="$SCRIPT_DIR/images"

# Создать директорию для PNG
mkdir -p "$IMAGES_DIR"

# Проверить наличие mmdc
if ! command -v mmdc &> /dev/null; then
    echo "Error: mermaid-cli (mmdc) не установлен"
    echo "Установите: npm install -g @mermaid-js/mermaid-cli"
    exit 1
fi

echo "Рендеринг Mermaid диаграмм в PNG..."

# Рендерить каждую диаграмму
for file in "$MERMAID_DIR"/*.mmd; do
    if [ -f "$file" ]; then
        filename=$(basename "$file" .mmd)
        output="$IMAGES_DIR/${filename}.png"

        echo "Рендеринг: $filename"

        mmdc -i "$file" \
             -o "$output" \
             -w 2400 \
             -H 1800 \
             -s 3 \
             -b transparent

        # Проверить, что файл создан
        if [ -f "$output" ]; then
            size=$(du -h "$output" | cut -f1)
            echo "  ✓ Создан: $output ($size)"
        else
            echo "  ✗ Ошибка рендеринга: $filename"
        fi
    fi
done

echo ""
echo "Рендеринг завершён!"
echo "PNG файлы находятся в: $IMAGES_DIR"
```

Запуск:

```bash
chmod +x docs/diagrams/render_diagrams.sh
./docs/diagrams/render_diagrams.sh
```

## Интеграция в Документацию

### Создание Markdown документа с диаграммами

Создайте `docs/02-architecture/ARCHITECTURE_DIAGRAMS.md`:

```markdown
# Architecture Diagrams

## 1. Five Layer Architecture

![Five Layer Architecture](../diagrams/images/01_five_layer_architecture.png)

**Описание:** Полная архитектура проекта с пятью слоями: Domain, Application, Composition, Infrastructure, Interfaces.

**Ключевые компоненты:**
- Domain: Чистая бизнес-логика, 26 портов, 3 DDD aggregates
- Application: PipelineRunner, BatchExecutor, RecordProcessor
- Composition: Dependency Injection, Factories, Bootstrap
- Infrastructure: Adapters для 7 провайдеров, Storage writers
- Interfaces: CLI commands

---

## 2. Complete Pipeline Flow

![Complete Pipeline Flow](../diagrams/images/02_complete_pipeline_flow.png)

**Описание:** End-to-end поток данных от API провайдера до Gold layer.

**Этапы:**
1. Preflight checks
2. Lock acquisition
3. Fetch batch
4. Transform (Bronze → Silver)
5. Write Silver (Delta merge)
6. Write Gold (Validated)
7. Postrun DQ analysis
8. VACUUM cleanup

---

... (continue for all 25 diagrams)
```

### Добавление диаграмм в README.md

Обновите `README.md` в корне проекта:

```markdown
## Architecture

BioETL следует Hexagonal Architecture (Ports & Adapters) с Medallion подходом для data pipeline.

![Architecture Overview](docs/diagrams/images/01_five_layer_architecture.png)

Подробная документация:
- [Architecture Diagrams](docs/02-architecture/ARCHITECTURE_DIAGRAMS.md) - 25 ключевых диаграмм
- [Diagram Catalog](docs/diagrams/DIAGRAM_CATALOG.md) - Полный каталог 500 диаграмм
- [ADR](docs/02-architecture/decisions/) - 27 Architecture Decision Records
```

## Использование в Презентациях

PNG диаграммы можно импортировать в:
- PowerPoint / Google Slides
- Confluence
- Notion
- Markdown документы
- Wiki

Рекомендуемое разрешение для печати: **300 DPI** (scale=3 в mmdc)

## Редактирование Диаграмм

1. Откройте `.mmd` файл в текстовом редакторе
2. Внесите изменения в Mermaid синтаксис
3. Проверьте на https://mermaid.live/
4. Сохраните файл
5. Перерендерите PNG: `mmdc -i file.mmd -o file.png -s 3`

## Mermaid Синтаксис

Документация: https://mermaid.js.org/intro/

**Типы диаграмм:**
- `flowchart` - Flowchart / Data Flow
- `classDiagram` - Class Diagram (UML)
- `sequenceDiagram` - Sequence Diagram (UML)
- `stateDiagram-v2` - State Diagram
- `graph TB/LR` - Component Diagram

## Проблемы и Решения

### Диаграмма слишком большая

Увеличьте размер canvas:

```bash
mmdc -i file.mmd -o file.png -w 3200 -H 2400 -s 3
```

### Текст нечитаемый

Увеличьте размер шрифта в диаграмме:

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'fontSize':'18px'}}}%%
```

### Прозрачный фон не работает

Используйте белый фон для печати:

```bash
mmdc -i file.mmd -o file.png -s 3 -b white
```

## Лицензия

Диаграммы являются частью проекта BioETL и распространяются под той же лицензией.

---

*Создано автоматически Claude Code 2026-01-20*
