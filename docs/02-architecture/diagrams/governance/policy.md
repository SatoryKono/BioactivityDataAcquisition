______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# POL-LLM-DIAGRAMS-001

Политика генерации и сопровождения диаграмм проекта BioETL.

## 1. Назначение

Этот документ задаёт обязательные правила для диаграмм как инженерных артефактов:

- архитектурная корректность;
- воспроизводимый рендер;
- единый визуальный стандарт;
- синхронизация с кодовой базой.

## 2. Источник истины и каталоги

1. Канонический policy: `docs/02-architecture/diagrams/governance/policy.md`.
1. Исторический policy (контекст): `docs/02-architecture/diagrams/governance/00-diagramming-policy.md`.
1. Канонические исходники диаграмм: `docs/02-architecture/diagrams/**/*.mmd`.
1. Decomposed views: `docs/02-architecture/diagrams/views/*.mermaid`.
1. Рендер-артефакты: `svg/png` под sibling-каталогами `diagrams/**/svg` и `diagrams/**/png` считаются поддерживаемыми documentation outputs и регенерируются через `render.sh` после изменения источников.

## 3. Форматы и именование

1. Обязательный формат для новых диаграмм: Mermaid (`.mmd`).
1. Расширение `.mermaid` допускается для decomposed views (`diagrams/views/`) и legacy-набора.
1. Именование: `NN-topic-name.mmd` (порядковый номер + kebab-case).
1. Одна диаграмма = один файл = одна основная архитектурная идея.

## 4. Архитектурные ограничения

1. Диаграммы обязаны отражать Hexagonal + DDD + Medallion архитектуру.
1. Запрещено показывать зависимости `domain -> infrastructure`.
1. Для application-вызовов infrastructure отображать контракт через port/protocol.
1. В domain-диаграммах запрещён I/O контент.
1. Наименования сущностей/интерфейсов должны соответствовать RULES.md.

## 5. Типы диаграмм

Разрешены:

1. Architecture / C4 (context, container, component).
1. Pipeline/Dataflow (DAG, Medallion flow).
1. Class/Protocol maps.
1. Sequence (retry, rate-limit, circuit breaker, lock/checkpoint).
1. State/ER/Mindmap при обоснованной пользе.

## 6. Визуальный стандарт

### 6.1 Палитра слоёв (muted)

| Layer          | Fill      | Stroke    |
| -------------- | --------- | --------- |
| Domain         | `#F5F3FF` | `#7C3AED` |
| Application    | `#F0FDF4` | `#16A34A` |
| Infrastructure | `#FFF1F2` | `#DC2626` |
| Composition    | `#FFF7ED` | `#F59E0B` |
| Interfaces     | `#EFF6FF` | `#2563EB` |
| External       | `#F1F5F9` | `#64748B` |

### 6.2 Medallion palette

| Layer      | Fill      | Stroke    |
| ---------- | --------- | --------- |
| Bronze     | `#FFF7ED` | `#F59E0B` |
| Silver     | `#F8FAFC` | `#475569` |
| Gold       | `#FEFCE8` | `#CA8A04` |
| Quarantine | `#FFE4E6` | `#E11D48` |

### 6.3 Линии и семантика

1. Data flow: сплошная линия.
1. DI/implements: пунктир.
1. Error/quarantine path: красный пунктир.
1. Observability path: нейтральный серый.
1. Непрозрачные/случайные цвета вне палитры запрещены.

### 6.4 Layout engine (ELK)

Для flowchart по умолчанию используется ELK с профилем:

```mermaid
%%{init: {
%%  'layout': 'elk',
%%  'theme': 'base',
%%  'themeVariables': { 'fontFamily': 'Inter, Roboto, sans-serif' },
%%  'elk': {
%%    'mergeEdges': true,
%%    'nodePlacementStrategy': 'BRANDES_KOEPF',
%%    'cycleBreakingStrategy': 'GREEDY',
%%    'direction': 'RIGHT',
%%    'spacing.nodeNode': 40,
%%    'spacing.edgeNode': 30,
%%    'spacing.edgeEdge': 20,
%%    'edgeRouting': 'ORTHOGONAL'
%%  }
%%}}%%
```

Примечание: `ORTHOGONAL` считается каноническим значением. Для очень плотных
схем допускается локальное переопределение `edgeRouting`, но это должно быть
осознанным исключением, а не базовым профилем.

## 7. Definition of Done для диаграммы

Диаграмма считается готовой, если одновременно выполнено:

1. Есть исходник в каноническом каталоге (`.mmd`).
1. Есть соответствующий обновлённый рендер: `svg` как обязательный publication artifact и `png` там, где он ещё нужен как compatibility/export surface.
1. Есть запись в индексной странице/разделе документации.
1. Ссылка на диаграмму не битая.
1. `scripts/diagrams/lint_diagrams.py` не даёт ошибок.

## 8. Обязательные проверки

```bash
uv run python -m scripts.diagrams lint docs
uv run python -m scripts.docs check-links --links
uv run python -m scripts.diagrams check-artifacts --manifest docs/02-architecture/diagrams/manifests/visual-smoke.txt
uv run python -m scripts.diagrams check-visual-smoke
bash scripts/diagrams/validate_mermaid_syntax.sh
```

Если runtime для `validate_mermaid_syntax.sh` не готов, это фиксируется как открытый риск до устранения.
Поддерживаемые remediation paths: локальный `chrome-headless-shell`, явный `PUPPETEER_EXECUTABLE_PATH`,
или Docker fallback с host-mounted `PUPPETEER_CACHE_DIR`.

`uniform_diagram_sizes.py` использовать только точечно и только после ручной проверки,
так как режим с `&nbsp;` конфликтует с правилом `NBSP-001` в `lint_diagrams.py`.

## 9. Синхронизация с кодом

1. Любое изменение архитектурных модулей или порт-контрактов требует обновления релевантных диаграмм.
1. Изменение диаграммы без изменения кода допускается только для устранения рассинхрона или улучшения читаемости.
1. Сначала документируем фактическую реализацию, затем желаемую (если есть расхождение).
