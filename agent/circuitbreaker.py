import time
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Implements the Circuit Breaker pattern to handle repeated tool or model failures.
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED" # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """Checks if the circuit is in a state that allows execution."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True

    def record_success(self):
        """Records a successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        """Records a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(f"Circuit Breaker OPENED after {self.failure_count} failures.")
