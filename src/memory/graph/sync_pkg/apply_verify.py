"""Post-apply verification helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import JsonValue
from memory.graph.sync_pkg.apply_runtime import _execute_grouped_statements
from memory.graph.sync_pkg.live_queries import (
    _live_managed_node_counts,
    _live_managed_relation_counts,
)
from memory.graph.sync_pkg.transport import Neo4jHttpClient

__all__ = [
    "CRITICAL_ANALYSIS_NODE_LABELS",
    "CRITICAL_ANALYSIS_RELATION_TYPES",
    "_active_group_names",
    "_critical_analysis_group_counts",
    "_critical_analysis_mismatch_messages",
    "_critical_analysis_retry_batch_size",
    "_expected_group_counts",
    "_expected_group_mismatches",
    "_group_count_mismatches",
    "_group_mismatch_messages",
    "_group_names",
    "_missing_group_names",
    "_raise_analysis_group_mismatches",
    "_refresh_node_counts_if_retried",
    "_refresh_relation_counts_if_retried",
    "_retry_critical_analysis_groups",
    "_retry_critical_node_groups",
    "_retry_critical_relation_groups",
    "_retry_missing_groups",
    "_verify_expected_group_counts",
]

CRITICAL_ANALYSIS_NODE_LABELS: tuple[str, ...] = (
    "retirement_candidate",
    "complexity_candidate",
)
CRITICAL_ANALYSIS_RELATION_TYPES: tuple[str, ...] = (
    "CANDIDATE_FOR_REMOVAL",
    "HAS_COMPLEXITY_SIGNAL",
    "CANDIDATE_FOR_SIMPLIFICATION",
    "JUSTIFIED_BY_RUNTIME",
    "BLOCKED_BY_VARIANCE",
)


def _active_group_names(
    ordered_names: tuple[str, ...],
    grouped_statements: dict[str, list[dict[str, JsonValue]]],
) -> list[str]:
    return [name for name in ordered_names if name in grouped_statements]


def _missing_group_names(
    active_names: list[str],
    grouped_statements: dict[str, list[dict[str, JsonValue]]],
    live_counts: dict[str, int],
) -> list[str]:
    return [
        name
        for name in active_names
        if live_counts.get(name, 0) != len(grouped_statements[name])
    ]


def _retry_missing_groups(
    client: Neo4jHttpClient,
    grouped_statements: dict[str, list[dict[str, JsonValue]]],
    missing_names: list[str],
    retry_batch_size: int,
    *,
    kind: str,
) -> None:
    if not missing_names:
        return
    _execute_grouped_statements(
        client,
        {name: grouped_statements[name] for name in missing_names},
        retry_batch_size,
        kind,
    )


def _critical_analysis_retry_batch_size(batch_size: int) -> int:
    return max(1, min(batch_size, 5))


def _refresh_node_counts_if_retried(
    client: Neo4jHttpClient,
    active_node_labels: list[str],
    missing_node_labels: list[str],
    *,
    sync_run: str | None,
    live_node_counts: dict[str, int],
) -> dict[str, int]:
    if not missing_node_labels:
        return live_node_counts
    return _live_managed_node_counts(
        client,
        tuple(active_node_labels),
        context="post-retry critical node verification",
        sync_run=sync_run,
    )


def _refresh_relation_counts_if_retried(
    client: Neo4jHttpClient,
    active_relation_types: list[str],
    missing_relation_types: list[str],
    *,
    sync_run: str | None,
    live_relation_counts: dict[str, int],
) -> dict[str, int]:
    if not missing_relation_types:
        return live_relation_counts
    return _live_managed_relation_counts(
        client,
        tuple(active_relation_types),
        context="post-retry critical relation verification",
        sync_run=sync_run,
    )


def _group_mismatch_messages(
    active_names: list[str],
    grouped_statements: dict[str, list[dict[str, JsonValue]]],
    live_counts: dict[str, int],
    *,
    noun: str,
) -> list[str]:
    mismatches: list[str] = []
    for name in active_names:
        live_count = live_counts.get(name, 0)
        expected = len(grouped_statements[name])
        if live_count == expected:
            continue
        mismatches.append(
            f"{noun} `{name}` expected {expected}, live managed {live_count}"
        )
    return mismatches


def _raise_analysis_group_mismatches(
    mismatches: list[str],
    *,
    prefix: str,
) -> None:
    if mismatches:
        raise RuntimeError(prefix + "; ".join(mismatches))


def _retry_critical_analysis_groups(
    client: Neo4jHttpClient,
    node_groups: dict[str, list[dict[str, JsonValue]]],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    batch_size: int,
    sync_run: str | None = None,
) -> None:
    retry_batch_size = _critical_analysis_retry_batch_size(batch_size)
    active_node_labels = _active_group_names(CRITICAL_ANALYSIS_NODE_LABELS, node_groups)
    active_relation_types = _active_group_names(
        CRITICAL_ANALYSIS_RELATION_TYPES, relation_groups
    )
    live_node_counts, live_relation_counts = _critical_analysis_group_counts(
        client,
        active_node_labels=active_node_labels,
        active_relation_types=active_relation_types,
        sync_run=sync_run,
    )
    live_node_counts = _retry_critical_node_groups(
        client,
        active_node_labels,
        node_groups,
        live_node_counts=live_node_counts,
        retry_batch_size=retry_batch_size,
        sync_run=sync_run,
    )
    live_relation_counts = _retry_critical_relation_groups(
        client,
        active_relation_types,
        relation_groups,
        live_relation_counts=live_relation_counts,
        retry_batch_size=retry_batch_size,
        sync_run=sync_run,
    )

    missing_after_retry = _critical_analysis_mismatch_messages(
        active_node_labels=active_node_labels,
        node_groups=node_groups,
        live_node_counts=live_node_counts,
        active_relation_types=active_relation_types,
        relation_groups=relation_groups,
        live_relation_counts=live_relation_counts,
    )
    _raise_analysis_group_mismatches(
        missing_after_retry,
        prefix="Post-apply verification failed for critical analysis groups: ",
    )


def _retry_critical_node_groups(
    client: Neo4jHttpClient,
    active_node_labels: list[str],
    node_groups: dict[str, list[dict[str, JsonValue]]],
    *,
    live_node_counts: dict[str, int],
    retry_batch_size: int,
    sync_run: str | None,
) -> dict[str, int]:
    missing_node_labels = _missing_group_names(
        active_node_labels,
        node_groups,
        live_node_counts,
    )
    _retry_missing_groups(
        client,
        node_groups,
        missing_node_labels,
        retry_batch_size,
        kind="critical node retry",
    )
    return _refresh_node_counts_if_retried(
        client,
        active_node_labels,
        missing_node_labels,
        sync_run=sync_run,
        live_node_counts=live_node_counts,
    )


def _retry_critical_relation_groups(
    client: Neo4jHttpClient,
    active_relation_types: list[str],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    *,
    live_relation_counts: dict[str, int],
    retry_batch_size: int,
    sync_run: str | None,
) -> dict[str, int]:
    missing_relation_types = _missing_group_names(
        active_relation_types,
        relation_groups,
        live_relation_counts,
    )
    _retry_missing_groups(
        client,
        relation_groups,
        missing_relation_types,
        retry_batch_size,
        kind="critical relation retry",
    )
    return _refresh_relation_counts_if_retried(
        client,
        active_relation_types,
        missing_relation_types,
        sync_run=sync_run,
        live_relation_counts=live_relation_counts,
    )


def _critical_analysis_group_counts(
    client: Neo4jHttpClient,
    *,
    active_node_labels: list[str],
    active_relation_types: list[str],
    sync_run: str | None,
) -> tuple[dict[str, int], dict[str, int]]:
    return (
        _live_managed_node_counts(
            client,
            tuple(active_node_labels),
            context="post-apply critical node verification",
            sync_run=sync_run,
        ),
        _live_managed_relation_counts(
            client,
            tuple(active_relation_types),
            context="post-apply critical relation verification",
            sync_run=sync_run,
        ),
    )


def _critical_analysis_mismatch_messages(
    *,
    active_node_labels: list[str],
    node_groups: dict[str, list[dict[str, JsonValue]]],
    live_node_counts: dict[str, int],
    active_relation_types: list[str],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    live_relation_counts: dict[str, int],
) -> list[str]:
    mismatches = _group_mismatch_messages(
        active_node_labels,
        node_groups,
        live_node_counts,
        noun="label",
    )
    mismatches.extend(
        _group_mismatch_messages(
            active_relation_types,
            relation_groups,
            live_relation_counts,
            noun="relation",
        )
    )
    return mismatches


def _verify_expected_group_counts(
    client: Neo4jHttpClient,
    node_groups: dict[str, list[dict[str, JsonValue]]],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    *,
    strict_analysis: bool,
    sync_run: str | None = None,
) -> None:
    live_node_counts, live_relation_counts = _expected_group_counts(
        client,
        node_groups=node_groups,
        relation_groups=relation_groups,
        sync_run=sync_run,
    )
    mismatches = _expected_group_mismatches(
        node_groups=node_groups,
        relation_groups=relation_groups,
        live_node_counts=live_node_counts,
        live_relation_counts=live_relation_counts,
    )

    if strict_analysis:
        active_tokens = tuple(node_groups) + tuple(relation_groups)
        critical_mismatches = [
            mismatch
            for mismatch in mismatches
            if any(token in mismatch for token in active_tokens)
        ]
        _raise_analysis_group_mismatches(
            critical_mismatches,
            prefix="Post-apply verification failed for critical analysis groups: ",
        )
    else:
        _raise_analysis_group_mismatches(
            mismatches,
            prefix="Post-apply verification failed for targeted sync groups: ",
        )


def _expected_group_mismatches(
    *,
    node_groups: dict[str, list[dict[str, JsonValue]]],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    live_node_counts: dict[str, int],
    live_relation_counts: dict[str, int],
) -> list[str]:
    mismatches = _group_count_mismatches(
        grouped_statements=node_groups,
        live_counts=live_node_counts,
        noun="label",
    )
    mismatches.extend(
        _group_count_mismatches(
            grouped_statements=relation_groups,
            live_counts=live_relation_counts,
            noun="relation",
        )
    )
    return mismatches


def _group_count_mismatches(
    *,
    grouped_statements: dict[str, list[dict[str, JsonValue]]],
    live_counts: dict[str, int],
    noun: str,
) -> list[str]:
    mismatches: list[str] = []
    for name, statements in sorted(grouped_statements.items()):
        expected = len(statements)
        live_count = live_counts.get(name, 0)
        if live_count != expected:
            mismatches.append(
                f"{noun} `{name}` expected {expected}, live managed {live_count}"
            )
    return mismatches


def _group_names(
    grouped_statements: dict[str, list[dict[str, JsonValue]]],
) -> tuple[str, ...]:
    return tuple(sorted(grouped_statements))


def _expected_group_counts(
    client: Neo4jHttpClient,
    *,
    node_groups: dict[str, list[dict[str, JsonValue]]],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    sync_run: str | None,
) -> tuple[dict[str, int], dict[str, int]]:
    return (
        _live_managed_node_counts(
            client,
            _group_names(node_groups),
            context="post-apply node group verification",
            sync_run=sync_run,
        ),
        _live_managed_relation_counts(
            client,
            _group_names(relation_groups),
            context="post-apply relation group verification",
            sync_run=sync_run,
        ),
    )
