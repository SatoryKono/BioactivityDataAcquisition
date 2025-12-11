import requests

from bioetl.infrastructure.errors import ApiClientError, ApiTimeoutError
from bioetl.infrastructure.http.retry import ExponentialRetryPolicy


def test_should_retry_on_timeout_and_status():
    policy = ExponentialRetryPolicy(max_attempts=3, backoff_factor=0.5)

    assert policy.should_retry(ApiTimeoutError("timeout"), attempt=1)

    exc = requests.RequestException()
    assert policy.should_retry(exc, attempt=1)

    api_err = ApiClientError("fail", status_code=500)
    assert policy.should_retry(api_err, attempt=1)

    non_retry = ApiClientError("fail", status_code=400)
    assert not policy.should_retry(non_retry, attempt=1)


def test_backoff_exponential():
    policy = ExponentialRetryPolicy(max_attempts=5, backoff_factor=1.0)
    assert policy.get_backoff(1) == 1.0
    assert policy.get_backoff(2) == 2.0
    assert policy.get_backoff(3) == 4.0


def test_backoff_cap():
    policy = ExponentialRetryPolicy(
        max_attempts=4, backoff_factor=10.0, backoff_max=15.0
    )

    assert policy.get_backoff(1) == 10.0
    assert policy.get_backoff(2) == 15.0
    assert policy.get_backoff(3) == 15.0
