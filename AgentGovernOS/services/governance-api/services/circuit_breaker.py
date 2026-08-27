import logging

logger = logging.getLogger(__name__)

# Fallback in-memory store if Redis is unavailable
_in_memory_failures: dict[str, int] = {}
CIRCUIT_BREAKER_THRESHOLD = 5

class CircuitBreakerService:
    def __init__(self, redis_client=None):
        self.redis = redis_client

    def record_failure(self, agent_id: str) -> None:
        """
        Increments the failure counter for an agent.
        """
        if self.redis:
            key = f"circuit_breaker:failures:{agent_id}"
            self.redis.incr(key)
            self.redis.expire(key, 3600)  # Reset after 1 hour
        else:
            _in_memory_failures[agent_id] = _in_memory_failures.get(agent_id, 0) + 1
            
    def is_open(self, agent_id: str) -> bool:
        """
        Checks if the circuit breaker is open (too many recent failures).
        """
        if self.redis:
            val = self.redis.get(f"circuit_breaker:failures:{agent_id}")
            if val and int(val) >= CIRCUIT_BREAKER_THRESHOLD:
                return True
            return False
        else:
            return _in_memory_failures.get(agent_id, 0) >= CIRCUIT_BREAKER_THRESHOLD
            
    def reset(self, agent_id: str) -> None:
        """
        Resets the circuit breaker manually.
        """
        if self.redis:
            self.redis.delete(f"circuit_breaker:failures:{agent_id}")
        else:
            _in_memory_failures.pop(agent_id, None)
