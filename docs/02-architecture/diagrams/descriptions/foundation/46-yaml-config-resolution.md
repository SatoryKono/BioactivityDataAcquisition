______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-02'

______________________________________________________________________

# Title: YAML Configuration and Contract Rollout Resolution Chain

- Исходная диаграмма: `foundation/46-yaml-config-resolution.mmd`

## Описание

Диаграмма описывает не только YAML merge path, но и то, как из `contracts`-секции выводятся typed contract policy, runtime rollout value object и planner/runtime routing semantics. Это делает схему актуальной для нынешней версии BioETL, где configuration resolution напрямую определяет version-aware Silver/Gold reads and writes.

Ключевые участки:

- layered merge base/provider/entity/source остаётся входом для `PipelineYamlConfig`;
- DQ и filter hierarchies продолжают идти через отдельные loaders;
- `PipelineContractPolicy` и `ContractRolloutPolicy` теперь явно выведены из того же resolved payload;
- version-aware routing показывает смысл `read_order`, `write_versions`, `shadow_versions` и `affects_hash`;
- `ContractMigrationService` и CLI `maintenance plan` используют те же rollout anchors, но уже в planner-only режиме и разворачивают `transitions` + `required_actions`.

Эта схема теперь служит bridge-документом между config resolution, contract rollout и maintenance planning.

## Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-04-02`
