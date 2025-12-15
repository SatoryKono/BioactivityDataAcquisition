from prometheus_client import Counter, Gauge, Histogram

# Rule 3.5: Provider Health Metric
# Labels: provider
PROVIDER_HEALTH_STATUS = Gauge(
    "provider_health_status",
    "Current health status of the provider (0=Unhealthy, 1=Degraded, 2=Healthy)",
    ["provider"]
)

# Rule 3.4: Data Quality Metrics
# Labels: pipeline, entity, column, check
DQ_VALIDATION_SCORE = Gauge(
    "dq_validation_score",
    "Data Quality validation score (e.g., null rate, uniqueness)",
    ["pipeline", "entity", "column", "check"]
)

# Rule 3.1.2: Error Rates
RECORD_ERROR_RATE = Gauge(
    "record_error_rate",
    "Rate of records failing validation in the current batch",
    ["pipeline", "dataset"]
)

# Circuit Breaker State
# Labels: service
CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=Closed, 1=Half-Open, 2=Open)",
    ["service"]
)

CIRCUIT_BREAKER_TRIPS = Counter(
    "circuit_breaker_trips_total",
    "Total number of times the circuit breaker has opened",
    ["service"]
)
