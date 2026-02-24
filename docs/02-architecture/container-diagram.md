# C4: Диаграмма Контейнеров

Эта диаграмма детализирует "Систему BioETL", представленную на диаграмме контекста. Она показывает основные контейнеры (приложения и хранилища данных), которые составляют систему BioETL, и их взаимодействие.

```mermaid
flowchart TB
    engineer["Инженер-программист<br/>CLI (bioetl run)"]
    analyst["Аналитик данных"]
    external_apis["Внешние научные API<br/>ChEMBL, PubChem, UniProt и др."]

    subgraph bioetl_system["Система BioETL (локальный процесс)"]
        pipeline_runner["PipelineRunner<br/>Application Layer"]
        storage_port["StoragePort<br/>(Domain Port)"]
        lock_port["LockPort<br/>(Domain Port)"]
        writers["BronzeWriter / SilverWriter / GoldWriter<br/>(StoragePort impl)"]
        memory_lock["MemoryLock<br/>(LockPort impl)"]
        local_fs["Локальная файловая система<br/>data/ (bronze/silver/gold, checkpoints)"]
    end

    engineer -->|"Запускает пайплайны"| pipeline_runner
    pipeline_runner -->|"Запрашивает данные"| external_apis
    pipeline_runner -->|"Пишет через порт"| storage_port
    storage_port --> writers
    writers -->|"Чтение/запись"| local_fs
    pipeline_runner -->|"Блокировки"| lock_port
    lock_port --> memory_lock
    analyst -->|"Читает локальные данные"| local_fs
```

## Компоненты

*   **PipelineRunner (Application Layer)**: Локальный процесс, который оркестрирует пайплайны и вызывает порты для источников данных, хранения и блокировок.
*   **StoragePort**: Доменный порт, через который `PipelineRunner` записывает данные в Bronze/Silver/Gold уровни.
*   **BronzeWriter / SilverWriter / GoldWriter**: Реализации `StoragePort`, которые пишут данные в локальную файловую систему `data/`.
*   **LockPort / MemoryLock**: Локальный механизм блокировок, реализующий `LockPort` в рамках single-instance выполнения (ADR-010).
*   **Локальная файловая система (`data/`)**: Хранилище Bronze/Silver/Gold и checkpoints в рамках Local-Only развертывания.
