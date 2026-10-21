import json
import unittest
from urllib.error import HTTPError
from scripts.runpod_api_readonly_check import verify, BASE

class FakeResponse:
    status = 200
    def __init__(self, data):
        self.data = data
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, count=-1): return json.dumps(self.data).encode()

class RunPodReadOnlyTests(unittest.TestCase):
    def test_missing_key_never_calls_network(self):
        def bad(*a, **k): raise AssertionError("must not call network")
        self.assertEqual(verify("", opener=bad), (2, "MISSING_OR_INVALID_KEY"))
    def test_only_get_pods_and_network_volumes(self):
        calls = []
        def opener(request, timeout):
            calls.append((request.full_url, request.get_method(), timeout))
            return FakeResponse({})
        self.assertEqual(verify("fake-test-key", opener=opener), (0, "READ_ONLY_CONNECTED"))
        self.assertEqual(calls, [(BASE + "/pods", "GET", 20), (BASE + "/network-volumes", "GET", 20)])
    def test_fails_closed_on_bad_auth_without_leaking_body(self):
        def opener(request, timeout):
            raise HTTPError(request.full_url, 401, "test secret should not appear", {}, None)
        self.assertEqual(verify("fake-test-key", opener=opener), (1, "PODS_HTTP_401"))
    def test_aborts_before_storage_request_after_first_failure(self):
        calls = []
        def opener(request, timeout):
            calls.append(request.full_url)
            raise HTTPError(request.full_url, 403, "No access", {}, None)
        self.assertEqual(verify("fake-test-key", opener=opener), (1, "PODS_HTTP_403"))
        self.assertEqual(calls, [BASE + "/pods"])

if __name__ == "__main__":
    unittest.main()
