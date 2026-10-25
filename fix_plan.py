import re

with open("docs/05-operations/runbooks/incident-response.md", "r") as f:
    content = f.read()

# Replace the "Auth Failure" header with proper symptom and alertname
content = re.sub(
    r"### 1\. Auth Failure \(`401 Unauthorized`\)\n\n- \*\*Symptom\*\*: Logs show repeated `401` errors from a provider API\.",
    r"### 1. Provider HTTP Error Rate High\n\n- **Alert**: `BioETLProviderHttpErrorRateHigh`\n- **Symptom**: Logs show repeated `401 Unauthorized` or similar HTTP errors from a provider API.",
    content
)

# Replace the "Rate Limit Exhausted" header
content = re.sub(
    r"### 2\. Rate Limit Exhausted \(`429 Too Many Requests`\)\n\n- \*\*Symptom\*\*: Spike in `bioetl_errors_total\{error_code=\"recoverable\"\}` metric\. Pipeline slows down effectively to a halt\.",
    r"### 2. Provider Rate Limiter Depleted / Wait High\n\n- **Alert**: `BioETLProviderRateLimiterTokensDepleted` / `BioETLProviderRateLimiterWaitHigh`\n- **Symptom**: Spike in `bioetl_errors_total{error_code=\"recoverable\"}` metric. Logs show `429 Too Many Requests`. Pipeline slows down effectively to a halt.",
    content
)


# Replace the "Lock Timeout" header
content = re.sub(
    r"### 4\. Lock Timeout \(\"Lock expired\"\)\n\n- \*\*Symptom\*\*: Alert \"Lock expired\" fires, or pipeline refuses to start\.",
    r"### 4. Lock Timeout\n\n- **Alert**: `BioETLCheckpointCompatibilityBlocked` (or related control plane / checkpoint failed alerts)\n- **Symptom**: Logs show \"Lock expired\", or pipeline refuses to start.",
    content
)


print(content)
