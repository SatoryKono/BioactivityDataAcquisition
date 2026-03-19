# RF-FS-002 Baseline Plan

**Дата:** 2026-03-19  
**Тема:** Уменьшить ширину плоских пакетов и вернуть package-level cohesion  
**Связанные находки:** `FS-001`  
**Основной scope:** `src/bioetl/application/core/`, `src/bioetl/application/composite/`, `src/bioetl/infrastructure/storage/`, `src/bioetl/interfaces/cli/commands/`

## Цель

Цель `RF-FS-002` не в том, чтобы разбросать файлы по подпапкам ради числа файлов на уровне каталога. Правильная цель — уменьшить когнитивную ширину hotspot-пакетов и вернуть им осмысленную внутреннюю географию. По текущему baseline самые проблемные каталоги выглядят так: `application/core` содержит около пятидесяти `.py` файлов на одном уровне, `application/composite` — около сорока, `infrastructure/storage` — более пятидесяти, `interfaces/cli/commands` — около тридцати пяти. Это уже не просто “много файлов”. На таком уровне package перестаёт быть архитектурной единицей и становится папкой-накопителем, где новые helper-модули появляются быстрее, чем возникает ясная карта ответственности.

## Почему это важно

Широкий плоский пакет создаёт четыре долговых эффекта одновременно. Во-первых, падает discoverability: новые участники и будущие refactor-wave читают каталог, а не bounded context. Во-вторых, растёт вероятность локальных дубликатов: похожие helpers легче создать рядом, чем найти правильный модуль. В-третьих, пакет начинает скрывать layering внутри себя: например, в `application/composite` рядом лежат planning, joining, validation, preflight, runner, metadata-adjacent helpers. В-четвёртых, test ownership становится мутнее: clustered tests покрывают поведение, но привязка к подсекторам пакета не читается.

## Принцип выполнения

`RF-FS-002` нельзя делать как один широкий move-only refactor. Это четыре независимых waves, каждая со своим blast radius и verify-set. Если попытаться двигать `application/core`, `application/composite`, `infrastructure/storage` и `interfaces/cli/commands` в одном батче, проект получит гигантский churn импортов, а реальный выигрыш трудно будет измерить. Поэтому эта задача должна быть декомпозирована по пакетам, даже если в планировании она остаётся под одним RF-ID.

## Подзадача 1. application/core

Здесь основной выигрыш даст выравнивание вокруг execution lifecycle. Вероятные зоны:
- lifecycle / runner context;
- batch execution / transform / writer orchestration;
- callbacks / metrics / tracing adjuncts;
- shared execution models и contracts.

Важно не разносить всё на микропапки. Если пакет уже большой, создание десяти подпакетов по два файла не решит проблему. Здесь нужна умеренная гранулярность, где каждый подпакет соответствует устойчивой теме.

## Подзадача 2. application/composite

Этот пакет уже отражает несколько разных смыслов:
- planning;
- dependency/join logic;
- validation;
- preflight;
- runner and execution coordination.

Рефакторинг должен закрепить именно эти зоны. Нельзя смешивать join-preparation helpers и runner-adjacent code только потому, что исторически они попали в один каталог. При этом нужно сохранять архитектурный контракт: весь код остаётся в application, без проталкивания логики в composition или infrastructure.

## Подзадача 3. infrastructure/storage

Это, вероятно, самый рискованный пакет в `RF-FS-002`, потому что он не просто широк, а ещё и operationally sensitive. На одном уровне сейчас живут bronze/silver/gold writers, metadata generation, delta helpers, resilience mixins, health/maintenance behavior. Правильный срез здесь не по классам, а по storage subdomains:
- bronze;
- silver;
- gold;
- metadata;
- delta primitives;
- cross-layer maintenance/resilience.

Особенно важно не смешать package split с change в storage behavior. Любой move должен быть максимально чистым и совместимым по imports.

## Подзадача 4. interfaces/cli/commands

Этот пакет уже частично готов к thinning через run-related split, но пока остаётся плоским каталогом команд и helper-модулей. Здесь естественные домены очевидны:
- run;
- health/diagnostics;
- quarantine;
- export/report;
- operational helpers.

CLI split обычно безопаснее storage/core, поэтому его можно выполнять раньше как более дешёвый structural win.

## Риски

Главный риск здесь не алгоритмический, а интеграционный. Package split ломает imports, реэкспорты, patch-пути в тестах, а иногда и неявные runtime assumptions в `__init__.py`. Второй риск — декоративное дробление: каталог станет глубже, но понятнее не будет. Третий риск — заодно начать править логику, хотя цель RF структурная. Четвёртый риск — делать этот RF до завершения cycle/config cleanup и потом заново двигать те же файлы.

## Минимизация рисков

- Выполнять `RF-FS-002` только после `RF-FS-001` и `RF-FS-004`.
- Для каждого hotspot-пакета отдельная wave и отдельная верификация.
- Первым шагом в каждой wave фиксировать target package map: какие подпакеты вводятся и какие файлы куда переезжают.
- Не менять поведение, сигнатуры и публичные CLI/storage contracts в том же батче, если можно избежать.
- Сохранять temporary re-exports там, где это нужно для совместимости тестов.

## Верификация

Для каждой package-wave набор разный, но общий принцип такой: сперва cluster-local unit tests, параллельно docs check, затем architecture + mypy.

Примеры:

```bash
./.venv/Scripts/python.exe -m pytest tests/unit/application/core -q
./.venv/Scripts/python.exe -m pytest tests/unit/application/composite -q
./.venv/Scripts/python.exe -m pytest tests/unit/infrastructure/storage -q
./.venv/Scripts/python.exe -m pytest tests/unit/interfaces/cli tests/unit/interfaces/cli/commands -q
```

Параллельно после каждого батча:

```bash
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs
```

После переноса импортов:

```bash
./.venv/Scripts/python.exe -m pytest tests/architecture/test_forbidden_imports.py tests/architecture/test_layer_dependencies.py -q
./.venv/Scripts/python.exe -m mypy --strict --no-incremental src/bioetl/
```

## Definition of Done

`RF-FS-002` закрывается не по количеству созданных подпапок, а по следующим признакам:
- каждый из четырёх hotspot-пакетов стал заметно уже на верхнем уровне;
- появились устойчивые подпакеты по ответственности, а не по историческим следам;
- imports и public seams остались предсказуемыми;
- тесты и architecture checks зелёные;
- package split снизил ширину без повторного смешения тем внутри новых подпакетов.

Итоговая цель этого RF — сделать структуру каталогов полезной картой системы, а не просто файловой поверхностью.
