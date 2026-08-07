from __future__ import annotations

import json

import pytest

from scripts.ai.codex import profile_benchmark

pytestmark = pytest.mark.unit


def test_score_response_uses_reproducible_60_40_rubric() -> None:
    task = profile_benchmark.TASKS[0]
    payload = {
        "answer": task.expected_answer,
        "validation": list(task.expected_validation),
    }
    assert profile_benchmark.score_response(task, payload) == {
        "correctness": 60,
        "validation_completeness": 40,
        "total": 100,
    }


def test_score_accepts_semantically_equivalent_paths_and_valid_dag_order() -> None:
    navigation = profile_benchmark.TASKS[0]
    navigation_payload = {
        "answer": {
            "implementation_owner": "src/bioetl/infrastructure/adapters/chembl/client.py",
            "wiring_owner": "src/bioetl/composition/bootstrap/chembl.py",
            "forbidden_direction": "interfaces importing infrastructure",
        },
        "validation": list(navigation.expected_validation),
    }
    planning = profile_benchmark.TASKS[2]
    planning_payload = {
        "answer": {"order": ["A", "B", "D", "C"], "parallel_with_c": "D"},
        "validation": list(planning.expected_validation),
    }

    assert profile_benchmark.score_response(navigation, navigation_payload)["total"] == 100
    assert profile_benchmark.score_response(planning, planning_payload)["total"] == 100

def test_parse_jsonl_extracts_only_final_payload_and_usage() -> None:
    stdout = "\n".join(
        [
            json.dumps({"type": "thread.started", "thread_id": "redacted"}),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "agent_message",
                        "text": '{"answer":{"option":"B"},"validation":[]}',
                    },
                }
            ),
            json.dumps(
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": 40,
                        "output_tokens": 10,
                    },
                }
            ),
        ]
    )

    payload, usage = profile_benchmark.parse_jsonl(stdout)

    assert payload == {"answer": {"option": "B"}, "validation": []}
    assert usage == {
        "input_tokens": 100,
        "cached_input_tokens": 40,
        "output_tokens": 10,
    }


def test_profile_commands_are_ephemeral_read_only_and_disable_plugins() -> None:
    command = profile_benchmark._command(
        profile_benchmark.PROFILES["balanced"], "safe prompt"
    )

    assert command[:3] == ["codex", "exec", "--ephemeral"]
    assert "--ignore-user-config" in command
    assert "--ignore-rules" in command
    assert "read-only" in command
    assert "plugins" in command
    assert "apps" in command
    assert "safe prompt" == command[-1]


def test_recommendation_uses_quality_then_latency_and_checks_deep() -> None:
    summaries = {
        "fast": {
            "mean_score": 100,
            "median_wall_time_ms": 5,
            "total_billable_token_proxy": 5,
            "failed_runs": 0,
        },
        "balanced": {
            "mean_score": 100,
            "median_wall_time_ms": 10,
            "total_billable_token_proxy": 20,
            "failed_runs": 0,
        },
        "deep": {
            "mean_score": 96,
            "median_wall_time_ms": 12,
            "total_billable_token_proxy": 10,
            "failed_runs": 0,
        },
    }

    recommendation = profile_benchmark._recommendation(
        summaries, ["fast", "balanced", "deep"]
    )

    assert recommendation["default"] == "balanced"
    assert recommendation["deep_noninferior_to_default"] is True
    assert recommendation["agents_max_threads"] == 3
