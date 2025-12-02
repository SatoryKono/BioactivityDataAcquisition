import pytest
from bioetl.infrastructure.clients.base.impl.retry_policy import ExponentialBackoffRetryImpl

def test_should_retry():
    policy = ExponentialBackoffRetryImpl(max_attempts=3)
    assert policy.should_retry(Exception(), 1)
    assert policy.should_retry(Exception(), 2)
    assert not policy.should_retry(Exception(), 3)
    assert policy.max_attempts == 3

def test_get_delay():
    policy = ExponentialBackoffRetryImpl(
        base_delay=1.0, 
        backoff_factor=2.0, 
        jitter=False
    )
    assert policy.get_delay(1) == 1.0
    assert policy.get_delay(2) == 2.0
    assert policy.get_delay(3) == 4.0
