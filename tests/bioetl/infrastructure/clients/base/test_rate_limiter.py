import pytest
import time
from bioetl.infrastructure.clients.base.impl.rate_limiter import TokenBucketRateLimiterImpl

def test_rate_limiter_acquire():
    limiter = TokenBucketRateLimiterImpl(rate=50, capacity=1)
    start = time.monotonic()
    limiter.acquire() # consume 1 (immediate if capacity=1)
    
    # Now tokens=0. Need 1 token. rate=50 -> 0.02 sec
    limiter.acquire() 
    duration = time.monotonic() - start
    assert duration >= 0.015

def test_rate_limiter_refill():
    limiter = TokenBucketRateLimiterImpl(rate=10, capacity=10)
    limiter._tokens = 0
    limiter._last_refill = time.monotonic() - 0.5
    limiter._refill()
    assert 4.9 <= limiter._tokens <= 5.1

def test_wait_if_needed():
    limiter = TokenBucketRateLimiterImpl(rate=1, capacity=1)
    limiter.wait_if_needed() # Should not raise
