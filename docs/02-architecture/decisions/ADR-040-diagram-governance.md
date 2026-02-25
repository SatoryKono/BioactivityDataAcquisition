# ADR-040: Diagram Governance and Layout Policy

## Status

Accepted

## Date

2026-02-25

## Context

BioETL содержит два каталога диаграмм:

- `docs/02-architecture/mmd-diagrams/` — канонические `.mmd` файлы.
- `docs/02-architecture/diagrams/mermaid/` — decomposed `.mermaid` views.

Существующая инфраструктура:

- Тема: `theme/mermaid-config.json` + `theme/custom.css`
- Render: `render.sh` (SVG + PNG)
- Lint: `scripts/lint_diagrams.py` (поддержка `.mmd` + `.mermaid`)

## Decision

### D1: Canonical Colour Scheme

Единая палитра фиксируется в `theme/custom.css`.
Все inline `style` в `.mermaid` и `.mmd` MUST использовать эту палитру.

### D2: Dual Repository Structure

- `.mmd` в `mmd-diagrams/` — каноническое расположение.
- `.mermaid` в `diagrams/mermaid/` — decomposed views.

### D3: View-based Decomposition Rules

- Hard limit: 20 узлов на view-файл.
- Soft limit: 15 узлов.
- Файлы >35 узлов = CRITICAL.

### D4: Metadata Formats

- `.mmd`: `@version`, `@date`, `@type`, `@level`, `@nodes`.
- `.mermaid`: `%% View: <type> | Parent: <file>`.

### D5: CI Validation

`scripts/lint_diagrams.py` проверяет оба каталога:

- SIZE-001/002: node limits
- META-001: metadata presence
- COLOUR-001: approved palette

Pre-commit hook: `lint-diagrams`.

### D6: Tool Selection Criteria

| Scope                 | Tool            |
| --------------------- | --------------- |
| ≤20 узлов             | Mermaid         |
| 20–40, complex layout | PlantUML        |
| >40                   | D2 (ELK layout) |

## Consequences

### Positive

- Единая палитра без визуальных конфликтов.
- CI предотвращает деградацию.

### Negative

- Два каталога + два расширения увеличивают когнитивную нагрузку.

### Risks

- linkStyle индексы хрупкие.
- Подсчёт узлов эвристический.

## Related ADRs

- ADR-005 (Composition Layer)
- ADR-020 (BasePipeline decomposition)
