# 00 Index

## Список ChEMBL-пайплайнов

- **Activity** — формирует таблицу активностей с бизнес-ключами и QC-отчётами.
- **Assay** — нормализует описания биологических ассеев.
- **Target** — собирает и обогащает мишени, связывая их с активностями.
- **TestItem** — нормализует тестируемые объекты и их идентификаторы.
- **Document** — агрегирует публикации и метаданные для ссылок на эксперименты.
- **Molecule** — выгружает молекулы с деталями (структуры, свойства, иерархия) в `id_only` режиме через список идентификаторов.

## Общие принципы

Все пайплайны наследуют `ChemblPipelineBase` ([`src/bioetl/application/pipelines/chembl/base.py`](../../../../src/bioetl/application/pipelines/chembl/base.py)), используют единый `ChemblExtractionService` и общую конфигурацию (release, пагинация, лимиты). Доступны dry-run и QC-артефакты по умолчанию.

## Навигация по пайплайнам

- Activity: `activity/00-activity-chembl-overview.md`
- Assay: `assay/00-assay-chembl-overview.md`
- Target: `target/00-target-chembl-overview.md`
- TestItem: `testitem/00-testitem-chembl-overview.md`
- Document: `document/00-document-chembl-overview.md`
- Molecule: `molecule/00-molecule-chembl-overview.md`
