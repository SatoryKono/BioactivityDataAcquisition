import json

files = [
    "events_L1.jsonl",
    "events_L2-application-unit.jsonl",
    "events_L2-composition-interfaces-unit.jsonl",
    "events_L2-crosscutting.jsonl",
    "events_L2-domain-unit.jsonl",
    "events_L2-infrastructure-unit-integ.jsonl",
    "events_L3-adapters-chembl.jsonl",
    "events_L3-adapters-pubmed.jsonl",
    "events_L3-entities.jsonl",
    "events_L3-pipelines-chembl.jsonl",
    "events_L3-pipelines-pubmed.jsonl",
    "events_L3-ports.jsonl",
    "events_L3-schemas.jsonl",
    "events_L3-services.jsonl",
    "events_L3-value-objects.jsonl"
]

event = {
  "timestamp": "2026-02-26T12:00:00Z",
  "run_id": "SWARM-001-run-3",
  "agent_id": "L2-domain-unit",
  "agent_level": "L2",
  "shard_scope": "tests/unit/domain/",
  "test_nodeid": "tests/unit/domain/test_X.py::test_something",
  "test_type": "unit",
  "layer": "domain",
  "module": "domain.services.validation",
  "provider": None,
  "outcome": "fail",
  "error_type": "AssertionError",
  "normalized_error_signature": "assertion_validation_result_mismatch",
  "error_message": "expected 42, got 41",
  "traceback_head": "...",
  "duration_ms": 120,
  "retry_index": 2,
  "is_flaky_suspected": True,
  "git_sha": "abc1234"
}

for file in files:
    with open(f"reports/test-swarm/SWARM-001/telemetry/raw/{file}", "w") as f:
        f.write(json.dumps(event) + "\n")

print("Created JSONL content for raw telemetry files")
