# Class Diagrams - Domain Layer

Диаграммы классов для слоя Domain (bioetl.domain).

## 1. Validation Service Structure

```mermaid
classDiagram
    class ValidationService {
        -_schema_provider: SchemaProviderABC
        +get_schema(entity_name) Type[DataFrameModel]
        +get_schema_columns(entity_name) list[str]
        +validate(df, entity_name) DataFrame
    }

    class SchemaProviderABC {
        <<abstract>>
        +get_schema(name)* Type[DataFrameModel]
        +list_schemas()* list[str]
        +get_schema_columns(name)* list[str]
        +register(name, schema, column_order)*
    }

    class SchemaRegistry {
        -_schemas: dict[str, _SchemaEntry]
        +register(name, schema, column_order)
        +get_schema(name) Type[DataFrameModel]
        +get_schema_columns(name) list[str]
        +list_schemas() list[str]
    }

    class ValidatorABC {
        <<abstract>>
        +validate(df)* ValidationResult
        +is_valid(df)* bool
    }

    class PanderaValidatorImpl {
        -_schema: Type[DataFrameModel]
        +validate(df) ValidationResult
        +is_valid(df) bool
    }

    ValidationService --> SchemaProviderABC : uses
    SchemaProviderABC <|-- SchemaRegistry
    ValidatorABC <|-- PanderaValidatorImpl
```

## 2. Transform Services

```mermaid
classDiagram
    class TransformerABC {
        <<abstract>>
        +apply(df, context)* DataFrame
    }

    class TransformerChain {
        -_transformers: list[TransformerABC]
        +apply(df, context) DataFrame
    }

    class HashColumnsTransformer {
        -_hash_service: HashService
        -_business_key_fields: list[str]
        +apply(df, context) DataFrame
    }

    class IndexColumnTransformer {
        -_hash_service: HashService
        +apply(df, context) DataFrame
    }

    class DatabaseVersionTransformer {
        -_hash_service: HashService
        -_database_version_provider: Callable
        +apply(df, context) DataFrame
    }

    class FulldateTransformer {
        -_hash_service: HashService
        +apply(df, context) DataFrame
    }

    TransformerABC <|-- TransformerChain
    TransformerABC <|-- HashColumnsTransformer
    TransformerABC <|-- IndexColumnTransformer
    TransformerABC <|-- DatabaseVersionTransformer
    TransformerABC <|-- FulldateTransformer
```

## 3. Hash Service

```mermaid
classDiagram
    class HashService {
        -_hasher: HasherABC
        -_index_counter: int
        -_now_provider: Callable
        -_extracted_at: str | None
        +add_hash_columns(df, business_key_cols) DataFrame
        +add_index_column(df) DataFrame
        +add_database_version_column(df, version) DataFrame
        +add_fulldate_column(df) DataFrame
        +reset_state()
    }

    class HasherABC {
        <<abstract>>
        +hash_row(row)* str
        +hash_columns(df, cols)* Series
        +hash_value(value)* str
    }

    class HasherImpl {
        +hash_row(row) str
        +hash_columns(df, cols) Series
        +hash_value(value) str
        -_serialize_canonical(obj) str
    }

    HashService --> HasherABC : uses
    HasherABC <|-- HasherImpl
```

## 4. Normalization Service

```mermaid
classDiagram
    class NormalizationService {
        <<Protocol>>
        +normalize_record(record, config) NormalizedRecord
    }

    class ChemblNormalizationService {
        +normalize_record(record, config) NormalizedRecord
        -_normalize_field(field_name, value, config)
    }

    class NormalizationServiceABC {
        <<abstract>>
        +normalize_record(record, config)* NormalizedRecord
    }

    class NormalizationService {
        -_normalizers: dict[str, Callable]
        +normalize_record(record, config) NormalizedRecord
        -_normalize_scalar(value, mode)
        -_normalize_array(value)
        -_normalize_record(value)
    }

    NormalizationService <|.. ChemblNormalizationService
    NormalizationServiceABC <|-- NormalizationService
```

## 5. Schema Models

```mermaid
classDiagram
    class DataFrameModel {
        <<Pandera>>
    }

    class ActivitySchema {
        +activity_id: int
        +assay_id: int
        +molecule_id: int
        +target_id: int
        +value: float
        +unit: str
    }

    class AssaySchema {
        +assay_id: int
        +assay_type: str
        +assay_category: str
        +description: str
    }

    class DocumentSchema {
        +document_id: int
        +pubmed_id: int
        +doi: str
        +title: str
    }

    class TargetSchema {
        +target_id: int
        +target_type: str
        +pref_name: str
    }

    class MoleculeSchema {
        +molecule_id: int
        +molecular_formula: str
        +molecular_weight: float
    }

    DataFrameModel <|-- ActivitySchema
    DataFrameModel <|-- AssaySchema
    DataFrameModel <|-- DocumentSchema
    DataFrameModel <|-- TargetSchema
    DataFrameModel <|-- MoleculeSchema
```

## 6. Domain Models

```mermaid
classDiagram
    class RunContext {
        +start_time: datetime
        +stage: str
        +chunk_index: int
        +entity_name: str
        +provider: str
    }

    class StageResult {
        +stage: str
        +success: bool
        +row_count: int
        +duration_sec: float
        +error: Exception | None
    }

    class RunResult {
        +success: bool
        +row_count: int
        +duration_sec: float
        +stages: list[StageResult]
        +metadata: dict
    }

    class StageDescriptor {
        +name: str
        +description: str
        +order: int
    }

    RunResult --> StageResult : contains
    RunContext --> StageDescriptor : uses
```

## 7. Provider Registry

```mermaid
classDiagram
    class ProviderId {
        <<Enum>>
        +CHEMBL
        +PUBCHEM
        +DUMMY
    }

    class ProviderDefinition {
        +provider_id: ProviderId
        +config_class: Type[BaseProviderConfig]
        +components: ProviderComponents
    }

    class ProviderComponents {
        <<Protocol>>
        +create_client(config) DataClientABC
        +create_normalization_service(config) NormalizationService
    }

    class ProviderRegistry {
        -_providers: dict[ProviderId, ProviderDefinition]
        +register(definition)
        +get(provider_id) ProviderDefinition
        +list_all() list[ProviderDefinition]
        +reset()
    }

    ProviderRegistry --> ProviderDefinition : stores
    ProviderDefinition --> ProviderId : uses
    ProviderDefinition --> ProviderComponents : contains
```

## 8. Normalizers

```mermaid
classDiagram
    class NormalizerFunction {
        <<Callable>>
        +normalize(value) Any
    }

    class IdentifierNormalizers {
        +normalize_doi(value) str | None
        +normalize_chembl_id(value) str | None
        +normalize_pmid(value) int | None
        +normalize_pcid(value) int | None
        +normalize_uniprot(value) str | None
        +normalize_bao_id(value) str | None
        +normalize_bao_label(value) str | None
    }

    class CollectionNormalizers {
        +normalize_array(value) list | None
        +normalize_record(value) dict | None
        +normalize_target_components(value) list[dict] | None
        +normalize_cross_references(value) list[dict] | None
    }

    class NormalizerRegistry {
        -_normalizers: dict[str, Callable]
        +register(field_name, func)
        +get(field_name) Callable | None
    }

    NormalizerRegistry --> NormalizerFunction : stores
    IdentifierNormalizers ..> NormalizerFunction : implements
    CollectionNormalizers ..> NormalizerFunction : implements
```

## 9. Domain Contracts

```mermaid
classDiagram
    class DataClientABC {
        <<abstract>>
        +fetch_one(id)*
        +fetch_many(ids)*
        +iter_pages(request)*
    }

    class ExtractionServiceABC {
        <<abstract>>
        +extract_all()* DataFrame
        +extract_by_ids(ids)* DataFrame
        +extract_by_filter(filter_params)* DataFrame
    }

    class RecordSource {
        <<Protocol>>
        +iter_records()* Iterable[RawRecord]
        +get_total_count()* int | None
    }

    class InMemoryRecordSource {
        -_records: list[RawRecord]
        +iter_records() Iterable[RawRecord]
        +get_total_count() int
    }

    class ApiRecordSource {
        -_extraction_service: ExtractionServiceABC
        -_filter_params: dict
        +iter_records() Iterable[RawRecord]
        +get_total_count() int | None
    }

    RecordSource <|.. InMemoryRecordSource
    RecordSource <|.. ApiRecordSource
    ExtractionServiceABC --> DataClientABC : uses
```

## 10. Domain Errors

```mermaid
classDiagram
    class BioetlError {
        +message: str
    }

    class ConfigError {
    }

    class ConfigValidationError {
    }

    class ProviderError {
    }

    class ClientError {
    }

    class ClientNetworkError {
    }

    class ClientRateLimitError {
    }

    class ClientResponseError {
    }

    class PipelineStageError {
        +stage: str
        +context: dict
    }

    BioetlError <|-- ConfigError
    ConfigError <|-- ConfigValidationError
    BioetlError <|-- ProviderError
    ProviderError <|-- ClientError
    ClientError <|-- ClientNetworkError
    ClientError <|-- ClientRateLimitError
    ClientError <|-- ClientResponseError
    BioetlError <|-- PipelineStageError
```

