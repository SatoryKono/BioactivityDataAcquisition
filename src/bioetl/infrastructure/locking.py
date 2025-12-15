import time
import uuid
import redis
import logging

class LockAcquisitionError(Exception):
    pass

class RedisDistributedLock:
    def __init__(self, redis_client: redis.Redis, resource: str, ttl_sec: int = 60):
        self.redis = redis_client
        self.resource = f"lock:{resource}"
        self.ttl = ttl_sec
        # Rule 3.3: Fencing Token (owner_id)
        self.owner_id = f"{uuid.uuid4()}:{int(time.time())}"
        self._is_locked = False

    def acquire(self, blocking: bool = True, timeout: int = 300) -> None:
        """Acquires lock via SETNX."""
        start_time = time.time()
        while True:
            # Rule 3.3: SETNX + EXPIRE
            if self.redis.set(self.resource, self.owner_id, nx=True, ex=self.ttl):
                self._is_locked = True
                return

            if not blocking:
                raise LockAcquisitionError(f"Could not acquire lock for {self.resource}")

            if time.time() - start_time > timeout:
                raise LockAcquisitionError(f"Timeout acquiring lock for {self.resource}")

            time.sleep(0.1)

    def heartbeat(self) -> None:
        """Rule 3.3: Heartbeat mechanism."""
        if not self._is_locked:
            return
        # Extend TTL only if we still own the lock
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        success = self.redis.eval(script, 1, self.resource, self.owner_id, self.ttl)
        if not success:
            self._is_locked = False
            raise LockAcquisitionError("Lock lost during heartbeat! Aborting.")

    def release(self) -> None:
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        self.redis.eval(script, 1, self.resource, self.owner_id)
        self._is_locked = False
