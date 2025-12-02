# Файловая политика

Этот документ фиксирует структуру репозитория и правила размещения файлов.

## Структура каталогов

Проект следует архитектурному паттерну Ports & Adapters (Hexagonal) + DDD.

```text
.
├── configs/                # Runtime конфигурации (YAML)
├── docs/                   # Документация
│   ├── application/        # Use Cases (описания пайплайнов)
│   ├── architecture/       # Архитектурные решения (ADR) и принципы
│   ├── domain/             # Бизнес-логика: Глоссарий, Схемы (Pandera)
│   ├── guides/             # Руководства (How-to)
│   ├── infrastructure/     # Адаптеры: Клиенты, Логирование, Config
│   ├── interfaces/         # Внешние интерфейсы: CLI
│   └── MAP.md              # Навигатор по проекту
├── src/                    # Исходный код
│   └── bioetl/             # Root package
│       ├── application/    # Implementation of Use Cases
│       ├── domain/         # Implementation of Domain Logic
│       ├── infrastructure/ # Implementation of Adapters
│       └── interfaces/     # Implementation of Ports (CLI/API)
└── tests/                  # Тесты (зеркалят структуру src/)
```

## Правила именования

1.  **Markdown файлы**:
    *   Используйте `kebab-case` (например, `system-design.md`).
    *   Для упорядочивания используйте префиксы `NN-` (например, `01-getting-started.md`).

2.  **Архитектурные решения (ADR)**:
    *   Размещаются в `docs/architecture/decisions/`.
    *   Формат: `NNNN-title-in-kebab-case.md`.

3.  **Пайплайны**:
    *   Документация: `docs/application/pipelines/<provider>/<entity>/`.
    *   Код: `src/bioetl/application/pipelines/<provider>/<entity>/`.

## Принципы "Docs-as-Code"

*   **Источники истины**:
    *   Схемы данных описываются в коде (`src/.../schemas`) и документируются в `docs/domain/schemas`.
    *   Пайплайны описываются в `docs/application/pipelines` и реализуются в `src`.
*   **Синхронизация**: Изменения в структуре `src/` должны отражаться в `docs/MAP.md`.

