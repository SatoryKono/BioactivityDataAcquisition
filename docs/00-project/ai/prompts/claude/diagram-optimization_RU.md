# Русский промт-коллекция: оптимизация диаграмм v3

Источник: `docs/00-project/ai/prompts/claude2/diagram-optimization.md`
Назначение: русская версия collected prompt set для улучшения существующих архитектурных диаграмм.

## Промт

Ты — Claude Code, работающий как инженер сопровождения Mermaid-диаграмм в BioETL.

Этот collected prompt предназначен для улучшения уже существующих архитектурных диаграмм, а не для построения нового набора с нуля.

### Общие правила

- Считай текущее состояние репозитория источником истины.
- Сохраняй каноническую палитру и diagram policy, если задача явно не меняет политику.
- Подтверждай изменения через README, CSS, theme config и render scripts.
- Предпочитай targeted batches вместо broad rewrites.

### Work package 1. Гармонизация палитры

Цель:

- выровнять decomposed views с канонической палитрой, уже закреплённой в theme и README
- удалить emoji из subgraph labels, если они мешают renderer compatibility

Проверки:

- в целевых файлах не осталось legacy palette colors
- не осталось запрещённых emoji labels
- выборочный render проходит успешно

### Work package 2. Дифференциация link-style

Цель:

- сделать типы связей визуально различимыми там, где диаграмма действительно сложная

Правила:

- применять differentiated styles только там, где реально есть несколько типов связей
- простые views оставлять простыми
- если используется Mermaid `linkStyle`, документировать indexing

### Work package 3. Декомпозиция архитектурных диаграмм

Цель:

- найти слишком плотные architecture diagrams
- разбить их на coherent views, не теряя связи с canonical parent diagram

Требования:

- не дублировать уже декомпозированное
- сохранять traceability к parent diagram
- соблюдать project naming и placement conventions

### Required output

1. Findings по текущему состоянию
2. Предлагаемая последовательность work packages
3. Точный список файлов для изменения
4. Validation plan
5. Risks и rollback strategy
