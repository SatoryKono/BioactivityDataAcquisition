______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# CLI / Interface Layer

- Исходная диаграмма: `architecture/14-cli-interface-layer.mmd`

## Описание

Диаграмма CLI / Interface Layer показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. В исходном файле прямо зафиксирован контекст: Shows CLI commands, their routing, and interaction with composition. Диаграмму следует читать как обзорный routing view: она показывает, как семейства CLI-команд и entrypoints передают управление в composition/bootstrap слой, но не служит исчерпывающим каталогом всех support-модулей внутри `interfaces.cli`.

Ключевые контейнеры и семейства на схеме: `CLI Interface (Click)`, `Run Commands`, `Health Commands`, `Data Commands`, а также основной маршрут от пользователя и терминала к конкретным command handlers и bootstrap entrypoints. В текущей кодовой базе этот срез полезен прежде всего для проверки границ между `interfaces`, `composition` и runtime assembly, а также для контроля того, что рост CLI surface не размывает routing contracts.

Оценка плотности `@nodes=24` полезна для контроля читаемости и стабильного рендеринга, но не должна интерпретироваться как точный инвентарь текущей command/support surface.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-03-20`
