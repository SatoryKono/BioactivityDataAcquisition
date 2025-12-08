# Domain Layer Audit

## 0. ������ ������

����� ���������� ����� `src/bioetl/domain`, ������������ (`configs/pipelines/chembl/*.yaml`, `configs/defaults/*.yaml`), ����� `src/bioetl/domain/schemas/chembl/*.py` � ������������ (`docs/domain`, `docs/architecture/14-class-diagrams-domain.md`). ��� � ������������� ����������� ������, bounded context��, ���������� � ��������� ������ DDD, � ����� ������������ ������� ����� ��������� ����.

## 1. ������������� �������

### 1.1 Runtime, registry � config-��������

| �������� | ��� | ��� | ������� ���� / ��������������� | ������� |
| --- | --- | --- | --- | --- |
| `StageResult` | `src/bioetl/domain/models.py` | dataclass | `stage_name`, `success`, �������� �������/������, ������������, ������ ������ | ���������� ������ |
| `RunContext` | `src/bioetl/domain/models.py` | dataclass | `run_id`, `entity_name`, `provider`, `started_at`, `config`, `dry_run`, `metadata` | ���������� ������� |
| `RunResult` | `src/bioetl/domain/models.py` | dataclass | ��� (`row_count`, `output_path`, ������������, ������, per-stage �������) | ������ ��������� |
| `StageDescriptor` | `src/bioetl/domain/models.py` | value object | �� ������, callable, ����� `skip_on_dry_run`/`required` | ������ ��������� |
| `PipelineConfig` + ������ | `src/bioetl/domain/configs/pipeline.py` | Pydantic aggregate | ID/`entity`/`provider`, `provider_config`, HTTP ��������, storage ����, �����������, �������, �����������, ������������, ����������� | �����������, ����������� ����� � �������������� |
| `ProviderDefinition` | `src/bioetl/domain/providers.py` | dataclass | ������������ `ProviderId`, ��� ������������ � ������� ����������� | ����� ����������� |
| `InMemoryProviderRegistry` | `src/bioetl/domain/provider_registry.py` | ������ | Register/list/restore �����������, �������� ���������� | ����� ����������� |
| `RawRecord` / `RecordSource` | `src/bioetl/domain/record_source.py` | TypedDict + Protocol | �������������� raw ������ � �������� ��������� ������ | ��� Extraction |
| `ApiRecordSource` | `src/bioetl/domain/record_source.py` | ������ | ��� �� `ExtractionServiceABC.iter_extract`, �������, chunking, optional `batch_adapter` | � ���� application-����������� |
| `ValidationResult` | `src/bioetl/domain/validation/contracts.py` | dataclass | `is_valid`, `errors`, `warnings`, `validated_df: pd.DataFrame | None` | �������� |
| `WriteResult` | `src/bioetl/domain/clients/base/output/contracts.py` | dataclass | `path: Path`, `row_count`, `duration_sec`, `checksum` | IO-���� |
| `HashService` | `src/bioetl/domain/transform/hash_service.py` | ������ | �������� `hash_row`, `hash_business_key`, `index`, `database_version`, `extracted_at` | ���-���������� ������ |
| `SchemaRegistry` | `src/bioetl/domain/schemas/registry.py` | ������ | ���������� Pandera-����, �������� `column_order`, `list/get` API | ��������� ������� |

### 1.2 �������� �� bounded context

| ������� | Pandera schema | Pipeline config | ������� ���� | ��������� |
| --- | --- | --- | --- | --- |
| Activity | `src/bioetl/domain/schemas/chembl/activity.py` | `configs/pipelines/chembl/activity.yaml` | 45+ ������� (assay/document/molecule �����, ���������, hash) | CSV �������� `data/input/activity.csv` |
| Assay | `src/bioetl/domain/schemas/chembl/assay.py` | `configs/pipelines/chembl/assay.yaml` | Organism, BAO id/label, �������������, target ������ | Config ��������� schema |
| Document | `src/bioetl/domain/schemas/chembl/document.py` | `configs/pipelines/chembl/document.yaml` | DOI/PMID, ������, ���, score | ��� ������ ������������ |
| Molecule | `src/bioetl/domain/schemas/chembl/molecule.py` | `configs/pipelines/chembl/molecule.yaml` | ChEMBL/PubChem ID, ����������� ������, parent-child, �������� | Docs ������������ � Molecule (glossary, domain objects, diagrams) |
| Target | `src/bioetl/domain/schemas/chembl/target.py` | `configs/pipelines/chembl/target.yaml` | Taxonomy, organism, UniProt, ����� � assay/activity | ����������� ��������� �������� |
| Cell / Tissue | `src/bioetl/domain/schemas/chembl/{cell,tissue}.py` | � | ���� `data/input/cell.csv`, `data/input/tissue.csv` ��� ���� � �������� | Stub Pandera-�����, pipeline/config TBD |

### 1.3 ���������

- �� �������� �������� ������������ Pandera-�������; ���������/dataclass��� ��� Activity/Assay/etc ���.
- ����������� (`docs/domain/01-glossary.md`, `docs/domain/schemas/00-schemas-overview.md`, `docs/architecture/01-domain-objects.md`, ��������� � `docs/architecture/diagrams/class/*.mmd`) ������������ � Molecule; ����������� файл `28-molecule-schema.mmd` �������� `TestItem`.
- CSV `cell/tissue` ������������ �� ������� ������; ������ ������ Pandera-����� (`cell.py`, `tissue.py`), �� pipeline/config ������ �������.

## 2. �������� � �����������

| ��� | ���� | ������� | ��� |
| --- | --- | --- | --- |
| �� `HashService` | `src/bioetl/domain/transform/hash_service.py`, `src/bioetl/infrastructure/transform/impl/hasher.py` | HashService ���������� ������ `HashServiceABC` | ✅ ��������: ������� infra-�������, HashService �������� только инжектируемый `HasherABC` |
| �����-��� | `src/bioetl/domain/observability/contracts.py` | `ProgressReporterABC` теперь живёт рядом с logging/tracing портами | ✅ ��������: shim удалён, импорты ведут на observability |
| ���������� �������� | `src/bioetl/domain/configs/base.py` | ����� re-export `pipeline.py` | ✅ ��������: файл удалён, импорты используют `domain.configs.pipeline` |
| Extraction shim | `src/bioetl/domain/contracts.py` | Alias �� `domain.ports.extraction` | ✅ ��������: shim удалён, прямые импорты из `domain.ports.extraction` |
| Docs vs ��� | `docs/domain/*`, `docs/architecture/14-class-diagrams-domain.md` | Docs ������� `TestItem/TestitemSchema`, � ���� ���� ������ `MoleculeTableSchema` | ✅ ��������: все ссылки обновлены на Molecule, диаграмма `28-molecule-schema.mmd` |
| ���������� ����� | `data/input/cell.csv`, `data/input/tissue.csv` | ����� ����, ����/�������� ��� | ✅ ��������: добавлены stub-схемы, но pipeline/config ещё не описаны |

### 2.1 �������

- [x] **HashService**: ���������� ����������, �������� �������� ����� + ������������� `Hasher`.
- [x] **Logging shim**: ������� `domain.clients.base.logging`, �������� ������� �� `domain.observability`.
- [x] **Configs/base**: ������� re-export, ������������� breaking change.
- [x] **`domain.contracts`**: ������ shim, �������� ���������/����.
- [x] **Docs TestItem**: ���������������� glossary/��������� � ����������� `Molecule` ��� �������� �������� ��������.
- [x] **Cell/Tissue**: ���� ������� �������/���������, ���� ������� ������� CSV.

## 3. ���� ���������� (ABC/Protocol)

| ��������� | ��� | ��������� | ������������ | ������ |
| --- | --- | --- | --- | --- |
| `RequestBuilderABC` | `domain/clients/base/contracts.py` | 1 (`ChemblRequestBuilderImpl`) | ������ ChemBL | �������� ��� �������� ���������� builder |
| `ResponseParserABC` | `domain/clients/base/contracts.py` | 1 | ������ ChemBL | �������� |
| `PaginatorABC` | `domain/clients/base/contracts.py` | 1 | ������ ChemBL | �������� �� enum/��������� |
| `RateLimiterABC` | `domain/clients/base/contracts.py` | 1 (`TokenBucket`) | �� ������������� | ������� `Noop` ��� �������� �� config |
| `RetryPolicyABC` | `domain/clients/base/contracts.py` | 1 (`ExponentialBackoff`) | �� ����������� | ��������� rate limiter |
| `SecretProviderABC` | `domain/clients/base/contracts.py` | 1 (`EnvSecretProvider`) | ����������� �������� ������� | �������� � �������������� ��� �������� Vault |
| `SideInputProviderABC` | `domain/clients/base/contracts.py` | 0 | ���� �� ��������� | ������ |
| `BatchAdapterABC` | `domain/ports/extraction.py` | 1 (`PandasBatchAdapter`) | ������ `ApiRecordSource` | ������� �� `Callable[[Any], list[RawRecord]]` |
| `DataClientABC` / `ChemblDataClientABC` | `domain/clients/*.py` | 1 (`ChemblDataClientHTTPImpl`) | �� ������ ����������� | ��� ������� ���������� ������ |
| `ExtractionServiceABC` | `domain/ports/extraction.py` | 1 (`ChemblExtractionServiceImpl`) | ��� ��������� | ���������� �������������� � ChemBL ������ |
| `HashServiceABC` / `HasherABC` | `domain/transform/contracts.py` | 1 (domain facade + HasherImpl) | ���-����������� | ������� ������������ canonical ���������� |
| `NormalizationServiceABC` | `domain/transform/contracts.py` | 2 (generic, ChemBL) | ���� ������������� | ���������, �� ������� ������� |
| `SchemaProviderABC` / `ValidatorABC` | `domain/validation/contracts.py` | 1 (SchemaRegistry / Pandera) | ���� ������� | ������������ roadmap ����������� |
| `WriterABC` / `MetadataWriterABC` / `QualityReportABC` / `OutputWriterABC` | `domain/clients/base/output/contracts.py` | 1�2 | ������ �� `Path` � `pd.DataFrame` | ������ � ��������������, �������� DTO-���� |
| `LoggingPortABC` / `PipelineMetricsPortABC` | `domain/observability/contracts.py` | 1 (Structured logger, SimpleNamespace metrics) | ������ ����������� �������� � `interfaces/wiring.py` | ������� ����������� ������� � ���������������� � ABC registry |

��������� � ?2 ��������� ������������ (`CacheABC`, `NormalizationServiceABC`, CSV/Parquet writers) ��������, �� ��������� ������������ ������� �������������.

## 4. �������� ������ DDD

1. **Domain - pandas** � `domain/transform/contracts.py`, `domain/validation/contracts.py`, `domain/clients/base/output/contracts.py` ��������� `pd.DataFrame`. > ���� value objects + �������� DataFrame - VO.
2. **����� ��������� ����** � `PipelineConfig` �������� HTTP ��������, ���� �, ��������� ����������� � ������. > �������� �� �������� �������� � ���������������� �������.
3. **`ApiRecordSource` ������������ ��������** � `src/bioetl/domain/record_source.py` ��������� ���������� � batch adapter. > �������� ����� � application ����, � ������ �������� ������ Protocol.
4. **IO-����� ����� ��� `Path` � �����������** � `WriterABC`/`OutputWriterABC` ������� `Path` � ��������� �������� ���������. > ������� ���� ��������� DTO; ������ ������ � ��������������.
5. **����������� vs ���**: docs ������������� � MoleculeTableSchema; `TestItem` ���������� ����������� (glossary, diagrams, README). > ����������� ������������� выполнена.
6. **Metrics port ��� ����������** � `PipelineMetricsPortABC` ���������� `types.SimpleNamespace` � `src/bioetl/interfaces/wiring.py`. > ������� ��������� ������� (Prometheus) � ���������������� ��� � ABC registry.

## 5. ������ �����

- ����������� ������������ ������ (schema/dataclass) �� ������ ������-��������.
- ������� ������� �������� � ��������������� ����������/DTO; DataFrame ������� ����������� �� ��������.
-  ������ ������ ����������� ����� (������ ABC ����� ?2 ���������� ��� roadmap).
- ������ ���������: ����� ����� �� ��������������� � ��������, �������������� � ��� HTTP/storage/logging/metrics.
- ����������� � ��������� ���������������� � �����; ����� `cell/tissue` ���� �������, ���� �������.

## 6. ����������� � ��������

### 6.1 Roadmap

| ������� | ���� | ������� �������� |
| --- | --- | --- |
| ������ ������ (?1 ������) | ������ | ✅ Done: HashService объединён, logging/config/extraction shim'ы удалены, docs → Molecule, stub-схемы cell/tissue |
| ������� ���� (1�3 �������) | ������������ | ����� dataclass/TypedDict ��� Activity/Assay/Document/Target/Molecule, �������� �������, ��������� `ApiRecordSource` � application ����, ��������� pipeline config |
| ����� ���� (3+ �������) | ������ ������� | ������� �������� metrics/writer ��������, ����������� ���������� ��� ����� �����������, ������� ����� �������� ������� |

### 6.2 ������� �������

- [x] �������� �������� �� ������� 2.1 (���������, ������������).
- [ ] ��������� ABC �� ������ �� ������� 3.
- [ ] ������������ ���������� �������� � ������� ���������������� ������������ (������ 4).
- [ ] ������� `docs/architecture/14-class-diagrams-domain.md` � ��������� ��������� ����� ��������������/��������.
- [ ] ������� `CHANGELOG.md` ��� ���� ��������� API/CLI ���������.

���������� roadmap ��������� �����������, ������ ������� ������ � ���������� �������� ������ ������.
