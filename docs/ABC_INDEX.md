# ABC Index
<!-- generated -->

- `DataClientABC` — `bioetl.domain.clients.contracts.DataClientABC`
  - Universal data source client contract. Supports extraction of arbitrary entities through a unified ``fetch`` method with filters, as well as side operations (pagination, metadata, resource release).

- `RequestBuilderABC` — `bioetl.domain.clients.base.contracts.RequestBuilderABC`
  - Builder pattern for request creation. This ABC provides a fluent interface for constructing API requests. Implementations should support endpoint configuration and pagination. Note: Consider using :class:`bioetl.domain.ports.request_building.RequestBuilderPortABC` for new code - it provides a cleaner port-based contract.

- `ResponseParserPortABC` — `bioetl.domain.ports.parsing.ResponseParserPortABC`
  - Port for parsing raw API responses without domain model knowledge. This abstract base class defines the contract for parsing raw API responses into generic record dictionaries. Implementations in infrastructure layer can parse provider-specific response formats while domain layer remains decoupled from those details. Type Parameters: RecordT: The type of records returned by parse_to_records. Defaults to RawRecord (dict[str, Any]) for untyped parsing. Example: >>> # Untyped parser (default) >>> class ChemblParserAdapter(ResponseParserPortABC): ... def parse_to_records(self, raw_response): ... # Extract records from ChEMBL-specific response structure ... for key, value in raw_response.items(): ... if isinstance(value, list): ... return value ... return [] ... ... def extract_pagination(self, raw_response): ... return raw_response.get("page_meta", {}) >>> # Typed parser with Pydantic model >>> class TypedParser(ResponseParserPortABC[MyModel]): ... def parse_to_records(self, raw_response) -> list[MyModel]: ... return [MyModel(**r) for r in raw_response.get("items", [])] ... ... def extract_pagination(self, raw_response): ... return raw_response.get("meta", {})

- `PaginatorABC` — `bioetl.domain.clients.base.contracts.PaginatorABC`
  - Pagination strategy.

- `RateLimiterABC` — `bioetl.domain.clients.base.contracts.RateLimiterABC`
  - Request rate limiting.

- `CacheABC` — `bioetl.domain.clients.base.contracts.CacheABC`
  - Caching interface.

- `SecretProviderABC` — `bioetl.domain.clients.base.contracts.SecretProviderABC`
  - Secret provider (env, vault).

- `PipelineContainerABC` — `bioetl.application.contracts.PipelineContainerABC`
  - Dependency container contract for assembling pipelines. Provides factories for core pipeline services, including logging, validation, extraction, normalization, record sourcing, hashing, post-transformation, hooks, and error handling.

- `PipelineHookABC` — `bioetl.domain.pipelines.contracts.PipelineHookABC`
  - Pipeline lifecycle hooks.

- `ErrorPolicyABC` — `bioetl.domain.pipelines.contracts.ErrorPolicyABC`
  - Error handling policy.

- `LoaderABC` — `bioetl.domain.pipelines.contracts.LoaderABC`
  - Component responsible for loading data to destination. Uses domain-level TabularData abstraction for input data.

- `ProviderRegistryLoaderABC` — `bioetl.domain.provider_registry.ProviderRegistryLoaderABC`
  - Protocol for provider registry loader.

- `ProviderRegistryABC` — `bioetl.domain.provider_registry.ProviderRegistryABC`
  - Abstract base class for provider registry.

- `ProgressReporterABC` — `bioetl.domain.observability.contracts.ProgressReporterABC`
  - Progress reporting interface. Concrete implementation is selected by infrastructure and bound to the container.

- `LoggingPortABC` — `bioetl.domain.observability.contracts.LoggingPortABC`
  - Port describing structured logging operations.

- `TracingPortABC` — `bioetl.domain.observability.contracts.TracingPortABC`
  - Port describing distributed tracing operations. Experimental: not yet integrated into main pipeline flow.

- `HasherABC` — `bioetl.domain.transform.contracts.HasherABC`
  - Low-level hashing abstraction. Provides primitive hashing operations used by HashServiceABC. Uses domain-level Record and TabularData instead of pandas types. Infrastructure implementations can work with pandas internally. Note: This is an internal abstraction. Prefer HashServiceABC for domain code.

- `HashServiceABC` — `bioetl.domain.transform.contracts.HashServiceABC`
  - Stateless service for computing deterministic hashes. Responsible for computing and adding hash columns to data. Does not contain stateful logic (indices, timestamps). Terminology (see module docstring for full mapping): fingerprint: Computes record_hash - hash of entire record. entity_key: Computes business_key_hash - hash of business key fields. Output columns (schema layer): hash_row: Contains the record_hash (fingerprint result). hash_business_key: Contains the business_key_hash (entity_key result). Example: >>> service: HashServiceABC = get_hash_service() >>> digest = service.compute_fingerprint({"id": 1, "name": "test"}) >>> print(digest.value) # hex string

- `TimestampProviderABC` — `bioetl.domain.transform.contracts.TimestampProviderABC`
  - Timestamp provider for data extraction. Provides deterministic timestamp within a session.

- `IndexGeneratorABC` — `bioetl.domain.transform.contracts.IndexGeneratorABC`
  - Sequential index generator for data rows. Stateful: maintains counter value between calls.

- `NormalizationServiceABC` — `bioetl.domain.transform.contracts.NormalizationServiceABC`
  - Data normalization service. Provides batch and record-level normalization operations. Uses domain-level TabularData abstraction.

- `SchemaProviderABC` — `bioetl.domain.validation.contracts.SchemaProviderABC`
  - Data schema provider (technology-agnostic).

- `ValidatorFactoryABC` — `bioetl.domain.validation.contracts.ValidatorFactoryABC`
  - Factory for schema-specific validators.

- `SchemaProviderFactoryABC` — `bioetl.domain.validation.contracts.SchemaProviderFactoryABC`
  - Factory for schema providers.

- `QualityReportABC` — `bioetl.domain.clients.base.output.contracts.QualityReportABC`
  - QC report generator port. Uses domain-level TabularData abstraction.

- `OutputFrameConverterABC` — `bioetl.domain.clients.base.output.contracts.OutputFrameConverterABC`
  - Tabular data converter for post-processing before write. Uses domain-level TabularData abstraction.
