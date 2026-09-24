# diagrams

- prompt: `prompt.audit.diagrams`
- surface_score: **2**
- proven: 5; P0/P1: 1
- run_id: `20260924T183653Z-9d9d303fa3f6-e28b4aa3`

Инвентарь checkout: 328 `.mmd` (с `_template.mmd`), 165 `.mermaid`, 492 tracked SVG, 0 PNG (gitignore DOC-GOV-02). Парность source↔svg полная, binary-only нет. Рендер — `tooling/render.sh` и `scripts/diagrams/mmdc_wrapper.sh`, pin `@mermaid-js/mermaid-cli@10.6.1`; `npx -y` в render/CI нет. CI валидирует синтаксис и lint при изменении диаграмм; полный render и nightly phase2 выключены. Drift-gate проверяет co-change имени SVG и не покрывает providers/sequence/state-machines. Deploy-diagram local-only не противоречит политике. Модель провайдеров местами неверна: ChEMBL (API key, cursor/scroll) и шаблон «pagination cursor» у offset-адаптеров.

## Findings

- **DIAG-001** P1 PROVEN `docs/02-architecture/diagrams/providers/chembl/01-api-integration-flow.mmd:14` — ChEMBL integration diagram ветвится по API key и по cursor/offset/scroll, тогда как адаптер собирает только offset/limit и ChEMBL нет в PROVIDER_AUTH_REQUIREMENTS.
- **DIAG-002** P2 PROVEN `docs/02-architecture/diagrams/providers/semanticscholar/01-api-integration-flow.mmd:20` — Клон provider flow помечает пагинацию как cursor у Semantic Scholar, PubMed и PubChem, хотя runtime — offset или offset не используется.
- **DIAG-003** P2 PROVEN `.github/workflows/docs.yml:496` — PR drift-gate смотрит только плоские globs architecture/foundation/class-diagrams `*.mmd` и views `*.mermaid` и пропускает 28 вложенных providers, 5 sequence и 5 state-machines.
- **DIAG-004** P2 PROVEN `.github/workflows/docs.yml:384` — Полный render и visual/quality gates лежат в job с `if: false`; drift-gate сравнивает только имя SVG в diff, без повторного рендера.
- **DIAG-005** P3 PROVEN `docs/02-architecture/diagrams/providers/uniprot/01-api-integration-flow.mmd:35` — classDef composition использует stroke `#ea580c`, которого нет в канонической палитре ADR-040, и COLOUR-001 его не ловит.

## Remediations

- Привести chembl/01-api-integration-flow.mmd к offset/limit без ветки API key и обновить SVG.
- Исправить подпись пагинации в semanticscholar, pubmed и pubchem 01-api-integration-flow.mmd.
- Включить providers, sequence и state-machines в check-diagram-drift.
- Сверять изменённые source pinned-рендером, а не только фактом co-change SVG.
- Заменить #ea580c на #f59e0b и запретить hex вне CANONICAL_PALETTE.
