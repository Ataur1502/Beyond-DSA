import unittest
import time
import threading
from Solution import MultiTenantRateLimiter

class TestTokenBucketRateLimiter(unittest.TestCase):

    def setUp(self):
        self.limiter = MultiTenantRateLimiter()

    def test_basic_burst(self):
        client_id = "client_burst"
        capacity = 5
        refill_rate = 1.0

        for i in range(capacity):
            self.assertTrue(self.limiter.allow_request(client_id, tokens=1, capacity=capacity, refill_rate=refill_rate))

        self.assertFalse(self.limiter.allow_request(client_id, tokens=1))

    def test_fractional_refill(self):
        client_id = "client_fractional"
        capacity = 5
        refill_rate = 0.5

        for i in range(capacity):
            self.assertTrue(self.limiter.allow_request(client_id, tokens=1, capacity=capacity, refill_rate=refill_rate))

        self.assertFalse(self.limiter.allow_request(client_id, tokens=1))

        time.sleep(2)
        self.assertTrue(self.limiter.allow_request(client_id, tokens=1))

        self.assertFalse(self.limiter.allow_request(client_id, tokens=1))

    def test_multiple_clients(self):
        clients = ["A", "B", "C"]
        capacity_map = {"A": 3, "B": 5, "C": 2}
        refill_map = {"A": 1.0, "B": 2.0, "C": 0.5}

        for client in clients:
            for _ in range(capacity_map[client]):
                self.assertTrue(self.limiter.allow_request(client, tokens=1, capacity=capacity_map[client], refill_rate=refill_map[client]))
            self.assertFalse(self.limiter.allow_request(client, tokens=1))

    def test_concurrent_requests(self):
        client_id = "client_concurrent"
        capacity = 10
        refill_rate = 5.0
        self.limiter.allow_request(client_id, tokens=0, capacity=capacity, refill_rate=refill_rate)

        results = []
        def make_request():
            allowed = self.limiter.allow_request(client_id, tokens=1)
            results.append(allowed)

        threads = [threading.Thread(target=make_request) for _ in range(capacity)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(results.count(True), capacity)
        self.assertFalse(self.limiter.allow_request(client_id, tokens=1))

    def test_get_client_tokens(self):
        client_id = "client_monitor"
        capacity = 5
        refill_rate = 1.0

        tokens = self.limiter.get_client_tokens(client_id)
        self.assertIsNone(tokens)

        self.assertTrue(self.limiter.allow_request(client_id, tokens=1, capacity=capacity, refill_rate=refill_rate))
        tokens = self.limiter.get_client_tokens(client_id)
        self.assertGreaterEqual(tokens, 3.9)

if __name__ == "__main__":
    unittest.main()
