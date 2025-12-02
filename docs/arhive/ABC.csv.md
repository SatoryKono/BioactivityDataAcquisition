# ABC.csv

|  /  |  |  |   |   |  |
| --- | --- | --- | --- | --- | --- |
| PipelineBase | core/pipeline_base.py |   ETL-: orchestrate extract?transform?validate?write | run(...) -> RunResult, extract(...) -> DataFrame, transform(df) -> DataFrame, validate(df) -> DataFrame, write(df, output_path) -> WriteResult, register_client(name, client), close_resources() | _add_hash_columns(df) -> DataFrame | config: PipelineConfig, run_id: str, pipeline_name: str, _clients: dict, _logger |
| StageABC | core/pipeline/base.py |     | run(context) -> Any, close() |  |  |
| PipelineHookABC | core/pipeline/hook.py |      | on_stage_start(stage), on_stage_complete(stage), on_stage_error(stage, error) |  |  |
| CLICommandABC | core/pipeline/cli_command.py |   CLI- | register_cli(cli_app), run_pipeline(config) -> RunResult |  |  |
| SourceClientABC | core/pipeline/source/client.py | Unified API    | fetch_one(request) -> Record, fetch_many(request) -> Iterator, iter_pages(request) -> Iterator, metadata() -> Mapping, close() |  |  |
| BaseExternalDataClient | core/pipeline/source/client.py |  SourceClientABC    | . SourceClientABC + metadata() | _build_url(...), _extract_items(...), _extract_next_cursor(...), _resolve_path(...) | _base_url, _routes, _default_params, _pagination, _transport |
| RateLimiterABC | core/pipeline/source/client.py |     | acquire(), reset() |  | max_calls, period_sec |
| RetryPolicyABC | core/pipeline/source/client.py |     | should_retry(error, attempt) -> bool, get_delay(attempt) -> float |  | max_attempts, base_delay |
| RequestBuilderABC | core/pipeline/source/request_builder.py |    API | build_request(params, page_token=None) -> ClientRequest |  |  |
| ResponseParserABC | core/pipeline/source/parser.py |  API- | parse(raw_data) -> Iterator[Record] |  |  |
| PaginatorABC | core/pipeline/source/parser.py |     | extract_items(raw) -> list[Record], `get_next_token(raw) -> str | None` |  |
| TransformerABC | core/pipeline/processing/transform.py |  DataFrame | transform(df) -> DataFrame |  |  |
| LookupEnricherABC | core/pipeline/processing/enrich.py |     | enrich(df, provider) -> DataFrame |  |  |
| SideInputProviderABC | core/pipeline/processing/enrich.py |     | get_data(key: str) -> Any |  |  |
| DeduplicatorABC | core/pipeline/processing/dedup.py |   | deduplicate(df) -> DataFrame |  | key_deriver, hasher, merge_strategy |
| BusinessKeyDeriverABC | core/pipeline/processing/dedup.py |  - | derive_key(record) -> str |  | key_fields: list[str] |
| HasherABC | core/pipeline/processing/dedup.py |    | hash(record) -> str |  | algorithm: str |
| MergeStrategyABC | core/pipeline/processing/dedup.py |   | merge(records: list[Record]) -> Record |  |  |
| SchemaProviderABC | core/pipeline/validation/schema.py |    | get_schema() -> Any |  |  |
| ValidatorABC | core/pipeline/validation/validator.py |  DataFrame   | validate(df) -> ValidationResult |  | schema_provider, rules |
| DQRuleABC | core/pipeline/validation/dq_rules.py | -   | check(df) -> list[DQIssue] |  | name, description |
| PathStrategyABC | core/pipeline/output/path_strategy.py |    | make_path(pipeline_name, run_id, base_dir) -> Path |  |  |
| WriterABC | core/pipeline/output/writer.py |  DataFrame   | write(df, path: Path) |  |  |
| MetadataWriterABC | core/pipeline/output/writer.py |    | write_metadata(run_result, meta_path) |  |  |
| ConfigResolverABC | core/pipeline/utils/config.py |     | resolve(config_name) -> PipelineConfig |  |  |
