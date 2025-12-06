"""Компонент, инкапсулирующий применение политики обработки ошибок."""

from collections.abc import Callable

from bioetl.application.pipelines.hooks_manager import HooksManager
from bioetl.domain.enums import ErrorAction
from bioetl.domain.errors import PipelineStageError
from bioetl.domain.models import RunContext
from bioetl.domain.pipelines.contracts import ErrorPolicyABC
from bioetl.domain.providers import ProviderId
from bioetl.clients.base.logging.contracts import LoggerAdapterABC


class ErrorPolicyManager:
    """Делегат для применения политики ошибок и вызова хуков."""

    def __init__(
        self,
        *,
        error_policy: ErrorPolicyABC,
        hooks_manager: HooksManager,
        logger: LoggerAdapterABC,
        provider_id: ProviderId,
        entity_name: str,
        default_on_skip: Callable[[str], object],
    ) -> None:
        self._error_policy = error_policy
        self._hooks_manager = hooks_manager
        self._logger = logger
        self._provider_id = provider_id
        self._entity_name = entity_name
        self._default_on_skip = default_on_skip
        self._last_error: PipelineStageError | None = None
        self._last_stage_action: dict[str, ErrorAction | None] = {}

    @property
    def last_error(self) -> PipelineStageError | None:
        """Последняя ошибка стадии."""

        return self._last_error

    def execute(
        self,
        stage: str,
        context: RunContext,
        action: Callable[[], object],
        *,
        attempt: int = 1,
        on_retry: Callable[[], None] | None = None,
    ) -> object:
        """Выполняет действие с учётом политики ошибок."""

        try:
            result = action()
            self._last_error = None
            self._last_stage_action[stage] = None
            return result
        except StopIteration:
            raise
        except Exception as exc:  # pylint: disable=broad-except
            error = PipelineStageError(
                provider=self._provider_id.value,
                entity=self._entity_name,
                stage=stage,
                attempt=attempt,
                run_id=context.run_id,
                cause=exc,
            )
            self._last_error = error
            self._logger.error(
                "Stage failed",
                stage=stage,
                provider=self._provider_id.value,
                entity=self._entity_name,
                run_id=context.run_id,
                error=str(exc),
            )
            for hook in self._hooks_manager.hooks:
                hook.on_error(stage, error)

            action_on_error = self._error_policy.handle(error, context)
            self._last_stage_action[stage] = action_on_error
            if (
                action_on_error == ErrorAction.RETRY
                and self._error_policy.should_retry(error)
            ):
                if on_retry:
                    on_retry()
                return self.execute(
                    stage,
                    context,
                    action,
                    attempt=attempt + 1,
                    on_retry=on_retry,
                )
            if action_on_error == ErrorAction.SKIP:
                self._logger.warning(
                    "Stage skipped due to error policy",
                    stage=stage,
                    provider=self._provider_id.value,
                    entity=self._entity_name,
                    run_id=context.run_id,
                    error=str(exc),
                )
                return self._default_on_skip(stage)

            raise error from exc

    def get_last_error_messages(self) -> list[str]:
        """Возвращает список сообщений последней ошибки."""

        if self._last_error is None:
            return []

        messages = [str(self._last_error)]
        if self._last_error.cause:
            messages.append(str(self._last_error.cause))
        return messages

    def get_last_action(self, stage: str) -> ErrorAction | None:
        """Возвращает последнее действие политики ошибок для стадии."""

        return self._last_stage_action.get(stage)

    def reset(self) -> None:
        """Сбрасывает состояние ошибок и действий политики."""

        self._last_error = None
        self._last_stage_action.clear()

    def set_logger(self, logger: LoggerAdapterABC) -> None:
        """Обновляет логгер для дальнейших сообщений."""

        self._logger = logger
