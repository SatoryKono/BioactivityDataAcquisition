# Class Diagrams - Interfaces Layer

Диаграммы классов для слоя Interfaces (bioetl.interfaces).

## 1. CLI Application Structure

```mermaid
classDiagram
    class CLIApp {
        +list_pipelines()
        +validate_config(config_path)
        +run(pipeline_name, profile, output, dry_run, config_path, limit, input_path, input_mode, csv_delimiter, csv_header, background)
        +smoke_run(pipeline_name)
    }

    class CLICommandABC {
        <<abstract>>
        +execute()*
    }

    class PipelineOrchestrator {
        +build_pipeline(limit)
        +run_pipeline(dry_run, limit)
        +run_in_background(dry_run, limit, executor)
    }

    CLIApp --> PipelineOrchestrator : uses
    CLIApp ..> CLICommandABC : may use
```

## 2. REST API Structure

```mermaid
classDiagram
    class FastAPI {
        +app
        +post("/pipelines/run")
        +get("/pipelines/status")
    }

    class PipelineRunRequest {
        +pipeline_name: str
        +profile: str
        +dry_run: bool
        +limit: int | None
    }

    class PipelineRunResponse {
        +success: bool
        +row_count: int
        +duration_sec: float
    }

    class PipelineOrchestrator {
        +run_pipeline(dry_run, limit)
    }

    FastAPI --> PipelineRunRequest : receives
    FastAPI --> PipelineRunResponse : returns
    FastAPI --> PipelineOrchestrator : uses
```

## 3. MQ Listener Structure

```mermaid
classDiagram
    class MQListener {
        -queue_name: str
        -handler: MQJobHandler
        +start()
        +stop()
        +listen()
    }

    class MQJob {
        +pipeline_name: str
        +config: dict
        +job_id: str
    }

    class MQJobHandler {
        +handle(job: MQJob)
        -_to_pipeline_id(name: str)
        -_create_orchestrator(name: str, profile: str)
    }

    class PipelineOrchestrator {
        +run_pipeline(dry_run, limit)
    }

    MQListener --> MQJobHandler : uses
    MQJobHandler --> MQJob : processes
    MQJobHandler --> PipelineOrchestrator : uses
```

## 4. CLI Contracts

```mermaid
classDiagram
    class CLICommandABC {
        <<abstract>>
        +execute()* RunResult
        +validate()* bool
    }

    class RunCommand {
        +execute() RunResult
        +validate() bool
    }

    class ListCommand {
        +execute() RunResult
        +validate() bool
    }

    class ValidateCommand {
        +execute() RunResult
        +validate() bool
    }

    CLICommandABC <|-- RunCommand
    CLICommandABC <|-- ListCommand
    CLICommandABC <|-- ValidateCommand
```

## 5. REST API Models

```mermaid
classDiagram
    class BaseModel {
        +model_dump()
        +model_validate()
    }

    class PipelineRunRequest {
        +pipeline_name: str
        +profile: str
        +dry_run: bool
        +limit: int | None
        +output_path: str | None
    }

    class PipelineRunResponse {
        +success: bool
        +row_count: int
        +duration_sec: float
        +error: str | None
    }

    class PipelineStatusResponse {
        +pipeline_name: str
        +status: str
        +progress: float
    }

    BaseModel <|-- PipelineRunRequest
    BaseModel <|-- PipelineRunResponse
    BaseModel <|-- PipelineStatusResponse
```

## 6. MQ Job Processing

```mermaid
classDiagram
    class MQJob {
        +job_id: str
        +pipeline_name: str
        +config: dict
        +created_at: datetime
        +status: str
    }

    class JobProcessor {
        +process(job: MQJob)
        -_validate_job()
        -_execute_pipeline()
    }

    class JobQueue {
        +enqueue(job: MQJob)
        +dequeue() MQJob | None
        +get_status(job_id) JobStatus
    }

    class JobStatus {
        +job_id: str
        +status: str
        +progress: float
        +result: RunResult | None
    }

    JobProcessor --> MQJob : processes
    JobQueue --> MQJob : manages
    JobQueue --> JobStatus : tracks
```

## 7. Interface Adapters

```mermaid
classDiagram
    class InterfaceAdapter {
        <<abstract>>
        +execute()*
        +validate()*
    }

    class CLIAdapter {
        +execute() RunResult
        +validate() bool
        -_parse_args()
        -_resolve_config()
    }

    class RESTAdapter {
        +execute() RunResult
        +validate() bool
        -_parse_request()
        -_build_response()
    }

    class MQAdapter {
        +execute() RunResult
        +validate() bool
        -_deserialize_job()
        -_serialize_result()
    }

    InterfaceAdapter <|-- CLIAdapter
    InterfaceAdapter <|-- RESTAdapter
    InterfaceAdapter <|-- MQAdapter
```

## 8. Configuration Resolution

```mermaid
classDiagram
    class ConfigResolver {
        +resolve_config(pipeline_name, profile, overrides) PipelineConfig
        -_load_base_config()
        -_apply_profile()
        -_apply_overrides()
    }

    class PipelineConfig {
        +entity_name: str
        +provider: str
        +output_path: str
        +pagination: PaginationConfig
        +client: ClientConfig
    }

    class ConfigLoader {
        +load_from_path(path, profile) PipelineConfig
        +load_from_dict(data, profile) PipelineConfig
    }

    ConfigResolver --> ConfigLoader : uses
    ConfigResolver --> PipelineConfig : returns
```

## 9. Error Handling in Interfaces

```mermaid
classDiagram
    class InterfaceError {
        +message: str
        +code: str
    }

    class CLIError {
        +exit_code: int
    }

    class RESTError {
        +status_code: int
        +detail: str
    }

    class MQError {
        +retryable: bool
        +dead_letter: bool
    }

    class ErrorHandler {
        +handle(error: Exception) InterfaceError
        +format_for_cli(error) str
        +format_for_rest(error) dict
        +format_for_mq(error) dict
    }

    InterfaceError <|-- CLIError
    InterfaceError <|-- RESTError
    InterfaceError <|-- MQError
    ErrorHandler --> InterfaceError : creates
```

## 10. Request/Response Flow

```mermaid
classDiagram
    class Request {
        +pipeline_name: str
        +config: dict
        +options: dict
    }

    class Response {
        +success: bool
        +data: Any
        +metadata: dict
    }

    class RequestValidator {
        +validate(request: Request) bool
        -_validate_pipeline_name()
        -_validate_config()
    }

    class ResponseBuilder {
        +build(result: RunResult) Response
        +build_error(error: Exception) Response
    }

    class RequestProcessor {
        +process(request: Request) Response
        -_validate()
        -_execute()
        -_build_response()
    }

    RequestProcessor --> Request : receives
    RequestProcessor --> Response : returns
    RequestProcessor --> RequestValidator : uses
    RequestProcessor --> ResponseBuilder : uses
```

