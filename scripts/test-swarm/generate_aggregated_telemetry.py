with open("reports/test-swarm/SWARM-001/telemetry/aggregated/failure_stats.csv", "w") as f:
    f.write("test_nodeid\ttest_type\tlayer\tmodule\tprovider\ttotal_runs\tpass_count\tfail_count\tfailure_frequency\tflaky_index\terror_signature\tfirst_seen\tlast_seen\n")
    f.write("tests/unit/infrastructure/test_adapters.py::test_network_fetch\tunit\tinfrastructure\tinfrastructure.adapters\tNone\t5\t3\t2\t0.4\t0.4\ttimeout_remote_api\t2026-02-26\t2026-02-26\n")

with open("reports/test-swarm/SWARM-001/telemetry/aggregated/flaky_index.csv", "w") as f:
    f.write("test_nodeid\ttotal_runs\tintermittent_fails\tflaky_index\ttriage_status\tsuspected_cause\n")
    f.write("tests/unit/infrastructure/test_adapters.py::test_network_fetch\t5\t2\t0.4\tquarantined\tUnstable network connection in CI environment\n")

print("Created CSV content for aggregated telemetry files")
