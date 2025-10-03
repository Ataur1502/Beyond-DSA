## Multi-Tenant Token-Bucket Rate Limiter Implementation

This solution implements a Multi-Tenant Token-Bucket Rate Limiter designed to manage and enforce fair usage limits for thousands of concurrent clients accessing a high-throughput public API. The design prioritizes thread safety, memory efficiency, and scalability, meeting all the requirements outlined in the problem statement.

### 1. Design Overview

The system is structured into two main classes:

*   **TokenBucket**: Manages the rate-limiting state for a single client. It handles token replenishment over time and thread-safe consumption.
*   **MultiTenantRateLimiter**: Manages a collection of TokenBucket instances, one for each client, providing the multi-tenant capability.

This separation of concerns ensures that the core rate-limiting logic is encapsulated and secured with a per-client lock, minimizing contention and maximizing scalability across a large number of clients.

### 2. Implementation Details

#### 2.1. The TokenBucket Class

| Attribute      | Type              | Description                                                                                  |
|----------------|-------------------|----------------------------------------------------------------------------------------------|
| capacity       | int               | The maximum number of tokens (burst capacity).                                               |
| refill_rate    | float             | Tokens added per second.                                                                     |
| current_tokens | float             | The current number of available tokens. Stored as a float for precise replenishment.         |
| last_checked   | float             | The timestamp of the last time tokens were replenished or consumed.                          |
| lock           | threading.Lock    | A per-bucket lock to ensure thread-safe access and updates to the token state.               |

**Token Refill Logic**

The token replenishment is performed on-demand within the `allow_request` method, using the following steps:

1.  Calculate the elapsed time since `last_checked`.
2.  Calculate replenished tokens: `elapsed × refill_rate`.
3.  Update `current_tokens`:
    `current_tokens = min(capacity, current_tokens + (elapsed × refill_rate))`
4.  Update `last_checked` to the current time.

**Request Allowance**

To handle fractional replenishment but enforce an integer-based request consumption, the check for available tokens uses the floor of the current token count:

`floor(current_tokens) ≥ tokens_requested`

If the request is allowed, the token count is decreased: `current_tokens -= tokens_requested`.

#### 2.2. The MultiTenantRateLimiter Class

This class manages the collection of client rate limiters.

| Attribute   | Type              | Description                                                        |
|-------------|-------------------|--------------------------------------------------------------------|
| clients     | Dict[str, TokenBucket] | A dictionary mapping client_id (string) to its corresponding TokenBucket instance. |
| global_lock | threading.Lock    | A global lock used only for the dictionary access (adding a new client).             |


**allow_request Method**

The process for handling a request is:

1.  **Client Check & Initialization**: Acquire the `global_lock`. If the `client_id` is not in the `clients` dictionary, a new `TokenBucket` is created using the provided or default parameters (`capacity=5, refill_rate=1.0`) and added to the dictionary. The `global_lock` is then released.
    *   **Rationale for the Global Lock**: This lock is only held briefly during client creation, which is a relatively rare event. This minimizes global contention.
2.  **Rate Limiting**: The request is delegated to the specific client's `TokenBucket` instance, which handles the per-client locking and the rate-limiting logic. This is the key to scalability, as concurrent requests for different clients will never contend for the same lock.

### 3. Key Design Features

#### Scalability and Concurrency

*   **Per-Client Locking**: The use of `threading.Lock` inside each `TokenBucket` instance means that only requests for the exact same client contend for a lock. Requests from different clients can proceed completely independently and concurrently, which is crucial for supporting thousands of clients.
*   **Minimal Global Lock**: The `global_lock` is only used for the initial lookup and creation of a new client's bucket. Once a client's bucket exists, the global lock is not needed for rate-limiting checks, ensuring the primary path of execution is non-contending.

#### Meeting Requirements

| Requirement        | How it's Met                                                                                                                                         |
|--------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| Dynamic Clients    | The `allow_request` method creates a new `TokenBucket` instance with full capacity upon the first request for a new `client_id`.                     |
| Burst Handling     | When a client is initialized, or after a long period of inactivity, `current_tokens` is capped at `capacity`, allowing for a burst of requests.      |
| Token Refill       | Tokens are replenished linearly based on `time.time()` and `refill_rate`, with `current_tokens` tracked as a float for precision.                    |
| Thread-Safe        | Both the client dictionary and individual `TokenBucket` operations are protected by `threading.Lock`.                                                |
| Memory-Efficient   | Only four floating-point/integer values and one lock are stored per client, keeping the overhead minimal.                                            |



### 4. Potential Extensions

The current design is highly extensible. Possible future modifications could include:

*   **Configuration Updates**: Adding a method to modify a client's capacity and refill\_rate at runtime.
*   **Token Consumption Monitoring**: Integrating a mechanism to log or track rate limit hits for reporting and analytics.
*   **Persistence**: Storing the `current_tokens` and `last_checked` state in a persistent store (e.g., Redis) to survive system restarts, which is a common requirement for production rate limiters.

### 5. Video Demonstration

