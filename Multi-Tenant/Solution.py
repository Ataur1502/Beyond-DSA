import time
import threading
from math import floor
from typing import Dict, Optional

class TokenBucket:

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.current_tokens = float(capacity)
        self.last_checked = time.time()
        self.lock = threading.Lock()

    def allow_request(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_checked
            self.current_tokens = min(self.capacity, self.current_tokens + elapsed * self.refill_rate)
            self.last_checked = now

            if floor(self.current_tokens) >= tokens:
                self.current_tokens -= tokens
                return True
            return False

    def get_tokens(self) -> float:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_checked
            self.current_tokens = min(self.capacity, self.current_tokens + elapsed * self.refill_rate)
            self.last_checked = now
            return self.current_tokens


class MultiTenantRateLimiter:
    def __init__(self):
        self.clients: Dict[str, TokenBucket] = {}
        self.global_lock = threading.Lock()

    def allow_request(
        self,
        client_id: str,
        tokens: int = 1,
        capacity: Optional[int] = None,
        refill_rate: Optional[float] = None
    ) -> bool:
        with self.global_lock:
            if client_id not in self.clients:
                if capacity is None:
                    capacity = 5
                if refill_rate is None:
                    refill_rate = 1.0
                self.clients[client_id] = TokenBucket(capacity, refill_rate)

        return self.clients[client_id].allow_request(tokens)

    def get_client_tokens(self, client_id: str) -> Optional[float]:
        bucket = self.clients.get(client_id)
        if bucket:
            return bucket.get_tokens()
        return None

