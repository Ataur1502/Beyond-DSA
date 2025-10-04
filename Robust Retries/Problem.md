# Problem 3 — Robust API Client with Exponential Backoff & Jitter (Reliable Retry in Distributed Systems)

**Context:**
In large-scale distributed systems, clients frequently call external APIs or microservices. Network glitches, transient server errors (5xx), or rate-limiting responses (429) can cause requests to fail intermittently. Naively retrying immediately can overwhelm the server, produce cascading failures, or cause synchronized retry storms across clients.

To improve reliability and resilience, production-grade clients implement retry policies with exponential backoff and jitter. Exponential backoff increases the delay between retries after each failure, while jitter introduces randomness to avoid synchronized retries from multiple clients hitting the service simultaneously.

You are tasked with designing a Retry Decorator that applies a robust retry policy to any API call or function, ensuring predictable behavior under transient failures while preventing overload on external services.

## Problem Description:

Implement a retry mechanism using a decorator that wraps any function performing external requests. The decorator should support exponential backoff with jitter, configurable retry limits, and handle both retryable and non-retryable errors.

Implement the decorator:

```python
@retry(max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 30.0, jitter: bool = True, retry_on: Tuple[Exception, ...] = (Exception,))
def call_api(*args, **kwargs) -> Any:
    ...
```

## System Requirements:

### Retry Policy
*   Retry only for transient or retryable errors (e.g., network failures, HTTP 5xx, 429).
*   Do not retry for permanent client errors (e.g., HTTP 4xx except 429).

### Exponential Backoff
*   Delay grows exponentially with each attempt: `delay = base_delay * 2 ** attempt`.
*   Must respect a configurable maximum delay (`max_delay`).

### Jitter
*   Add randomness to delay to prevent multiple clients from retrying simultaneously.
*   Jitter can be full, equal to 0–delay, or partial (optional).

### Maximum Retry Limit
*   After `max_retries` attempts, raise the last exception gracefully.

### Decorator Implementation
*   Retry logic must be reusable as a decorator.
*   Configurable via decorator parameters (`max_retries`, `base_delay`, `max_delay`, `jitter`, `retry_on`).

### Logging / Observability
*   Log each retry attempt, including attempt number, error, and delay.
*   Log final failure when retries are exhausted.

### Thread Safety
*   Safe to use in multi-threaded or asynchronous environments (optional).

## Example Flow:

| Time      | Request      | Behavior                                                               |
| :-------- | :----------- | :--------------------------------------------------------------------- |
| t0        | `call_api()` | Executes function; failure occurs, schedule retry                      |
| t0 + 1s   | First retry  | Waits ~1s (`base_delay`) + jitter; executes again                      |
| t0 + 3s   | Second retry | Waits ~2s (exponential) + jitter; executes again                       |
| t0 + 7s   | Third retry  | Waits ~4s + jitter; executes successfully                              |
| t0 + ...  | Retry limit  | Raises last exception; logs failure                                    |

## Learning Focus:

*   Designing robust retry strategies for distributed systems.
*   Applying exponential backoff and jitter to reduce retry storms.
*   Using decorators for reusable fault-tolerant logic.
*   Handling transient vs permanent failures in client APIs.
*   Observability and logging for retryable operations.