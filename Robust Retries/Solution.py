from __future__ import annotations
import time
import asyncio
import logging
import random
import functools
from typing import Any, Callable, Tuple, Optional

logger = logging.getLogger(__name__)


class MaxRetriesExceeded(Exception):
    """Raised when retries have been exhausted."""
    pass


class NonRetryableStatus(Exception):
    """Raised internally when a response indicates a non-retryable HTTP status (4xx except 429)."""
    def __init__(self, status_code: int, message: Optional[str] = None):
        self.status_code = status_code
        super().__init__(message or f"Non-retryable status code: {status_code}")


class FakeResponse:
    """Lightweight HTTP-like response mock."""
    def __init__(self, status_code: int, payload: Optional[dict] = None):
        self.status_code = status_code
        self.payload = payload or {}

    def json(self):
        return self.payload

    def __repr__(self):
        return f"<FakeResponse {self.status_code}>"


def _is_response_like(obj: Any) -> bool:
    return hasattr(obj, "status_code") and isinstance(getattr(obj, "status_code"), int)


def _should_retry_for_response(resp: Any) -> Tuple[bool, Optional[Exception]]:
    status = getattr(resp, "status_code", None)
    if status is None:
        return False, None
    if status == 429 or (500 <= status <= 599):
        return True, None
    if 400 <= status <= 499:
        return False, NonRetryableStatus(status, f"Permanent client error: {status}")
    return False, None


def retry(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    retry_on: Tuple[Exception, ...] = (Exception,),
):
    """Decorator factory for robust retry with exponential backoff and jitter."""

    def decorator(func: Callable):
        is_coroutine = asyncio.iscoroutinefunction(func)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if _is_response_like(result):
                        should_retry, non_retry_exc = _should_retry_for_response(result)
                        if non_retry_exc:
                            raise non_retry_exc
                        if should_retry:
                            raise RuntimeError(f"Retryable response status: {result.status_code}")
                    if attempt > 1:
                        logger.info("✅ Success on attempt %d for %s", attempt, func.__name__)
                    return result

                except Exception as exc:
                    last_exc = exc
                    if not isinstance(exc, retry_on):
                        raise
                    if isinstance(exc, NonRetryableStatus):
                        raise
                    if attempt == max_retries:
                        raise MaxRetriesExceeded(f"Failed after {max_retries} attempts") from exc

                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    if jitter:
                        delay = random.uniform(0, delay)
                    logger.warning(
                        "Attempt %d/%d for %s failed with %s → retrying in %.2fs",
                        attempt,
                        max_retries,
                        func.__name__,
                        type(exc).__name__,
                        delay,
                    )
                    time.sleep(delay)
            raise MaxRetriesExceeded(f"Failed after {max_retries} attempts") from last_exc

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    if _is_response_like(result):
                        should_retry, non_retry_exc = _should_retry_for_response(result)
                        if non_retry_exc:
                            raise non_retry_exc
                        if should_retry:
                            raise RuntimeError(f"Retryable response status: {result.status_code}")
                    if attempt > 1:
                        logger.info("✅ Success on attempt %d for %s", attempt, func.__name__)
                    return result

                except Exception as exc:
                    last_exc = exc
                    if not isinstance(exc, retry_on):
                        raise
                    if isinstance(exc, NonRetryableStatus):
                        raise
                    if attempt == max_retries:
                        raise MaxRetriesExceeded(f"Failed after {max_retries} attempts") from exc

                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    if jitter:
                        delay = random.uniform(0, delay)
                    logger.warning(
                        "Attempt %d/%d for %s failed with %s → retrying in %.2fs",
                        attempt,
                        max_retries,
                        func.__name__,
                        type(exc).__name__,
                        delay,
                    )
                    await asyncio.sleep(delay)
            raise MaxRetriesExceeded(f"Failed after {max_retries} attempts") from last_exc

        return async_wrapper if is_coroutine else sync_wrapper

    return decorator


