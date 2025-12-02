<!-- e3b2af17-2515-4c9c-8c19-665061317214 44727322-823c-40a0-b14a-4412038f26ac -->
# Структура документации BioETL

## Целевая структура

```
docs/
├── project/
│   └── 00-rules-summary.md              # Сводка правил проекта
├── architecture/
│   ├── 00-overview.md                   # Обзор архитектуры (назначение, уровни)
│   ├── 01-domain-objects.md             # ABC-объекты: Assay, Activity, Target, TestItem
│   ├── 02-etl-layers.md                 # Уровни ETL-архитектуры
│   ├── 03-pipeline-base.md              # PipelineBase и производные классы
│   └── 04-abc-interfaces.md             # ABC-интерфейсы по слоям
├── reference/
│   └── abc/
│       └── index.md                     # Каталог всех ABC-интерфейсов
├── 02-pipelines/
│   └── chembl/
│       ├── README.md                    # Обзор ChEMBL-пайплайнов
│       ├── activity/
│       │   └── 00-activity-chembl-overview.md   # ChemblActivityPipeline
│       ├── assay/
│       │   └── 00-assay-chembl-overview.md      # ChemblAssayPipeline
│       ├── target/
│       │   └── 00-target-chembl-overview.md     # ChemblTargetPipeline
│       ├── testitem/
│       │   └── 00-testitem-chembl-overview.md   # ChemblTestitemPipeline
│       └── document/
│           └── 00-document-chembl-overview.md   # ChemblDocumentPipeline
└── integration/
    └── 00-rest-api-integration.md       # Интеграция с внешними REST API
```

## Изменения

| Файл | Действие |

|------|----------|

| `docs/architecture/README.md` | Переименовать в `00-overview.md`, обновить содержимое |

| `docs/project/00-rules-summary.md` | Создать (сводка правил) |

| `docs/architecture/01-domain-objects.md` | Создать (ABC-объекты) |

| `docs/architecture/02-etl-layers.md` | Создать (уровни архитектуры) |

| `docs/architecture/03-pipeline-base.md` | Создать (PipelineBase) |

| `docs/architecture/04-abc-interfaces.md` | Создать (ABC-интерфейсы) |

| `docs/reference/abc/index.md` | Создать (каталог ABC) |

| `docs/02-pipelines/chembl/README.md` | Создать (обзор ChEMBL) |

| `docs/02-pipelines/chembl/activity/00-activity-chembl-overview.md` | Создать |

| `docs/02-pipelines/chembl/assay/00-assay-chembl-overview.md` | Создать |

| `docs/02-pipelines/chembl/target/00-target-chembl-overview.md` | Создать |

| `docs/02-pipelines/chembl/molecule/00-molecule-chembl-overview.md` | Создать |

| `docs/02-pipelines/chembl/document/00-document-chembl-overview.md` | Создать |

| `docs/integration/00-rest-api-integration.md` | Создать |

## Содержание ключевых документов

### `docs/architecture/00-overview.md`

- Назначение проекта BioETL
- Поддерживаемые источники (ChEMBL + планы: PubMed, PubChem, UniProt и др.)
- ABC-модель доменных сущностей (обзор)
- Ссылки на детальные документы

### `docs/architecture/01-domain-objects.md`

- Assay: идентификатор, типы тестов, биологический контекст
- Activity: activity_id, связи, числовые параметры, бизнес-ключ, хеш-строки
- Target: target_chembl_id, uniprot_id, классификация
- TestItem: molecule_chembl_id, химические идентификаторы
- Взаимосвязи ABC-объектов (диаграмма)

### `docs/architecture/03-pipeline-base.md`

- Табличный PipelineBase (`src/bioetl/core/pipeline_base.py`)
- Stage-ориентированный PipelineBase (`unified.py`)
- ChEMBL-специализации: ChemblPipelineBase, ChemblCommonPipeline, ChemblDocumentPipeline
- Методы: `run`, `extract`, `transform`, `validate`, `write`

### `docs/02-pipelines/chembl/activity/00-activity-chembl-overview.md`

- Источник: ChEMBL `/activity`
- Класс: ChemblActivityPipeline
- Стадии: extract → transform → validate → save_results
- Ключевые поля, бизнес-ключ
- Конфигурация: `configs/pipelines/chembl/activity.yaml`

## Источники контента

- Предоставленный текст архитектуры (раздел user_query)
- Существующий `docs/architecture/README.md`
- Конфигурации `configs/pipelines/chembl/*.yaml`

### To-dos

- [ ] Создать docs/project/00-rules-summary.md
- [ ] Переименовать и обновить docs/architecture/00-overview.md
- [ ] Создать docs/architecture/01-domain-objects.md
- [ ] Создать docs/architecture/02-etl-layers.md
- [ ] Создать docs/architecture/03-pipeline-base.md
- [ ] Создать docs/architecture/04-abc-interfaces.md
- [ ] Создать docs/reference/abc/index.md
- [ ] Создать docs/02-pipelines/chembl/README.md
- [ ] Создать 00-activity-chembl-overview.md (ChemblActivityPipeline)
- [ ] Создать 00-assay-chembl-overview.md (ChemblAssayPipeline)
- [ ] Создать 00-target-chembl-overview.md (ChemblTargetPipeline)
- [ ] Создать 00-testitem-chembl-overview.md (ChemblTestitemPipeline)
- [ ] Создать 00-document-chembl-overview.md (ChemblDocumentPipeline)
- [ ] Создать docs/integration/00-rest-api-integration.md