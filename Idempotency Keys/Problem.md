**Problem 2 — Idempotent Payments API (Guaranteed-Once Execution in Distributed Systems)**

**Context:**
In large-scale payment systems, network retries, load balancers, and multi-region deployments can cause the same request to hit the backend multiple times. A simple “if seen before, skip execution” logic isn’t enough — because duplicate requests can arrive simultaneously on different servers, possibly before the first one completes.

To ensure a charge operation runs exactly once, even under concurrent, delayed, or retried conditions, payment platforms use idempotency keys and consistent result caching.

You are tasked with designing an Idempotent Payments Processor that guarantees a request with the same `idempotency_key` will have only one successful execution across concurrent invocations — returning consistent results every time.

---

**Problem Description:**
Implement a fault-tolerant **IdempotentProcessor** that coordinates between concurrent and repeated calls using the same idempotency key. It should behave predictably under timing races, handle failures gracefully, and avoid duplicate side effects (e.g., charging a card twice).

Implement the method:

```
process(idempotency_key: str, action_callable: Callable, *args, **kwargs) -> Any
```

---

**System Requirements:**

1.  **Single Execution Guarantee:**
    *   If multiple identical requests (same key) are received simultaneously, only one should execute `action_callable`.
    *   Others should wait for that execution to complete and return the same result.
2.  **Failure Semantics:**
    *   If the first execution fails (exception), the failure is not cached.
    *   A subsequent retry should re-execute the action.
3.  **Result Consistency:**
    *   Every request with the same key (until expiration) must receive the same exact result object.
4.  **TTL-Based Expiry:**
    *   Cached results expire after a configurable TTL (default: 5 minutes).
    *   After expiry, a new request with the same key should re-execute the action.
5.  **Thread & Process Safety:**
    *   Must be thread-safe within a single instance.
    *   Your design should allow easy extension to distributed caches (e.g., Redis, DynamoDB).
6.  **Memory Efficiency:**
    *   Only minimal state should be kept in memory.
    *   Include a background cleanup mechanism for expired results.
7.  **Observability:**
    *   Log or expose metrics for cache hits, cache misses, and concurrent waits per key.
8.  **Extensibility:**
    *   The system should allow different backends for key storage (e.g., in-memory, Redis, PostgreSQL) by abstracting the storage layer.

---

**Example Flow:**

| Time    | Request                        | Action               | Expected Behavior                   |
| :------ | :----------------------------- | :------------------- | :---------------------------------- |
| t0      | Client sends key=“abc123”      | Executes charge      | Result stored                       |
| t0+5ms  | Duplicate key=“abc123”         | Waits for first      | Returns same result                 |
| t0+5s   | Client retries key=“abc123”    | Cache hit            | Returns cached result               |
| t0+301s | Retry key=“abc123”             | TTL expired          | Executes again                      |

---

**Learning Focus:**

*   Achieving exactly-once semantics in distributed payment APIs.
*   Building concurrency-safe systems using locks and futures.
*   Designing layered caching with TTL and cleanup.
*   Extending in-memory logic to distributed key-value stores.
*   Understanding practical idempotency patterns in payment engineering.
