from types import SimpleNamespace
from typing import Self

from bioetl.application.pipelines.hooks_impl import LoggingPipelineHookImpl
from bioetl.clients.base.logging.contracts import LoggerAdapterABC
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import StageResult


class _DummyLogger(LoggerAdapterABC):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    def info(self, msg: str, **ctx: object) -> None:
        self.calls.append(("info", msg, ctx))

    def error(self, msg: str, **ctx: object) -> None:
        self.calls.append(("error", msg, ctx))

    def debug(self, msg: str, **ctx: object) -> None:
        self.calls.append(("debug", msg, ctx))

    def warning(self, msg: str, **ctx: object) -> None:
        self.calls.append(("warning", msg, ctx))

    def bind(self, **ctx: object) -> Self:  # pragma: no cover - не используется в тестах
        return self


def test_logging_hook_records_messages_and_context():
    logger = _DummyLogger()
    hook = LoggingPipelineHookImpl(logger)

    context = SimpleNamespace(run_id="run-123", provider="chembl", entity_name="bioactivity")
    stage_result = StageResult(
        stage_name="extract",
        success=True,
        records_processed=10,
        chunks_processed=1,
        duration_sec=0.5,
        errors=[],
    )
    stage_error = PipelineStageError(
        provider="chembl",
        entity="bioactivity",
        stage="extract",
        attempt=2,
        run_id="run-123",
        cause=Exception("boom"),
    )

    hook.on_stage_start("extract", context)
    hook.on_stage_end("extract", stage_result)
    hook.on_error("extract", stage_error)

    assert logger.calls == [
        (
            "debug",
            "Hook: stage started",
            {"stage": "extract", "run_id": "run-123", "provider": "chembl", "entity": "bioactivity"},
        ),
        (
            "debug",
            "Hook: stage finished",
            {"stage": "extract", "success": True, "records": 10, "duration_sec": 0.5},
        ),
        (
            "error",
            "Hook: stage error",
            {
                "stage": "extract",
                "attempt": 2,
                "run_id": "run-123",
                "provider": "chembl",
                "entity": "bioactivity",
                "error": "boom",
            },
        ),
    ]
