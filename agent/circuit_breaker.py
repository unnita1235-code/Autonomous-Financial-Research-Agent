import time
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Implements the Circuit Breaker pattern to handle repeated tool or model failures.
    Supports per-tool tracking and a global fallback state.
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.states = {} # tool_name -> {failure_count, last_failure_time, state}

    def _get_state(self, name: str):
        if name not in self.states:
            self.states[name] = {
                "failure_count": 0,
                "last_failure_time": 0,
                "state": "CLOSED"
            }
        return self.states[name]

    def can_execute(self, name: str = "global") -> bool:
        """Checks if the circuit for the given name is in a state that allows execution."""
        state_data = self._get_state(name)
        if state_data["state"] == "OPEN":
            if time.time() - state_data["last_failure_time"] > self.recovery_timeout:
                state_data["state"] = "HALF_OPEN"
                return True
            return False
        return True

    def is_open(self, name: str) -> bool:
        """Helper to check if a specific tool's circuit is open."""
        return not self.can_execute(name)

    def record_success(self, name: str = "global"):
        """Records a successful operation for the given name."""
        state_data = self._get_state(name)
        state_data["failure_count"] = 0
        state_data["state"] = "CLOSED"

    def record_failure(self, name: str = "global"):
        """Records a failed operation for the given name."""
        state_data = self._get_state(name)
        state_data["failure_count"] += 1
        state_data["last_failure_time"] = time.time()
        
        if state_data["failure_count"] >= self.failure_threshold:
            state_data["state"] = "OPEN"
            logger.error(f"Circuit Breaker for '{name}' OPENED after {state_data['failure_count']} failures.")
