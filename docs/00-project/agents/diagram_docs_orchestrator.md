# BioETL Diagram Docs Orchestrator Agent

Специализированный агент для обновления Mermaid-диаграмм и пересборки связанных артефактов документации (`svg/png`, `docx`, `pdf`).

## Цель

Обеспечить воспроизводимый pipeline:
1. Проверка диаграммных quality gates.
2. Рендер диаграмм.
3. Обновление `*-with-descriptions.docx` и `*-with-descriptions.pdf`.

## Канонические инструменты агента (`scripts/diagrams/*`)

1. `run_diagram_checks.sh` — единый quality gate (lint/syntax/render/smoke/quality).
2. `generate_with_descriptions_docx.py` — генерация DOCX из `*-with-descriptions.md`.
3. `generate_with_descriptions_pdf.py` — генерация PDF из `*-with-descriptions.md`.
4. `run_diagram_docs_agent.sh` — единый orchestrator для полного цикла.

## Базовые команды

```bash
# Полный цикл (checks + docx + pdf)
bash scripts/diagrams/run_diagram_docs_agent.sh

# Полный цикл для одной диаграммы
bash scripts/diagrams/run_diagram_docs_agent.sh \
  --diagram docs/02-architecture/mmd-diagrams/foundation/30-port-adapter-mapping.mmd

# Только пересборка бандлов без checks
bash scripts/diagrams/run_diagram_docs_agent.sh --skip-checks
```

## Режимы

| Режим | Описание |
|---|---|
| `CHECK` | Только `run_diagram_checks.sh` |
| `BUNDLES` | Только `docx/pdf` генерация |
| `FULL` | Checks + bundles |

## Инварианты

1. Использовать только канонические скрипты из `scripts/diagrams/`.
2. Следовать ADR-040 (diagram governance).
3. При ошибках окружения (`pandoc`, `wkhtmltopdf`, `mmdc`) завершать с явным сообщением.
4. Не менять зоны вне диаграммного контура без явного запроса.

## Ожидаемые артефакты

- Обновлённые `svg/png` рендеры диаграмм (при необходимости).
- Обновлённые:
  - `docs/02-architecture/mmd-diagrams/class-diagrams-with-descriptions.docx`
  - `docs/02-architecture/mmd-diagrams/foundation-diagrams-with-descriptions.docx`
  - `docs/02-architecture/mmd-diagrams/class-diagrams-with-descriptions.pdf`
  - `docs/02-architecture/mmd-diagrams/foundation-diagrams-with-descriptions.pdf`

Примечание: пересборка выполняется для Markdown-бандлов, доступных как источники `*-with-descriptions.md`.
