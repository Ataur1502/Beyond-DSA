import time
import threading
import pytest
from Solution import IdempotentProcessor


def test_single_execution_under_concurrency():
    processor = IdempotentProcessor(ttl_seconds=10)
    call_count = 0
    lock = threading.Lock()

    def charge_action(amount: int) -> dict:
        nonlocal call_count
        with lock:
            call_count += 1
            time.sleep(0.01)  # simulate work
        return {"status": "success", "charge_id": "ch_123", "amount": amount}

    key = "test_key_001"
    results = []
    exceptions = []

    def worker():
        try:
            res = processor.process(key, charge_action, 100)
            results.append(res)
        except Exception as e:
            exceptions.append(e)

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert call_count == 1, f"Expected 1 execution, got {call_count}"
    assert len(exceptions) == 0
    assert len(results) == 50
    first = results[0]
    for r in results[1:]:
        assert r == first


def test_failure_not_cached():
    processor = IdempotentProcessor(ttl_seconds=10)
    call_count = 0

    def flaky_action():
        nonlocal call_count
        call_count += 1
        raise ValueError("Payment failed")

    key = "fail_key_001"
    with pytest.raises(ValueError):
        processor.process(key, flaky_action)
    with pytest.raises(ValueError):
        processor.process(key, flaky_action)
    assert call_count == 2


def test_success_cached_until_ttl():
    processor = IdempotentProcessor(ttl_seconds=1)
    call_count = 0

    def stable_action():
        nonlocal call_count
        call_count += 1
        return {"id": "txn_abc", "status": "ok"}

    key = "ttl_key_001"
    res1 = processor.process(key, stable_action)
    assert call_count == 1
    res2 = processor.process(key, stable_action)
    assert call_count == 1
    assert res2 == res1
    time.sleep(1.1)
    res3 = processor.process(key, stable_action)
    assert call_count == 2
    assert res3 == res1


def test_metrics_tracking():
    processor = IdempotentProcessor(ttl_seconds=10)

    def dummy_action():
        time.sleep(0.05)  # ensure overlap for concurrent wait
        return "result"

    # Cache miss
    processor.process("key1", dummy_action)
    metrics = processor.get_metrics()
    assert metrics["cache_miss"] == 1
    assert metrics.get("cache_hit", 0) == 0
    assert metrics.get("concurrent_wait", 0) == 0

    # Cache hit
    processor.process("key1", dummy_action)
    metrics = processor.get_metrics()
    assert metrics["cache_hit"] == 1

    # Concurrent wait using Barrier
    results = []
    barrier = threading.Barrier(2)

    def worker():
        barrier.wait()  # synchronize threads
        results.append(processor.process("key2", dummy_action))

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    metrics = processor.get_metrics()
    assert metrics.get("concurrent_wait", 0) >= 1
    assert len(results) == 2
    assert results[0] == results[1]


def test_background_cleanup():
    processor = IdempotentProcessor(ttl_seconds=1, cleanup_interval_seconds=0.5)

    def action():
        return "clean_me"

    processor.process("expiring_key", action)
    assert len(processor.storage._results) == 1
    time.sleep(2.0)
    assert len(processor.storage._results) == 0


def test_exception_propagation():
    processor = IdempotentProcessor(ttl_seconds=10)

    class PaymentError(Exception):
        pass

    def bad_action():
        raise PaymentError("Card declined")

    key = "err_key"
    with pytest.raises(PaymentError) as exc_info1:
        processor.process(key, bad_action)
    with pytest.raises(PaymentError) as exc_info2:
        processor.process(key, bad_action)

    assert str(exc_info1.value) == "Card declined"
    assert str(exc_info2.value) == "Card declined"


def test_shutdown():
    processor = IdempotentProcessor(ttl_seconds=10)
    processor.shutdown()
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
