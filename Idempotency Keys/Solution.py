import time
import threading
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class IdempotentStorage(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Tuple[float, Any, bool]]:
        pass

    @abstractmethod
    def set_success(self, key: str, result: Any, ttl_seconds: int) -> None:
        pass

    @abstractmethod
    def cleanup_expired(self, current_time: float, ttl_seconds: int) -> None:
        pass


class InMemoryIdempotentStorage(IdempotentStorage):
    def __init__(self):
        self._results: Dict[str, Tuple[float, Any, bool]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Tuple[float, Any, bool]]:
        with self._lock:
            return self._results.get(key)

    def set_success(self, key: str, result: Any, ttl_seconds: int) -> None:
        with self._lock:
            self._results[key] = (time.time(), result, True)

    def cleanup_expired(self, current_time: float, ttl_seconds: int) -> None:
        with self._lock:
            expired = [
                k for k, (ts, _, _) in self._results.items()
                if current_time - ts > ttl_seconds
            ]
            for k in expired:
                del self._results[k]


class IdempotentProcessor:
    def __init__(
        self,
        ttl_seconds: int = 300,
        storage: Optional[IdempotentStorage] = None,
        cleanup_interval_seconds: float = 30.0,
    ):
        self.ttl_seconds = ttl_seconds
        self.storage = storage or InMemoryIdempotentStorage()
        self.cleanup_interval = cleanup_interval_seconds

        self._key_locks: Dict[str, threading.Lock] = {}
        self._in_flight: Dict[str, bool] = {}
        self._coord_lock = threading.Lock()

        self._metrics = defaultdict(int)
        self._metrics_lock = threading.Lock()

        self._shutdown_event = threading.Event()
        self._cleanup_thread = threading.Thread(
            target=self._run_cleanup_loop,
            daemon=True,
            name="IdempotentProcessor-Cleanup"
        )
        self._cleanup_thread.start()

    def _record_metric(self, name: str) -> None:
        with self._metrics_lock:
            self._metrics[name] += 1

    def process(self, idempotency_key: str, action_callable: Callable, *args, **kwargs) -> Any:
        current_time = time.time()

        cached = self.storage.get(idempotency_key)
        if cached is not None:
            timestamp, result, is_success = cached
            if is_success and (current_time - timestamp <= self.ttl_seconds):
                self._record_metric("cache_hit")
                return result

        with self._coord_lock:
            if idempotency_key not in self._key_locks:
                self._key_locks[idempotency_key] = threading.Lock()
            key_lock = self._key_locks[idempotency_key]

            if idempotency_key in self._in_flight:
                self._record_metric("concurrent_wait")  # Record concurrent wait here
                is_first = False
            else:
                self._in_flight[idempotency_key] = True
                is_first = True

        acquired = False
        try:
            key_lock.acquire()
            acquired = True

            cached = self.storage.get(idempotency_key)
            if cached is not None:
                timestamp, result, is_success = cached
                if is_success and (current_time - timestamp <= self.ttl_seconds):
                    return result

            self._record_metric("cache_miss")
            result = action_callable(*args, **kwargs)
            self.storage.set_success(idempotency_key, result, self.ttl_seconds)
            return result

        except Exception:
            raise
        finally:
            if acquired:
                key_lock.release()
                with self._coord_lock:
                    self._in_flight.pop(idempotency_key, None)

    def get_metrics(self) -> Dict[str, int]:
        with self._metrics_lock:
            return dict(self._metrics)

    def _run_cleanup_loop(self) -> None:
        while not self._shutdown_event.is_set():
            try:
                self.storage.cleanup_expired(time.time(), self.ttl_seconds)
            except Exception as e:
                logger.warning("Cleanup error: %s", e, exc_info=True)
            self._shutdown_event.wait(timeout=self.cleanup_interval)

    def shutdown(self, timeout: float = 5.0) -> None:
        if not self._shutdown_event.is_set():
            self._shutdown_event.set()
            self._cleanup_thread.join(timeout=timeout)
            logger.info("IdempotentProcessor shutdown complete.")

    def __del__(self):
        self.shutdown()