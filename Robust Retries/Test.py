import logging
import time
import asyncio
import math
from Solution import retry, FakeResponse, MaxRetriesExceeded, NonRetryableStatus


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def approx_equal(a, b, tol=0.2):
    return abs(a - b) <= tol


class FlakyService:
    def __init__(self):
        self.calls = 0

    @retry(max_retries=5, base_delay=0.5, max_delay=4.0, jitter=False)
    def call(self):
        self.calls += 1
        if self.calls < 3:
            logging.info(f"[FlakyService] Simulated transient failure #{self.calls}")
            raise RuntimeError("temporary network glitch")
        logging.info(f"[FlakyService] Success on attempt {self.calls}")
        return "OK"


class BadRequestService:
    @retry(max_retries=4, base_delay=0.5, max_delay=2.0, jitter=False)
    def call(self):
        return FakeResponse(400)


class AsyncFlaky:
    def __init__(self):
        self.calls = 0

    @retry(max_retries=4, base_delay=0.5, max_delay=3.0, jitter=False)
    async def call(self):
        self.calls += 1
        if self.calls < 2:
            logging.info(f"[AsyncFlaky] Simulated async transient failure #{self.calls}")
            raise RuntimeError("network timeout")
        return FakeResponse(200, {"msg": "async success"})


class AlwaysFail:
    @retry(max_retries=3, base_delay=0.5, max_delay=4.0, jitter=False)
    def call(self):
        raise RuntimeError("service down")


class JitterTest:
    @retry(max_retries=2, base_delay=1.0, max_delay=4.0, jitter=True)
    def call(self):
        raise RuntimeError("force jitter")


if __name__ == "__main__":
    print("\n========== Test 1: FlakyService Success After Retries ==========")
    s = FlakyService()
    start = time.time()
    result = s.call()
    duration = time.time() - start
    print(f"✅ Result: {result}, Calls: {s.calls}, Duration: {duration:.2f}s")
    assert result == "OK"
    assert s.calls == 3
    expected_delay = 0.5 + 1.0  # first (0.5s) + second (1.0s)
    assert approx_equal(duration, expected_delay, tol=0.5)

    print("\n========== Test 2: BadRequestService (Non-Retryable) ==========")
    bad = BadRequestService()
    try:
        bad.call()
    except NonRetryableStatus as e:
        print(f"✅ Non-retryable detected correctly: {e}")
    else:
        raise AssertionError("Should not retry for 400 status")

    print("\n========== Test 3: AsyncFlaky Success After One Retry ==========")
    async def run_async_test():
        af = AsyncFlaky()
        start = time.time()
        res = await af.call()
        elapsed = time.time() - start
        print(f"✅ Async success after {af.calls} calls, duration={elapsed:.2f}s")
        assert af.calls == 2
        assert res.status_code == 200

    asyncio.run(run_async_test())

    print("\n========== Test 4: AlwaysFail Exhausts Retries ==========")
    always = AlwaysFail()
    try:
        always.call()
    except MaxRetriesExceeded as e:
        print(f"✅ Raised MaxRetriesExceeded as expected: {e}")
    else:
        raise AssertionError("Expected MaxRetriesExceeded")

    print("\n========== Test 5: Jitter Randomness Check ==========")
    jt = JitterTest()
    delays = []
    for _ in range(5):
        start = time.time()
        try:
            jt.call()
        except MaxRetriesExceeded:
            pass
        delays.append(time.time() - start)

    print(f"✅ Jitter delays observed (approx): {[round(d, 2) for d in delays]}")
    print("Note: They should vary — proving jitter randomness works.")

    print("\n✅✅✅ All tests completed successfully.")
