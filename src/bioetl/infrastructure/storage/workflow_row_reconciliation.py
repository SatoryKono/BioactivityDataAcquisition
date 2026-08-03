"""Infrastructure adapter for deterministic workflow row reconciliation."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, cast

from bioetl.domain.ports import (
    LoggerPort,
    MetricsPort,
    RowReconciliationConfig,
    RowReconciliationError,
    RowReconciliationExecutionError,
    RowReconciliationLayer,
    RowReconciliationPort,
    RowReconciliationResult,
    RowReconciliationTypePolicy,
)
from bioetl.infrastructure.storage.workflow_row_reconciliation_support import (
    reconcile_loaded_rows,
)

__all__ = ["StorageRowReconciliationAdapter"]

_RECONCILIATION_ROWS_LEFT_TOTAL = "bioetl_workflow_row_reconciliation_left_rows_total"
_RECONCILIATION_ROWS_RIGHT_TOTAL = "bioetl_workflow_row_reconciliation_right_rows_total"
_RECONCILIATION_ROWS_KEPT_TOTAL = "bioetl_workflow_row_reconciliation_kept_rows_total"
_RECONCILIATION_ROWS_EXCLUDED_TOTAL = (
    "bioetl_workflow_row_reconciliation_excluded_rows_total"
)
_IMPLEMENTATION_ID = "storage_row_reconciliation_v1"


@dataclass(slots=True)
class StorageRowReconciliationAdapter(RowReconciliationPort):
    """Reconcile Silver/Gold rows through existing storage reader seams."""

    silver_reader: object
    gold_reader: object
    logger: LoggerPort
    metrics: MetricsPort | None = None

    async def reconcile_rows(
        self,
        config: RowReconciliationConfig,
    ) -> RowReconciliationResult:
        self._log(
            "info",
            "workflow row reconciliation started",
            layer=RowReconciliationLayer(config.layer).value,
            left_table=config.left_table,
            right_table=config.right_table,
            left_columns=list(config.left_columns),
            right_columns=list(config.right_columns),
            nulls_equal=config.nulls_equal,
            type_policy=cast("RowReconciliationTypePolicy", config.type_policy).value,
        )
        left_rows = await self._read_rows(config, side="left")
        right_rows = await self._read_rows(config, side="right")
        result = reconcile_loaded_rows(
            config,
            left_rows=left_rows,
            right_rows=right_rows,
            implementation=_IMPLEMENTATION_ID,
        )

        self._record_metrics(result)
        self._log(
            "info",
            "workflow row reconciliation completed",
            layer=result.layer.value,
            left_table=result.left_table,
            right_table=result.right_table,
            kept_rows=result.kept_rows,
            excluded_rows=result.excluded_rows,
            distinct_right_keys=result.distinct_right_keys,
        )
        return result

    async def _read_rows(
        self,
        config: RowReconciliationConfig,
        *,
        side: str,
    ) -> list[dict[str, object]]:
        if RowReconciliationLayer(config.layer) is RowReconciliationLayer.SILVER:
            return await self._call_reader(
                self.silver_reader,
                "read_silver",
                config.left_table if side == "left" else config.right_table,
                columns=None,
            )
        return await self._call_reader(
            self.gold_reader,
            "read_gold",
            config.left_table if side == "left" else config.right_table,
            columns=None,
            current_only=True,
        )

    async def _call_reader(
        self,
        reader: object,
        method_name: str,
        table_name: str,
        **kwargs: object,
    ) -> list[dict[str, object]]:
        method = getattr(reader, method_name, None)
        if not callable(method):
            raise RowReconciliationExecutionError(
                f"Configured {method_name} reader does not expose {method_name}()"
            )
        try:
            value = method(table_name, **_supported_kwargs(method, kwargs))
            if inspect.isawaitable(value):
                value = await value
            from collections.abc import Iterable
            from typing import Any, cast

            rows = cast(
                Iterable[Any],  # Any: storage result is dynamically dispatched.
                value,
            )
            return [dict(row) for row in rows]
        except RowReconciliationError:
            raise
        except (AttributeError, LookupError, TypeError, ValueError) as exc:
            raise RowReconciliationExecutionError(str(exc)) from exc

    def _record_metrics(self, result: RowReconciliationResult) -> None:
        if self.metrics is None:
            return
        labels = {"layer": result.layer.value}
        self.metrics.increment_counter(
            _RECONCILIATION_ROWS_LEFT_TOTAL,
            result.input_left_rows,
            labels,
        )
        self.metrics.increment_counter(
            _RECONCILIATION_ROWS_RIGHT_TOTAL,
            result.input_right_rows,
            labels,
        )
        self.metrics.increment_counter(
            _RECONCILIATION_ROWS_KEPT_TOTAL,
            result.kept_rows,
            labels,
        )
        self.metrics.increment_counter(
            _RECONCILIATION_ROWS_EXCLUDED_TOTAL,
            result.excluded_rows,
            labels,
        )

    def _log(
        self,
        level: str,
        message: str,
        **context: Any,  # Any: structured logger context accepts arbitrary scalars.
    ) -> None:
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message, **context)


def _non_none_kwargs(kwargs: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in kwargs.items() if value is not None}


def _signature_accepts_var_keyword(signature: inspect.Signature) -> bool:
    return any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def _supported_kwargs(
    method: Any,  # Any: inspect.signature accepts arbitrary runtime callables.
    kwargs: dict[str, object],
) -> dict[str, object]:
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        return _non_none_kwargs(kwargs)
    if _signature_accepts_var_keyword(signature):
        return _non_none_kwargs(kwargs)
    allowed = signature.parameters
    return {
        key: value
        for key, value in kwargs.items()
        if value is not None and key in allowed
    }
