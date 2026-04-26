# BioETL Diagram Docs Orchestrator Agent

*Статус: internal-published (Internal / Extended)*

Специализированный агент для обновления Mermaid-диаграмм и пересборки связанных артефактов документации (`svg/png`, `docx`, `pdf`).

## Цель

Обеспечить воспроизводимый pipeline:

1. Проверка диаграммных quality gates.
1. Рендер диаграмм.
1. Обновление `*-with-descriptions.docx` и `*-with-descriptions.pdf`.

## Канонические инструменты агента

1. `docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-1.sh` — единый quality gate (lint/syntax/render/smoke/quality).
1. `docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-2.py` — генерация DOCX из `*-with-descriptions.md`.
1. `docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-3.py` — генерация PDF из `*-with-descriptions.md`.
1. `docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-4.sh` — единый orchestrator для полного цикла.

## Базовые команды

```bash
# Полный цикл (checks + docx + pdf)
bash docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-4.sh

# Полный цикл для одной диаграммы
bash docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-4.sh \
  --diagram docs/02-architecture/diagrams/foundation/30-port-adapter-mapping.mmd

# Только пересборка бандлов без checks
bash docs/00-project/ai/agents/scripts/diagrams/py-doc-bot-4.sh --skip-checks
```

## Режимы

| Режим     | Описание                    |
| --------- | --------------------------- |
| `CHECK`   | Только `py-doc-bot-1.sh`    |
| `BUNDLES` | Только `docx/pdf` генерация |
| `FULL`    | Checks + bundles            |

## Инварианты

1. Использовать orchestrator и канонические скрипты из `docs/00-project/ai/agents/scripts/diagrams/`; путь `scripts/diagrams/` сохраняется как compatibility-слой.
1. Следовать ADR-040 (diagram governance).
1. При ошибках окружения (`pandoc`, `wkhtmltopdf`, `mmdc`) завершать с явным сообщением.
1. Не менять зоны вне диаграммного контура без явного запроса.

## Ожидаемые артефакты

- Обновлённые `svg/png` рендеры диаграмм (при необходимости).
- Обновлённые:
  - `docs/02-architecture/diagrams/bundles/class.bundle.docx`
  - `docs/02-architecture/diagrams/bundles/foundation.bundle.docx`
  - `docs/02-architecture/diagrams/bundles/class.bundle.pdf`
  - `docs/02-architecture/diagrams/bundles/foundation.bundle.pdf`

Примечание: пересборка выполняется для Markdown-бандлов, доступных как источники `*-with-descriptions.md`.
