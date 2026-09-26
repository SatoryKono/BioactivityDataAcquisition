"""Neo4j apply batch execution extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _as_mapping
from memory.graph.sync_pkg._core_models import GroupedStatementFailureContext, JsonValue
from memory.graph.sync_pkg.transport import Neo4jHttpClient

__all__ = [
    "_batched",
    "_execute_grouped_statements",
    "_execute_statement_batch",
    "_raise_grouped_statement_failure",
    "_statement_failure_context",
]


def _batched[T](items: list[T], size: int) -> list[list[T]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _statement_failure_context(statement: dict[str, JsonValue]) -> str:
    parameters = _as_mapping(statement.get("parameters"))
    node_name = parameters.get("name")
    if node_name is not None:
        return f"name={node_name!r}"
    source_name = parameters.get("source_name")
    target_name = parameters.get("target_name")
    return f"source={source_name!r}, target={target_name!r}"


def _raise_grouped_statement_failure(
    context: GroupedStatementFailureContext,
    statement: dict[str, JsonValue],
    cause: Exception,
) -> None:
    raise RuntimeError(
        f"Neo4j sync failed while applying {context.kind} group `{context.group_name}` "
        f"(batch {context.batch_index}/{context.batch_count}, "
        f"statement {context.statement_index}/{context.statement_count}, "
        f"{_statement_failure_context(statement)})"
    ) from cause


def _execute_statement_batch(
    client: Neo4jHttpClient,
    batch: list[dict[str, JsonValue]],
    *,
    kind: str,
    group_name: str,
    batch_index: int,
    batch_count: int,
) -> None:
    try:
        client.execute(batch)
    except Exception as exc:  # pragma: no cover - depends on live backend state
        if len(batch) == 1:
            _raise_grouped_statement_failure(
                GroupedStatementFailureContext(
                    kind=kind,
                    group_name=group_name,
                    batch_index=batch_index,
                    batch_count=batch_count,
                    statement_index=1,
                    statement_count=1,
                ),
                statement=batch[0],
                cause=exc,
            )
        for statement_index, statement in enumerate(batch, start=1):
            try:
                client.execute([statement])
            except (
                Exception
            ) as statement_exc:  # pragma: no cover - live backend dependent
                _raise_grouped_statement_failure(
                    GroupedStatementFailureContext(
                        kind=kind,
                        group_name=group_name,
                        batch_index=batch_index,
                        batch_count=batch_count,
                        statement_index=statement_index,
                        statement_count=len(batch),
                    ),
                    statement=statement,
                    cause=statement_exc,
                )


def _execute_grouped_statements(
    client: Neo4jHttpClient,
    grouped_statements: dict[str, list[dict[str, JsonValue]]],
    batch_size: int,
    kind: str,
) -> None:
    for group_name in sorted(grouped_statements):
        statements = grouped_statements[group_name]
        grouped_batches = _batched(statements, batch_size)
        for batch_index, batch in enumerate(grouped_batches, start=1):
            _execute_statement_batch(
                client,
                batch,
                kind=kind,
                group_name=group_name,
                batch_index=batch_index,
                batch_count=len(grouped_batches),
            )
