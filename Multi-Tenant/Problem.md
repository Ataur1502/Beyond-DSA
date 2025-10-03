### Problem 1 — Token-Bucket Rate Limiter (Multi-Tenant)

**Context:**

You are designing a high-throughput public API used by thousands of clients. To prevent abuse, ensure fair usage, and protect system resources, each client must be rate-limited. Requests may come in bursts, but over time, the system should enforce a maximum sustained request rate.

A token-bucket algorithm is commonly used in production systems for rate limiting because it allows bursts while enforcing a steady rate. This problem simulates that scenario in a multi-tenant system.

**Problem Statement**

Implement a token-bucket rate limiter that supports multiple clients. Each client has:

*   **Capacity:** Maximum number of requests that can be made in a burst.
*   **Refill rate:** Number of tokens added per second for sustained usage.

You must implement the function:

`allow_request(client_id: str, tokens: int = 1) -> bool`

Returns `True` if the request is allowed.
Returns `False` if the request exceeds the client’s available tokens.

Your system should support:

*   **Dynamic clients:** Clients can be added at any time. When a client is dynamically added or encountered for the first time, its `current_tokens` should be initialized to its full `capacity`.
*   **Burst handling:** Clients may temporarily exceed the sustained rate if tokens are available.
*   **Token refill over time:** Tokens must replenish linearly based on elapsed time. The `refill_rate` can be a fractional value (e.g., 0.5 tokens/second). `current_tokens` should be tracked as a floating-point number, allowing for precise token replenishment over time. `allow_request` should only consume integer amounts of `tokens`, effectively checking if `floor(current_tokens)` is greater than or equal to the requested `tokens`.
*   **Concurrency:** Multiple requests from the same client may arrive simultaneously.

**Additional Requirements**

*   **Memory-efficient:** Maintain only minimal state per client.
*   **Thread-safe:** Must correctly handle concurrent requests for the same client.
*   **Scalable:** Must support thousands of clients efficiently without excessive locking or contention.
*   **Extensible:** Design should allow easy modification of capacity and refill rate per client.

**Example Scenario**

| Client | Capacity | Refill rate | Requests sequence | Expected Result          |
| :----- | :------- | :---------- | :---------------- | :----------------------- |
| A      | 5        | 1/sec       | 5 requests at t=0 | All allowed              |
| A      | 5        | 1/sec       | 6th request at t=0 | Blocked (False)          |
| A      | 5        | 1/sec       | 1 request at t=1  | Allowed (tokens refilled)|

**Learning Focus**

*   Applying data structures like dictionaries and counters in practical engineering scenarios.
*   Implementing thread-safe algorithms for concurrent requests.
*   Understanding rate-limiting strategies and real-world production constraints.
*   Designing scalable systems that support multi-tenancy.

