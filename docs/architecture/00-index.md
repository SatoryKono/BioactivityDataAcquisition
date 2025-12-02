# 00 Index

## Содержание раздела

- `01-domain-objects.md` — описание доменных сущностей Assay, Activity, Target, TestItem и их связи с источниками.
- `02-etl-layers.md` — детализация шести ETL-слоёв, их ответственности и контрактов.
- `03-data-flow.md` — сквозной поток данных от extract до write, хуки и политики ошибок.
- `04-duplication-reduction.md` — стратегии снижения дублирования через ABC/Default/Impl и наследование пайплайнов.

## Навигация

Для обзора проекта начните с `docs/architecture/system_design.md`. За справочниками по API и схемам переходите в `docs/domain/*` и `docs/infrastructure/*`, за практическими шагами — в `docs/guides/*`, а за конкретными пайплайнами — в `docs/application/pipelines/chembl/*`.