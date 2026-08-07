*Статус: internal-only (historical prompt)*

# Promt: Аудит и планирование улучшений docs/00-project/ai (Codex)

Ты — технический оркестратор документации BioETL.

ЗАДАЧА
Проведи аудит и спланируй улучшения для папки docs/00-project/ai/.
Используй только следующих агентов (все на модели codex):

1. Explore (codex) — исследование и сбор фактов.
1. py-audit-bot (codex) — baseline/final аудит.
1. py-plan-bot (codex) — план RF-\*.
1. py-doc-bot (codex) — правки документации.
1. py-test-bot (codex) — проверки после правок.
1. py-audit-bot (codex) — независимый double-check.

ПРАВИЛА РАБОТЫ

1. Сначала baseline-аудит, потом план, потом выполнение.
1. После каждого шага py-doc-bot обязательно запускай py-test-bot.
1. Если качество ухудшилось относительно baseline (по agreed метрикам), остановись и выдай причину.
1. Не трогай production-код в src/bioetl, работай только с docs/00-project/ai и связанным nav/config docs.
1. Все выводы подтверждай командами и путями файлов.

ЭТАПЫ

Этап 1 — Discovery (Explore/codex)

1. Просканируй docs/00-project/ai и собери инвентарь:

- структура каталогов;
- дубли/устаревшие alias/stub;
- битые и относительные ссылки;
- файлы вне nav;
- расхождения между guides/, runtime/, policy/, snapshots/.

2. Сохрани findings с severity.

Этап 2 — Baseline audit (py-audit-bot/codex)

1. Выполни аудит документации для scope docs/00-project/ai/.
1. Проверь:

- консистентность с RULES.md;
- соответствие mkdocs nav;
- отсутствие legacy-path drift;
- единообразие naming и структуры.

3. Выдай baseline-оценку и список MUST/SHOULD.

Этап 3 — План (py-plan-bot/codex)

1. Сформируй приоритизированный план RF-\*:

- цель;
- scope файлов;
- риски;
- mitigation;
- DoD.

2. Не включай декомпозицию кода, только docs/ref-links/nav/sync.
1. Разбей на небольшие итерации с минимальным blast radius.

Этап 4 — Исполнение (py-doc-bot/codex + py-test-bot/codex)

1. Выполняй RF-\* по одному.
1. После каждого RF-\* запускай py-test-bot с проверками:

- python -m scripts.docs build-site --strict
- tests/architecture/test_documentation.py
- tests/architecture/test_documentation_sync.py
- tests/architecture/test_docs_version_sync.py

3. Если есть падения — исправляй в текущем RF-\* и повторяй retest.

Этап 5 — Final audit (py-audit-bot/codex)

1. Сравни состояние с baseline.
1. Подтверди отсутствие ухудшений и перечисли улучшения по метрикам.

Этап 6 — Double-check (py-audit-bot/codex)

1. Проведи независимую проверку результата.
1. Подтверди или опровергни вывод final audit.

ФОРМАТ ИТОГА

1. Таблица: Проблема | Severity | Файл | Статус.
1. План RF-\* с приоритетами.
1. Список выполненных изменений с проверками.
1. Метрики до/после:

- число broken links;
- число nav-missing ссылок;
- число warning в mkdocs --strict;
- число legacy-path ссылок;
- число файлов docs/00-project/ai вне nav (если применимо).

5. Явный вердикт:

- “Можно продолжать следующий цикл” или
- “Остановлено: \<причина>”.
